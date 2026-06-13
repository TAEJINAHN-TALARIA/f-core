import os
import json
import logging
import time
import requests
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

def get_missing_concepts(client, concept_map):
    logger.info("Scanning all companies for missing concepts...")
    res = client.table("companies").select("cik, name").execute()
    companies = res.data
    
    missing_list = []
    
    def process_company(comp):
        cik = comp["cik"]
        name = comp["name"]
        
        # Add retry logic for Supabase API rate limits / connection drops
        max_retries = 3
        for attempt in range(max_retries):
            try:
                facts_res = client.table("facts").select("tag").eq("cik", cik).execute()
                existing_tags = set(r["tag"] for r in facts_res.data)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Error fetching facts for {cik} after {max_retries} attempts: {e}")
                    return []
                time.sleep(1 + attempt)  # simple exponential backoff
            
        found_missing = []
        for concept, info in concept_map.items():
            target_tags = set(info.get("tags", []))
            if not target_tags:
                continue
            # If the company has none of the mapped tags
            if not existing_tags.intersection(target_tags):
                found_missing.append({"cik": cik, "name": name, "concept": concept, "description": info.get("description", concept)})
        return found_missing

    # Parallelize DB lookups
    total_comps = len(companies)
    completed = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_company, comp): comp for comp in companies}
        for future in as_completed(futures):
            res = future.result()
            missing_list.extend(res)
            completed += 1
            if completed % 1000 == 0:
                logger.info(f"Scanned {completed}/{total_comps} companies for missing concepts...")
                
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
    """
    chunk_data is a dict: 
    {
      "0001318605": [
         {"concept": "revenue", "description": "...", "candidates": [...]},
         ...
      ],
      "0001067983": [ ... ]
    }
    Returns a dict mapping CIK -> concept -> best_tag
    """
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
            if len(cands) > 50:
                cands = cands[:50]
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

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts":[{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        data = response.json()
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:-3].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:-3].strip()
            
        result_map = json.loads(raw_text)
        
        # Verify the returned tags are in the candidates list
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
        logger.error(f"LLM API error during chunk: {e}")
        return {}

def auto_commit_tag(concept, tag):
    with open(CONCEPT_MAP_PATH, "r", encoding="utf-8") as f:
        concept_map = json.load(f)
        
    if tag not in concept_map[concept]["tags"]:
        # Insert at the beginning so it has highest priority
        concept_map[concept]["tags"].insert(0, tag)
        with open(CONCEPT_MAP_PATH, "w", encoding="utf-8") as f:
            json.dump(concept_map, f, indent=4)
        return True
    return False

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
        
    chunk_size = 10
    ciks = list(missing_by_cik.keys())
    total_chunks = (len(ciks) + chunk_size - 1) // chunk_size
    
    processed_companies = 0
    total_companies = len(ciks)
    
    for i in range(0, len(ciks), chunk_size):
        chunk_ciks = ciks[i:i+chunk_size]
        logger.info(f"\n=== Processing Chunk {i//chunk_size + 1}/{total_chunks} ({len(chunk_ciks)} companies) ===")
        
        chunk_data = {}
        names_by_cik = {}
        
        def download_and_extract(cik):
            missing_items = missing_by_cik[cik]
            name = missing_items[0]["name"]
            logger.info(f"[{processed_companies + chunk_ciks.index(cik) + 1}/{total_companies}] {name} - {cik} | Downloading SEC facts...")
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
                    unmapped_log_path = os.path.join(os.path.dirname(__file__), "..", "unmapped_concepts.log")
                    with open(unmapped_log_path, "a", encoding="utf-8") as f_unmapped:
                        f_unmapped.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CIK: {cik} ({name}) -> Failed to find heuristic candidates for '{concept}'\n")
            return cik, name, c_data

        with ThreadPoolExecutor(max_workers=chunk_size) as executor:
            futures = {executor.submit(download_and_extract, c): c for c in chunk_ciks}
            for future in as_completed(futures):
                res_cik, res_name, c_data = future.result()
                names_by_cik[res_cik] = res_name
                if c_data:
                    chunk_data[res_cik] = c_data
                    
        processed_companies += len(chunk_ciks)
        
        if not chunk_data:
            continue
            
        logger.info(f"Batch asking LLM to infer best tags for {len(chunk_data)} companies...")
        inferred_tags = infer_best_tags_with_llm_chunk(chunk_data)
        
        for cik, items in chunk_data.items():
            name = names_by_cik[cik]
            for item in items:
                concept = item["concept"]
                best_tag = inferred_tags.get(cik, {}).get(concept)
                
                if best_tag:
                    logger.info(f"  ✅ LLM inferred tag for {cik} '{concept}': {best_tag}")
                    success = auto_commit_tag(concept, best_tag)
                    if success:
                        logger.info(f"  Successfully auto-committed '{best_tag}' to '{concept}' in concept_map.json.")
                        log_path = os.path.join(os.path.dirname(__file__), "..", "tag_updates.log")
                        with open(log_path, "a", encoding="utf-8") as log_f:
                            log_f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CIK: {cik} ({name}) -> Detected '{concept}' Tag: {best_tag}\n")
                else:
                    logger.warning(f"  ❌ LLM could not infer tag for {cik} '{concept}'.")
                    unmapped_log_path = os.path.join(os.path.dirname(__file__), "..", "unmapped_concepts.log")
                    with open(unmapped_log_path, "a", encoding="utf-8") as f_unmapped:
                        f_unmapped.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CIK: {cik} ({name}) -> LLM failed to infer tag for '{concept}' from {len(item['candidates'])} candidates\n")
        
        time.sleep(4)  # Rate limiting for Gemini API

if __name__ == "__main__":
    run_auto_discovery()
