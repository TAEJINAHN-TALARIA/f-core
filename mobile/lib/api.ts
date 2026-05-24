const BASE = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
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

export interface TTMItem {
  tag: string;
  value: number;
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

export function searchCompanies(q: string): Promise<Company[]> {
  return apiFetch(`/search?q=${encodeURIComponent(q)}&limit=10`);
}

export function getCompany(cik: string): Promise<Company> {
  return apiFetch(`/companies/${cik}`);
}

export function getFinancials(cik: string, period: "annual" | "quarterly" = "quarterly"): Promise<FinancialsResponse[]> {
  return apiFetch(`/companies/${cik}/financials?period=${period}`);
}

export function getMetrics(cik: string, period: "annual" | "quarterly" = "quarterly"): Promise<{ cik: string; data: MetricPoint[] }> {
  return apiFetch(`/companies/${cik}/metrics?period=${period}`);
}

export function getTTM(cik: string): Promise<TTMResponse> {
  return apiFetch(`/companies/${cik}/ttm`);
}

export function getFilings(cik: string, limit = 20): Promise<{ cik: string; data: Filing[] }> {
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
  return value.toString();
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}
