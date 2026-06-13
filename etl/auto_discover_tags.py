import os
import json
import logging
import time
import requests
import threading
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# Load .env early so API key is available
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from .loader import get_client
from .config import CONCEPT_MAP_PATH
from .downloader import iter_companyfacts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Locks for thread-safe file writing
file_lock = threading.Lock()

def get_missing_concepts(client, concept_map):
    logger.info("Scanning all companies for missing concepts...")

    companies_res = client.table("companies").select("cik, name").execute()
    companies = companies_res.data

    def fetch_covered_ciks(tags):
        """Return the set of CIKs that have at least one of the given tags."""
        # Each thread needs its own client — sharing one httpx/HTTP2 client across
        # threads causes RemoteProtocolError ("Server disconnected").
        thread_client = get_client()
        covered = set()
        page_size = 1000
        offset = 0
        while True:
            res = (thread_client.table("facts")
                   .select("cik")
                   .in_("tag", tags)
                   .range(offset, offset + page_size - 1)
                   .execute())
            for r in res.data:
                covered.add(r["cik"])
            if len(res.data) < page_size:
                break
            offset += page_size
        return covered

    # Fetch coverage for all concepts in parallel (~10 concurrent queries with pagination)
    # instead of one query per company (6,900 queries).
    concept_covered = {}
    concepts_with_tags = {c: info for c, info in concept_map.items() if info.get("tags")}
    with ThreadPoolExecutor(max_workers=len(concepts_with_tags)) as executor:
        future_to_concept = {
            executor.submit(fetch_covered_ciks, list(info["tags"])): concept
            for concept, info in concepts_with_tags.items()
        }
        for future in as_completed(future_to_concept):
            concept = future_to_concept[future]
            concept_covered[concept] = future.result()
            logger.info(f"  '{concept}' covered by {len(concept_covered[concept])} companies.")

    missing_list = []
    for comp in companies:
        cik = comp["cik"]
        name = comp["name"]
        for concept, info in concept_map.items():
            if not info.get("tags"):
                continue
            if cik not in concept_covered.get(concept, set()):
                missing_list.append({"cik": cik, "name": name, "concept": concept, "description": info.get("description", concept)})

    return missing_list

def extract_candidate_tags(all_tags, concept):
    candidates = []
    
    concept_lower = concept.lower()
    if concept_lower == "revenue":
        keywords = ["revenue", "sales", "income"]
        exclude = ["unearned", "deferred", "receivable"]
    elif concept_lower == "operating_income":
        keywords = ["operating", "income", "profit", "loss"]
        exclude = ["nonoperating", "netincome", "comprehensive"]
    elif concept_lower == "net_income":
        keywords = ["netincome", "loss", "earnings"]
        exclude = ["operating", "comprehensive", "per_share"]
    elif concept_lower == "operating_cash_flow":
        keywords = ["cash", "operating", "activities"]
        exclude = ["financing", "investing"]
    elif concept_lower == "eps_basic":
        keywords = ["earningspershare", "pershare", "per_share", "basic"]
        exclude = ["diluted"]
    elif concept_lower == "eps_diluted":
        keywords = ["earningspershare", "pershare", "per_share", "diluted"]
        exclude = ["basic"]
    elif concept_lower == "sbc":
        keywords = ["sharebased", "stockbased", "compensation"]
        exclude = []
    elif concept_lower == "rnd":
        keywords = ["research", "development"]
        exclude = []
    elif concept_lower == "ppne_net":
        keywords = ["property", "plant", "equipment"]
        exclude = ["gross"]
    elif concept_lower == "dividends_paid":
        keywords = ["dividend", "paid"]
        exclude = ["receivable", "payable"]
    else:
        keywords = [concept_lower.replace("_", " "), concept_lower.split("_")[0]]
        exclude = []
        
    for t in all_tags:
        tl = t.lower()
        if any(k in tl for k in keywords) and not any(e in tl for e in exclude):
            candidates.append(t)
    return list(set(candidates))

