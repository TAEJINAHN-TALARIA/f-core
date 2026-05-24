import { getTranslations } from "next-intl/server";
import { getBalanceSheet, formatValue } from "@/lib/api";

const TAG_LABELS: Record<string, string> = {
  Assets: "assets",
  AssetsCurrent: "assets",
  Liabilities: "liabilities",
  LiabilitiesCurrent: "liabilities",
  LongTermDebt: "longTermDebt",
  StockholdersEquity: "equity",
  CashAndCashEquivalentsAtCarryingValue: "cash",
  RetainedEarningsAccumulatedDeficit: "equity",
  CommonStockSharesOutstanding: "assets",
};

const TAG_DISPLAY: Record<string, string> = {
  Assets: "Total Assets",
  AssetsCurrent: "Current Assets",
  Liabilities: "Total Liabilities",
  LiabilitiesCurrent: "Current Liabilities",
  LongTermDebt: "Long-term Debt",
  StockholdersEquity: "Stockholders' Equity",
  CashAndCashEquivalentsAtCarryingValue: "Cash & Equivalents",
  RetainedEarningsAccumulatedDeficit: "Retained Earnings",
  CommonStockSharesOutstanding: "Shares Outstanding",
};

const TAG_ORDER = [
  "Assets",
  "AssetsCurrent",
  "CashAndCashEquivalentsAtCarryingValue",
  "Liabilities",
  "LiabilitiesCurrent",
  "LongTermDebt",
  "StockholdersEquity",
  "RetainedEarningsAccumulatedDeficit",
  "CommonStockSharesOutstanding",
];

export default async function BalancePage({ params }: { params: Promise<{ cik: string }> }) {
  const { cik } = await params;
  const tp = await getTranslations("period");

  const [quarterly, annual] = await Promise.all([
    getBalanceSheet(cik, "quarterly"),
    getBalanceSheet(cik, "annual"),
  ]);

  function renderTable(data: typeof quarterly, periodLabel: string) {
    if (!data.length) return null;

    const ordered = TAG_ORDER.map((tag) => data.find((d) => d.tag === tag)).filter(Boolean) as typeof quarterly;
    const dates = [...new Set(ordered.flatMap((f) => f.data.map((p) => p.end_date)))]
      .sort()
      .slice(-8);

    return (
      <div className="mb-8">
        <h3 className="text-gray-300 font-semibold mb-3">{periodLabel}</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left text-gray-400 font-medium py-2 pr-4 min-w-[180px]">Item</th>
                {dates.map((d) => (
                  <th key={d} className="text-right text-gray-400 font-medium py-2 px-2 min-w-[90px]">
                    {d.slice(0, 7)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ordered.map((series) => {
                const label = TAG_DISPLAY[series.tag] ?? series.tag;
                const byDate = Object.fromEntries(series.data.map((p) => [p.end_date, p]));
                const isIndented = ["AssetsCurrent", "CashAndCashEquivalentsAtCarryingValue", "LiabilitiesCurrent", "LongTermDebt", "RetainedEarningsAccumulatedDeficit"].includes(series.tag);
                return (
                  <tr key={series.tag} className="border-b border-gray-800 hover:bg-gray-800/30">
                    <td className={`py-2 pr-4 text-gray-300 ${isIndented ? "pl-4 text-gray-400" : "font-medium"}`}>
                      {label}
                    </td>
                    {dates.map((d) => {
                      const point = byDate[d];
                      const val = point ? formatValue(point.value, series.unit) : "—";
                      const isNeg = point && point.value < 0;
                      return (
                        <td key={d} className={`py-2 px-2 text-right font-mono text-xs ${isNeg ? "text-red-400" : "text-gray-200"}`}>
                          {val}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {renderTable(quarterly, tp("quarterly"))}
      {renderTable(annual, tp("annual"))}
    </div>
  );
}
