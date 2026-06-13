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
    else:
        keywords = [concept_lower.replace("_", " "), concept_lower.split("_")[0]]
        exclude = []
        
    for t in all_tags:
        tl = t.lower()
        if any(k in tl for k in keywords) and not any(e in tl for e in exclude):
            candidates.append(t)
    return list(set(candidates))

def infer_best_tag_with_llm(concept, description, candidates):
    if not candidates:
        return None
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set in .env.")
        return None
        
    # Limit candidates to a reasonable number to save tokens and avoid confusion
    if len(candidates) > 50:
        candidates = candidates[:50]
    
    prompt = f"""
We are mapping financial tags from SEC EDGAR. We need the US-GAAP tag that best represents '{concept}' ({description}).
Here is a list of candidate tags extracted from a company's SEC filing:
{', '.join(candidates)}

Which of these tags is the absolute best match for the main '{concept}' metric?
Please return ONLY the tag name exactly as it appears in the list. Do not include any other text, explanation, or quotes.
If none of them fit the concept accurately, return exactly the string "NONE".
"""
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts":[{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload))
        response.raise_for_status()
        data = response.json()
        tag = data["candidates"][0]["content"]["parts"][0]["text"].strip().strip("'\"")
        
        if tag == "NONE" or tag not in candidates:
            return None
        return tag
    except Exception as e:
        logger.error(f"LLM API error: {e}")
        return None

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
        
    processed_companies = 0
    total_companies = len(missing_by_cik)
    
    for cik, missing_items in missing_by_cik.items():
        name = missing_items[0]["name"]
        processed_companies += 1
        logger.info(f"[{processed_companies}/{total_companies}] {name} - {cik} | {len(missing_items)} missing concepts. Downloading SEC facts...")
        
        sec_data = next(iter_companyfacts([cik]), None)
        if not sec_data:
            logger.warning(f"❌ Could not download SEC facts for CIK {cik}. Skipping.")
            continue
            
        us_gaap = sec_data.get("facts", {}).get("us-gaap", {})
        all_tags = list(us_gaap.keys())
        
        for missing in missing_items:
            concept = missing["concept"]
            description = missing["description"]
            
            logger.info(f"  Missing '{concept}'. Extracting candidates...")
            candidates = extract_candidate_tags(all_tags, concept)
            logger.info(f"  Found {len(candidates)} heuristic candidates.")
            
            if not candidates:
                continue
                
            best_tag = infer_best_tag_with_llm(concept, description, candidates)
            
            if best_tag:
                logger.info(f"  ✅ LLM inferred best tag for '{concept}': {best_tag}")
                success = auto_commit_tag(concept, best_tag)
                if success:
                    logger.info(f"  Successfully auto-committed '{best_tag}' to '{concept}' in concept_map.json.")
                    log_path = os.path.join(os.path.dirname(__file__), "..", "tag_updates.log")
                    with open(log_path, "a", encoding="utf-8") as log_f:
                        log_f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CIK: {cik} ({name}) -> Detected '{concept}' Tag: {best_tag}\n")
            else:
                logger.warning(f"  ❌ LLM could not infer a good tag for '{concept}'.")
            
            time.sleep(4)  # Rate limiting for Gemini API

if __name__ == "__main__":
    run_auto_discovery()