def infer_best_tags_with_llm_chunk(chunk_data):
    if not chunk_data:
        return {}
        
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set in .env.")
        return {}
        
    prompt = "We are mapping financial tags from SEC EDGAR. We need the US-GAAP tag that best represents several missing concepts for multiple companies.\n"
    prompt += "For each company (identified by CIK), we have a list of missing concepts and curated candidate tags.\n\nCompanies to map:\n"
    
    for cik, items in chunk_data.items():
        prompt += f"\nCompany CIK: {cik}\n"
        for item in items:
            concept = item["concept"]
            description = item["description"]
            cands = item["candidates"]
            # Limit candidates to keep prompt size reasonable
            if len(cands) > 20:
                cands = cands[:20]
            prompt += f"- Concept: '{concept}'\n  Description: {description}\n  Candidates: {', '.join(cands)}\n"
        
    prompt += """
Please return ONLY a valid JSON object mapping each CIK to a dictionary of its concepts and their best candidate tag exactly as they appear in their candidate lists.
If none of the candidates fit accurately, map it to "NONE".
Do not wrap the JSON in Markdown formatting like ```json.
Example format:
{
  "0001318605": {
    "revenue": "RevenueFromContractWithCustomerExcludingAssessedTax",
    "gross_profit": "GrossProfit",
    "operating_income": "NONE"
  },
  "0001067983": {
    "revenue": "SalesRevenueNet"
  }
}
"""

    # streamGenerateContent+SSE keeps the connection alive while tokens generate,
    # avoiding read timeouts that occur with the blocking generateContent endpoint.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent?alt=sse&key={api_key}"
    payload = {
        "contents": [{"parts":[{"text": prompt}]}]
    }

    max_retries = 5
    for attempt in range(max_retries):
        try:
            # (connect_timeout, per-chunk read timeout) — streaming keeps data flowing so 30s per chunk is safe
            response = requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload), stream=True, timeout=(15, 30))
            response.raise_for_status()

            full_text = ""
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                try:
                    chunk = json.loads(data_str)
                    parts = chunk.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])
                    full_text += parts[0].get("text", "") if parts else ""
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue

            raw_text = full_text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:-3].strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:-3].strip()

            result_map = json.loads(raw_text)

            final_map = {}
            for cik, items in chunk_data.items():
                final_map[cik] = {}
                cik_results = result_map.get(cik, {})
                for item in items:
                    c = item["concept"]
                    tag = cik_results.get(c)
                    if tag == "NONE" or tag not in item["candidates"]:
                        final_map[cik][c] = None
                    else:
                        final_map[cik][c] = tag
            return final_map

        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"LLM API error during chunk after {max_retries} attempts: {e}")
                return {}
            delay = 4 * (2 ** attempt)  # 4, 8, 16, 32s
            logger.warning(f"LLM API error: {e}. Retrying in {delay}s ({attempt+1}/{max_retries})...")
            time.sleep(delay)
    return {}

def auto_commit_tag(concept, tag):
    with file_lock:
        with open(CONCEPT_MAP_PATH, "r", encoding="utf-8") as f:
            concept_map = json.load(f)
            
        if tag not in concept_map[concept]["tags"]:
            # Insert at the beginning so it has highest priority
            concept_map[concept]["tags"].insert(0, tag)
            with open(CONCEPT_MAP_PATH, "w", encoding="utf-8") as f:
                json.dump(concept_map, f, indent=4)
            return True
        return False

def write_log(filename, message):
    log_path = os.path.join(os.path.dirname(__file__), "..", filename)
    with file_lock:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(message)

