const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { next: { revalidate: 300 } });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

export interface Company {
  cik: string;
  name: string;
  ticker: string | null;
  exchange: string | null;
  sic: string | null;
  sic_description: string | null;
}

export interface FactPoint {
  end_date: string;
  period_type: string;
  form: string | null;
  filed_date: string | null;
  value: number;
}

export interface FinancialsResponse {
  cik: string;
  tag: string;
  unit: string;
  data: FactPoint[];
}

export interface MetricPoint {
  end_date: string;
  period_type: string;
  metric: string;
  value: number;
}

export interface MetricsResponse {
  cik: string;
  data: MetricPoint[];
}

export interface TTMItem {
  tag: string;
  value: number;
  period_type: string;
}

export interface TTMResponse {
  cik: string;
  as_of: string;
  items: TTMItem[];
}

export interface Filing {
  form: string;
  filed_date: string | null;
  end_date: string;
  cik: string;
}

export interface FilingsResponse {
  cik: string;
  data: Filing[];
}

export function searchCompanies(q: string): Promise<Company[]> {
  return apiFetch(`/search?q=${encodeURIComponent(q)}&limit=10`);
}

export function getCompany(cik: string): Promise<Company> {
  return apiFetch(`/companies/${cik}`);
}

export function getFinancials(
  cik: string,
  period: "annual" | "quarterly" = "annual"
): Promise<FinancialsResponse[]> {
  return apiFetch(`/companies/${cik}/financials?period=${period}`);
}

export function getBalanceSheet(
  cik: string,
  period: "annual" | "quarterly" = "annual"
): Promise<FinancialsResponse[]> {
  return apiFetch(`/companies/${cik}/balance-sheet?period=${period}`);
}

export function getCashFlow(
  cik: string,
  period: "annual" | "quarterly" = "annual"
): Promise<FinancialsResponse[]> {
  return apiFetch(`/companies/${cik}/cash-flow?period=${period}`);
}

export function getMetrics(
  cik: string,
  period: "annual" | "quarterly" = "annual"
): Promise<MetricsResponse> {
  return apiFetch(`/companies/${cik}/metrics?period=${period}`);
}

export function getTTM(cik: string): Promise<TTMResponse> {
  return apiFetch(`/companies/${cik}/ttm`);
}

export function getFilings(cik: string, limit = 20): Promise<FilingsResponse> {
  return apiFetch(`/companies/${cik}/filings?limit=${limit}`);
}

export function formatValue(value: number, unit: string): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (unit === "USD/shares") return `$${value.toFixed(2)}`;
  if (unit === "USD") {
    if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(1)}B`;
    if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
    if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(1)}K`;
    return `${sign}$${abs.toFixed(0)}`;
  }
  if (unit === "shares") {
    if (abs >= 1e9) return `${sign}${(abs / 1e9).toFixed(2)}B`;
    if (abs >= 1e6) return `${sign}${(abs / 1e6).toFixed(2)}M`;
    return `${sign}${abs.toLocaleString()}`;
  }
  return value.toString();
}

/** 툴팁용: 콤마 구분 전체 숫자 (예: $94,930M / $1,234M) */
export function formatValueFull(value: number, unit: string): string {
  if (unit === "USD/shares") return `$${value.toFixed(2)}`;
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);
  if (unit === "USD") {
    if (abs >= 1e6) {
      return `${sign}$${Math.round(abs / 1e6).toLocaleString("en-US")}M`;
    }
    return `${sign}$${Math.round(abs).toLocaleString("en-US")}`;
  }
  if (unit === "shares") {
    return `${sign}${Math.round(abs).toLocaleString("en-US")}`;
  }
  return value.toLocaleString("en-US");
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}
