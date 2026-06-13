from typing import Optional
from pydantic import BaseModel


class Company(BaseModel):
    cik: str
    name: str
    ticker: Optional[str] = None
    exchange: Optional[str] = None
    sic: Optional[str] = None
    sic_description: Optional[str] = None


class FactPoint(BaseModel):
    end_date: str
    period_type: str
    form: Optional[str] = None
    filed_date: Optional[str] = None
    value: float


class MetricPoint(BaseModel):
    end_date: str
    period_type: str
    metric: str
    value: float


class FinancialsResponse(BaseModel):
    cik: str
    tag: str
    unit: str
    data: list[FactPoint]


class MetricsResponse(BaseModel):
    cik: str
    data: list[MetricPoint]


class TTMItem(BaseModel):
    tag: str
    value: float
    period_type: str = "ttm"


class TTMResponse(BaseModel):
    cik: str
    as_of: str
    items: list[TTMItem]


class Filing(BaseModel):
    form: str
    filed_date: Optional[str] = None
    end_date: str
    cik: str


class FilingsResponse(BaseModel):
    cik: str
    data: list[Filing]


class ThemeCompany(BaseModel):
    cik: str
    name: str
    ticker: Optional[str] = None
    exchange: Optional[str] = None
    sic: Optional[str] = None
    sic_description: Optional[str] = None
    value: float
    history: Optional[list[float]] = None
