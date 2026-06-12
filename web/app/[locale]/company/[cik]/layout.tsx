import type { Metadata } from "next";
import { getCompany } from "@/lib/api";
import CompanyNav from "@/components/CompanyNav";
import LocaleSwitcher from "@/components/LocaleSwitcher";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; cik: string }>;
}): Promise<Metadata> {
  const { locale, cik } = await params;
  try {
    const company = await getCompany(cik);
    const isKo = locale === "ko";
    const displayName = company.ticker
      ? `${company.name} (${company.ticker})`
      : company.name;
    const description = isKo
      ? `${displayName} 재무 데이터 — 손익계산서, 재무상태표, 현금흐름 (SEC EDGAR 공시)`
      : `${displayName} financial data — income statement, balance sheet, cash flow from SEC EDGAR`;

    return {
      title: displayName,
      description,
      ...(SITE_URL && {
        alternates: {
          canonical: `${SITE_URL}/${locale}/company/${cik}`,
          languages: {
            en: `${SITE_URL}/en/company/${cik}`,
            ko: `${SITE_URL}/ko/company/${cik}`,
            "x-default": `${SITE_URL}/en/company/${cik}`,
          },
        },
        openGraph: {
          title: `${displayName} | f-core`,
          description,
          url: `${SITE_URL}/${locale}/company/${cik}`,
        },
      }),
    };
  } catch {
    return { title: "Company" };
  }
}

export default async function CompanyLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string; cik: string }>;
}) {
  const { locale, cik } = await params;
  const company = await getCompany(cik);

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Corporation",
    "name": company.name,
    "tickerSymbol": company.ticker || undefined,
    "exchange": company.exchange || undefined,
    "description": company.sic_description || `${company.name} financial reports and key metrics.`,
    "identifier": company.cik,
    "url": `${SITE_URL}/${locale}/company/${cik}`,
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-950">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <header className="bg-gray-950 border-b border-gray-800 px-6 py-3 flex items-center justify-between">
        <Link href={`/${locale}`} className="font-bold text-gray-100 text-lg tracking-tight hover:text-blue-400 transition-colors">
          f-core
        </Link>
        <LocaleSwitcher />
      </header>

      <div className="max-w-6xl mx-auto w-full px-4 py-6 flex-1">
        <div className="mb-6">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold text-gray-100">{company.name}</h1>
            {company.ticker && (
              <Badge variant="secondary" className="font-mono text-blue-400 bg-blue-950/50 border border-blue-800 text-sm">
                {company.ticker}
              </Badge>
            )}
            {company.exchange && (
              <Badge variant="outline" className="text-gray-400 border-gray-700 text-xs">
                {company.exchange}
              </Badge>
            )}
          </div>
          {company.sic_description && (
            <p className="text-gray-500 text-sm mt-1">{company.sic_description}</p>
          )}
        </div>

        <CompanyNav cik={cik} />
        {children}
      </div>
    </div>
  );
}
