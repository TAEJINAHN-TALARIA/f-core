import os
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

EDGAR_USER_AGENT = os.environ["EDGAR_USER_AGENT"]  # "YourName your@email.com"
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

# 수집할 과거 데이터 범위 (오늘 기준 N년 전 이후만 저장)
HISTORY_YEARS = 10
HISTORY_CUTOFF = (date.today() - timedelta(days=HISTORY_YEARS * 365)).isoformat()

import json

# Load concept map
CONCEPT_MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "web", "lib", "concept_map.json")
with open(CONCEPT_MAP_PATH, "r", encoding="utf-8") as f:
    CONCEPT_MAP = json.load(f)

# 일반 투자자 관점의 핵심 XBRL 태그 (동적 로드)
TARGET_TAGS = set()
for concept, data in CONCEPT_MAP.items():
    TARGET_TAGS.update(data["tags"])

TAXONOMY = "us-gaap"
