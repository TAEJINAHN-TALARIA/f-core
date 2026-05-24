import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
def health():
    return {"status": "ok"}
