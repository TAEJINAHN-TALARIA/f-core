import { getTranslations } from "next-intl/server";
import { getTTM, getFinancials, getMetrics, formatValue, formatPercent } from "@/lib/api";
import MetricCard from "@/components/MetricCard";
import RevenueChart from "@/components/charts/RevenueChart";
import MarginChart from "@/components/charts/MarginChart";

export default async function CompanyOverviewPage({
  params,
}: {
  params: Promise<{ locale: string; cik: string }>;
}) {
  const { cik } = await params;
  const t = await getTranslations("metrics");
  const tp = await getTranslations("period");
  const tc = await getTranslations("company");

  const [ttm, financials, metricsRes] = await Promise.allSettled([
    getTTM(cik),
    getFinancials(cik, "quarterly"),
    getMetrics(cik, "quarterly"),
  ]);

  const ttmData = ttm.status === "fulfilled" ? ttm.value : null;
  const financialsData = financials.status === "fulfilled" ? financials.value : [];
  const metricsData = metricsRes.status === "fulfilled" ? metricsRes.value.data : [];

  function getTTMValue(tag: string) {
    return ttmData?.items.find((i) => i.tag === tag)?.value ?? null;
  }

  function getLatestMetric(metric: string) {
    const sorted = metricsData.filter((m) => m.metric === metric).sort((a, b) => b.end_date.localeCompare(a.end_date));
    return sorted[0]?.value ?? null;
  }

  const revenue = getTTMValue("Revenues") ?? getTTMValue("RevenueFromContractWithCustomerExcludingAssessedTax");
  const netIncome = getTTMValue("NetIncomeLoss");
  const epsDiluted = getTTMValue("EarningsPerShareDiluted");
  const grossMargin = getLatestMetric("gross_margin");
  const operatingMargin = getLatestMetric("operating_margin");
  const netMargin = getLatestMetric("net_margin");
  const roe = getLatestMetric("roe");
  const fcf = getLatestMetric("fcf");
  const interestCoverage = getLatestMetric("interest_coverage");
  const buybackToFcf = getLatestMetric("buyback_to_fcf");
  const buybacks = getTTMValue("PaymentsForRepurchaseOfCommonStock") ?? getTTMValue("PaymentsForRepurchaseOfEquity");
  const dividends = getTTMValue("PaymentsOfDividendsCommonStock") ?? getTTMValue("PaymentsOfDividends");

  const cards = [
    {
      label: `${t("revenue")} (${tp("ttm")})`,
      value: revenue != null ? formatValue(revenue, "USD") : "—",
    },
    {
      label: `${t("netIncome")} (${tp("ttm")})`,
      value: netIncome != null ? formatValue(netIncome, "USD") : "—",
      positive: netIncome != null ? netIncome >= 0 : null,
    },
    {
      label: `${t("eps")} (${tp("ttm")})`,
      value: epsDiluted != null ? formatValue(epsDiluted, "USD/shares") : "—",
      positive: epsDiluted != null ? epsDiluted >= 0 : null,
    },
    {
      label: t("grossMargin"),
      value: grossMargin != null ? formatPercent(grossMargin) : "—",
    },
    {
      label: t("operatingMargin"),
      value: operatingMargin != null ? formatPercent(operatingMargin) : "—",
      positive: operatingMargin != null ? operatingMargin >= 0 : null,
    },
    {
      label: t("netMargin"),
      value: netMargin != null ? formatPercent(netMargin) : "—",
      positive: netMargin != null ? netMargin >= 0 : null,
    },
    {
      label: t("roe"),
      value: roe != null ? formatPercent(roe) : "—",
      positive: roe != null ? roe >= 0 : null,
    },
    {
      label: `${t("fcf")} (${tp("ttm")})`,
      value: fcf != null ? formatValue(fcf, "USD") : "—",
      positive: fcf != null ? fcf >= 0 : null,
    },
    {
      label: t("interestCoverage"),
      value: interestCoverage != null ? `${interestCoverage.toFixed(1)}x` : "—",
      positive: interestCoverage != null ? interestCoverage >= 1.5 : null,
    },
    {
      label: `${t("buybacks")} (${tp("ttm")})`,
      value: buybacks != null ? formatValue(buybacks, "USD") : "—",
    },
    {
      label: `${t("dividends")} (${tp("ttm")})`,
      value: dividends != null ? formatValue(dividends, "USD") : "—",
    },
    {
      label: t("buybackToFcf"),
      value: buybackToFcf != null ? formatPercent(buybackToFcf) : "—",
    },
  ];

  return (
    <div className="space-y-8">
      {/* TTM Metric Cards */}
      <section>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {cards.map((card) => (
            <MetricCard key={card.label} {...card} />
          ))}
        </div>
        {ttmData?.as_of && (
          <p className="text-gray-600 text-xs mt-2">{tc("ttmNote")} · {tp("ttm")} as of {ttmData.as_of}</p>
        )}
      </section>

      {/* Revenue Chart */}
      {financialsData.length > 0 && (
        <section>
          <h2 className="text-gray-300 font-semibold mb-3">{t("revenue")} / {t("grossProfit")} / {t("netIncome")}</h2>
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <RevenueChart financials={financialsData} />
          </div>
        </section>
      )}

      {/* Margin Chart */}
      {metricsData.length > 0 && (
        <section>
          <h2 className="text-gray-300 font-semibold mb-3">{t("grossMargin")} / {t("operatingMargin")} / {t("netMargin")}</h2>
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <MarginChart metrics={metricsData} />
          </div>
        </section>
      )}
    </div>
  );
}
