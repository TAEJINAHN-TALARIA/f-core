import os
from dotenv import load_dotenv

load_dotenv()

EDGAR_USER_AGENT = os.environ["EDGAR_USER_AGENT"]  # "YourName your@email.com"
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

# 일반 투자자 관점의 핵심 XBRL 태그
TARGET_TAGS = {
    # 손익계산서
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "GrossProfit",
    "OperatingIncomeLoss",
    "NetIncomeLoss",
    "EarningsPerShareBasic",
    "EarningsPerShareDiluted",
    "WeightedAverageNumberOfSharesOutstandingBasic",
    # 재무상태표
    "Assets",
    "AssetsCurrent",
    "Liabilities",
    "LiabilitiesCurrent",
    "LongTermDebt",
    "StockholdersEquity",
    "CashAndCashEquivalentsAtCarryingValue",
    "RetainedEarningsAccumulatedDeficit",
    # 현금흐름
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInInvestingActivities",
    "NetCashProvidedByUsedInFinancingActivities",
    "PaymentsToAcquirePropertyPlantAndEquipment",
    # 주주환원
    "PaymentsForRepurchaseOfCommonStock",
    "PaymentsForRepurchaseOfEquity",
    "PaymentsOfDividendsCommonStock",
    "PaymentsOfDividends",
    # 기타
    "CommonStockSharesOutstanding",
    "InterestExpense",
    "IncomeTaxExpenseBenefit",
    "DepreciationDepletionAndAmortization",
    "ResearchAndDevelopmentExpense",
}

TAXONOMY = "us-gaap"
