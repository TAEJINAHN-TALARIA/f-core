import os
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

EDGAR_USER_AGENT = os.environ["EDGAR_USER_AGENT"]  # "YourName your@email.com"
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

# 수집할 과거 데이터 범위 (오늘 기준 N년 전 이후만 저장)
HISTORY_YEARS = 5
HISTORY_CUTOFF = (date.today() - timedelta(days=HISTORY_YEARS * 365)).isoformat()

# 일반 투자자 관점의 핵심 XBRL 태그
TARGET_TAGS = {
    # 손익계산서
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "GrossProfit",
    "OperatingIncomeLoss",
    "NetIncomeLoss",
    # 재무상태표
    "Assets",
    "Liabilities",
    "StockholdersEquity",
    # 현금흐름
    "NetCashProvidedByUsedInOperatingActivities",
    "PaymentsToAcquirePropertyPlantAndEquipment",
    # 주주환원
    "PaymentsForRepurchaseOfCommonStock",
    "PaymentsForRepurchaseOfEquity",
    "PaymentsOfDividendsCommonStock",
    "PaymentsOfDividends",
    # 기타
    "InterestExpense",
}

TAXONOMY = "us-gaap"
