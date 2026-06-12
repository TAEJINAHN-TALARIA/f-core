import { getTranslations } from "next-intl/server";
import { getFinancials, formatValue } from "@/lib/api";
import RevenueChart from "@/components/charts/RevenueChart";

const INCOME_TAG_LABELS: Record<string, string> = {
  Revenues: "revenue",
  RevenueFromContractWithCustomerExcludingAssessedTax: "revenue",
  GrossProfit: "grossProfit",
  OperatingIncomeLoss: "operatingIncome",
  NetIncomeLoss: "netIncome",
  EarningsPerShareDiluted: "eps",
  EarningsPerShareBasic: "epsBasic",
  ResearchAndDevelopmentExpense: "fcf",
  InterestExpense: "fcf",
};

export default async function IncomePage({ params }: { params: Promise<{ cik: string }> }) {
  const { cik } = await params;
  const t = await getTranslations("metrics");
  const tp = await getTranslations("period");

  const [quarterly, annual] = await Promise.all([
    getFinancials(cik, "quarterly"),
    getFinancials(cik, "annual"),
  ]);

  function renderTable(data: typeof quarterly, periodLabel: string) {
    if (!data.length) return null;

    const tagOrder = [
      "Revenues",
      "RevenueFromContractWithCustomerExcludingAssessedTax",
      "GrossProfit",
      "OperatingIncomeLoss",
      "NetIncomeLoss",
      "EarningsPerShareDiluted",
      "EarningsPerShareBasic",
    ];

    const filtered = tagOrder
      .map((tag) => data.find((d) => d.tag === tag))
      .filter(Boolean) as typeof quarterly;

    const hasRevenues = filtered.some((f) => f.tag === "Revenues");
    const deduped = filtered.filter(
      (f) => f.tag !== "RevenueFromContractWithCustomerExcludingAssessedTax" || !hasRevenues
    );

    const dates = [...new Set(deduped.flatMap((f) => f.data.map((p) => p.end_date)))]
      .sort()
      .slice(-8);

    return (
      <div className="mb-8">
        <h3 className="text-gray-300 font-semibold mb-3">{periodLabel}</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left text-gray-400 font-medium py-2 pr-4 min-w-[140px]">Metric</th>
                {dates.map((d) => (
                  <th key={d} className="text-right text-gray-400 font-medium py-2 px-2 min-w-[90px]">
                    {d.slice(0, 7)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {deduped.map((series) => {
                const labelKey = INCOME_TAG_LABELS[series.tag];
                const label = labelKey ? t(labelKey as Parameters<typeof t>[0]) : series.tag;
                const byDate = Object.fromEntries(series.data.map((p) => [p.end_date, p]));
                return (
                  <tr key={series.tag} className="border-b border-gray-800 hover:bg-gray-800/30">
                    <td className="py-2 pr-4 text-gray-300">{label}</td>
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
      <div className="bg-card rounded-xl p-4 border border-border shadow-md">
        <RevenueChart financials={quarterly} />
      </div>
      {renderTable(quarterly, tp("quarterly"))}
      {renderTable(annual, tp("annual"))}
    </div>
  );
}
