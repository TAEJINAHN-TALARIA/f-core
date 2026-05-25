import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi import Depends
from supabase import Client

from .dependencies import get_supabase
from .routers import companies, financials, search

load_dotenv()

app = FastAPI(title="f-core API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(search.router, tags=["search"])
app.include_router(companies.router, prefix="/companies", tags=["companies"])
app.include_router(financials.router, prefix="/companies", tags=["financials"])


@app.get("/health")
def health(db: Client = Depends(get_supabase)):
    res = (
        db.table("etl_runs")
        .select("run_id,started_at,finished_at,status,companies,facts,metrics")
        .eq("status", "success")
        .order("finished_at", desc=True)
        .limit(1)
        .execute()
    )
    last_etl = res.data[0] if res.data else None
    return {"status": "ok", "last_etl": last_etl}
