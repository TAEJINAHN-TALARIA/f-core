import { getTranslations } from "next-intl/server";
import { getTTM, getFinancials, getCashFlow, getMetrics, formatValue, formatPercent } from "@/lib/api";
import MetricCard from "@/components/MetricCard";
import RevenueChart from "@/components/charts/RevenueChart";
import MarginChart from "@/components/charts/MarginChart";
import ShareholderReturnChart from "@/components/charts/ShareholderReturnChart";

export default async function CompanyOverviewPage({
  params,
}: {
  params: Promise<{ locale: string; cik: string }>;
}) {
  const { cik } = await params;
  const t = await getTranslations("metrics");
  const tp = await getTranslations("period");
  const tc = await getTranslations("company");

  const [ttm, financials, cashflow, metricsRes] = await Promise.allSettled([
    getTTM(cik),
    getFinancials(cik, "annual"),
    getCashFlow(cik, "annual"),
    getMetrics(cik, "annual"),
  ]);

  const ttmData = ttm.status === "fulfilled" ? ttm.value : null;
  const financialsData = financials.status === "fulfilled" ? financials.value : [];
  const cashflowData = cashflow.status === "fulfilled" ? cashflow.value : [];
  const metricsData = metricsRes.status === "fulfilled" ? metricsRes.value.data : [];

  function getTTMValue(tag: string) {
    return ttmData?.items.find((i) => i.tag === tag)?.value ?? null;
  }

  function getLatestMetric(metric: string) {
    const sorted = metricsData.filter((m) => m.metric === metric).sort((a, b) => b.end_date.localeCompare(a.end_date));
    return sorted[0]?.value ?? null;
  }

  const revenue = getTTMValue("Revenues") ?? getTTMValue("RevenueFromContractWithCustomerExcludingAssessedTax");
  const operatingMargin = getLatestMetric("operating_margin");
  const roe = getLatestMetric("roe");
  const fcf = getLatestMetric("fcf");
  const debtToEquity = getLatestMetric("debt_to_equity");
  const interestCoverage = getLatestMetric("interest_coverage");
  const interestExpense = getTTMValue("InterestExpense");
  const operatingIncome = getTTMValue("OperatingIncomeLoss");
  const buybacks = getTTMValue("PaymentsForRepurchaseOfCommonStock") ?? getTTMValue("PaymentsForRepurchaseOfEquity");
  const dividends = getTTMValue("PaymentsOfDividendsCommonStock") ?? getTTMValue("PaymentsOfDividends");
  const shareholderReturn = (buybacks != null || dividends != null) ? (buybacks ?? 0) + (dividends ?? 0) : null;

  // 이자보상배율 예외처리 (무차입 우량기업 처리)
  let interestCoverageStr = "—";
  let interestCoveragePositive: boolean | null = null;
  if (interestCoverage != null) {
    interestCoverageStr = `${interestCoverage.toFixed(1)}x`;
    interestCoveragePositive = interestCoverage >= 1.5;
  } else if (operatingIncome != null && operatingIncome >= 0 && (interestExpense == null || interestExpense <= 0)) {
    interestCoverageStr = t("safeDebtFree");
    interestCoveragePositive = true;
  }

  const cards = [
    {
      label: `${t("revenue")} (${tp("annual")})`,
      value: revenue != null ? formatValue(revenue, "USD") : "—",
    },
    {
      label: t("operatingMargin"),
      value: operatingMargin != null ? formatPercent(operatingMargin) : "—",
      positive: operatingMargin != null ? operatingMargin >= 0 : null,
    },
    {
      label: t("roe"),
      value: roe != null ? formatPercent(roe) : "—",
      positive: roe != null ? roe >= 0 : null,
    },
    {
      label: `${t("fcf")} (${tp("annual")})`,
      value: fcf != null ? formatValue(fcf, "USD") : "—",
      positive: fcf != null ? fcf >= 0 : null,
    },
    {
      label: t("debtToEquity"),
      value: debtToEquity != null ? formatPercent(debtToEquity) : "—",
      positive: debtToEquity != null ? debtToEquity <= 1.0 : null,
    },
    {
      label: t("interestCoverage"),
      value: interestCoverageStr,
      positive: interestCoveragePositive,
    },
    {
      label: `${t("shareholderReturn")} (${tp("annual")})`,
      value: shareholderReturn != null ? formatValue(shareholderReturn, "USD") : "—",
      positive: shareholderReturn != null ? shareholderReturn >= 0 : null,
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
          <h2 className="text-gray-300 font-semibold mb-3">{t("revenue")} / {t("operatingIncome")} / {t("netIncome")}</h2>
          <div className="bg-card rounded-xl p-4 border border-border shadow-md">
            <RevenueChart financials={financialsData} />
          </div>
        </section>
      )}

      {/* Margin Chart */}
      {metricsData.length > 0 && (
        <section>
          <h2 className="text-gray-300 font-semibold mb-3">{t("grossMargin")} / {t("operatingMargin")} / {t("netMargin")}</h2>
          <div className="bg-card rounded-xl p-4 border border-border shadow-md">
            <MarginChart metrics={metricsData} />
          </div>
        </section>
      )}

      {/* Shareholder Return Chart */}
      {cashflowData.length > 0 && (
        <section>
          <h2 className="text-gray-300 font-semibold mb-3">{t("buybacks")} / {t("dividends")} ({tp("annual")})</h2>
          <div className="bg-card rounded-xl p-4 border border-border shadow-md">
            <ShareholderReturnChart financials={cashflowData} />
          </div>
        </section>
      )}
    </div>
  );
}
