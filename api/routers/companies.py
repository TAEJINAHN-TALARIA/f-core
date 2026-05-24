from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from ..dependencies import get_supabase
from ..schemas import Company

router = APIRouter()


@router.get("/{cik}", response_model=Company)
def get_company(cik: str, db: Client = Depends(get_supabase)):
    cik = cik.zfill(10)
    res = (
        db.table("companies")
        .select("cik,name,ticker,exchange,sic,sic_description")
        .eq("cik", cik)
        .single()
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Company not found")
    return res.data
