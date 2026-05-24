import { getCompany } from "@/lib/api";
import CompanyNav from "@/components/CompanyNav";
import LocaleSwitcher from "@/components/LocaleSwitcher";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

export default async function CompanyLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string; cik: string }>;
}) {
  const { locale, cik } = await params;
  const company = await getCompany(cik);

  return (
    <div className="min-h-screen flex flex-col bg-gray-950">
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