def run_auto_discovery():
    logger.info("=== Starting Auto Discover Tags Pipeline ===")
    client = get_client()
    
    with open(CONCEPT_MAP_PATH, "r", encoding="utf-8") as f:
        concept_map = json.load(f)
        
    missing_list = get_missing_concepts(client, concept_map)
    logger.info(f"Found {len(missing_list)} missing concept/company pairs.")
    
    missing_by_cik = defaultdict(list)
    for m in missing_list:
        missing_by_cik[m["cik"]].append(m)
        
    # Scale: 10 companies per chunk, 10 chunks in parallel = 100 companies concurrent
    chunk_size = 10
    ciks = list(missing_by_cik.keys())
    total_chunks = (len(ciks) + chunk_size - 1) // chunk_size
    
    def process_chunk(chunk_ciks, chunk_index):
        logger.info(f"--- Started Chunk {chunk_index}/{total_chunks} ({len(chunk_ciks)} companies) ---")
        chunk_data = {}
        names_by_cik = {}
        
        # Parallel download for the companies in this chunk
        def download_and_extract(cik):
            missing_items = missing_by_cik[cik]
            name = missing_items[0]["name"]
            sec_data = next(iter_companyfacts([cik]), None)
            if not sec_data:
                logger.warning(f"❌ Could not download SEC facts for CIK {cik}.")
                return cik, name, None
                
            us_gaap = sec_data.get("facts", {}).get("us-gaap", {})
            all_tags = list(us_gaap.keys())
            
            c_data = []
            for missing in missing_items:
                concept = missing["concept"]
                description = missing["description"]
                candidates = extract_candidate_tags(all_tags, concept)
                if candidates:
                    c_data.append({"concept": concept, "description": description, "candidates": candidates})
                else:
                    logger.warning(f"  ❌ No candidates found for '{concept}' ({name}).")
                    write_log("unmapped_concepts.log", f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CIK: {cik} ({name}) -> Failed to find heuristic candidates for '{concept}'\n")
            return cik, name, c_data

        # Use threads for network IO (downloads)
        with ThreadPoolExecutor(max_workers=chunk_size) as dl_executor:
            futures = {dl_executor.submit(download_and_extract, c): c for c in chunk_ciks}
            for future in as_completed(futures):
                res_cik, res_name, c_data = future.result()
                names_by_cik[res_cik] = res_name
                if c_data:
                    chunk_data[res_cik] = c_data
                    
        if not chunk_data:
            return
            
        logger.info(f"Batch asking LLM to infer best tags for Chunk {chunk_index} ({len(chunk_data)} companies)...")
        inferred_tags = infer_best_tags_with_llm_chunk(chunk_data)
        
        for cik, items in chunk_data.items():
            name = names_by_cik[cik]
            for item in items:
                concept = item["concept"]
                best_tag = inferred_tags.get(cik, {}).get(concept)
                
                if best_tag:
                    logger.info(f"  ✅ [Chunk {chunk_index}] inferred tag for {cik} '{concept}': {best_tag}")
                    success = auto_commit_tag(concept, best_tag)
                    if success:
                        logger.info(f"  Successfully auto-committed '{best_tag}' to '{concept}' in concept_map.json.")
                        write_log("tag_updates.log", f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CIK: {cik} ({name}) -> Detected '{concept}' Tag: {best_tag}\n")
                else:
                    logger.warning(f"  ❌ [Chunk {chunk_index}] LLM could not infer tag for {cik} '{concept}'.")
                    write_log("unmapped_concepts.log", f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CIK: {cik} ({name}) -> LLM failed to infer tag for '{concept}' from {len(item['candidates'])} candidates\n")
                    
        logger.info(f"--- Finished Chunk {chunk_index}/{total_chunks} ---")

    # Run up to 10 chunks concurrently (10 * 10 = 100 companies concurrently)
    with ThreadPoolExecutor(max_workers=10) as chunk_executor:
        chunk_futures = []
        for i in range(0, len(ciks), chunk_size):
            chunk_ciks = ciks[i:i+chunk_size]
            chunk_index = i // chunk_size + 1
            chunk_futures.append(chunk_executor.submit(process_chunk, chunk_ciks, chunk_index))
            
        # Wait for all chunks to finish
        for future in as_completed(chunk_futures):
            future.result()

if __name__ == "__main__":
    run_auto_discovery()
