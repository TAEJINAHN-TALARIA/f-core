from fastapi import APIRouter, Depends, Query
from supabase import Client

from ..dependencies import get_supabase
from ..schemas import Company

router = APIRouter()


@router.get("/search", response_model=list[Company])
def search_companies(
    q: str = Query(..., min_length=1, description="Ticker or company name"),
    limit: int = Query(10, ge=1, le=50),
    db: Client = Depends(get_supabase),
):
    q = q.strip()

    # Try exact ticker match first (case-insensitive)
    ticker_res = (
        db.table("companies")
        .select("cik,name,ticker,exchange,sic,sic_description")
        .ilike("ticker", q)
        .limit(limit)
        .execute()
    )

    if ticker_res.data:
        return ticker_res.data

    # Fall back to name prefix/contains search
    name_res = (
        db.table("companies")
        .select("cik,name,ticker,exchange,sic,sic_description")
        .ilike("name", f"%{q}%")
        .limit(limit)
        .execute()
    )

    return name_res.data
