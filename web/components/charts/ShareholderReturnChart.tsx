"use client";

import {
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  ReferenceLine,
} from "recharts";
import { useTranslations } from "next-intl";
import type { FinancialsResponse } from "@/lib/api";
import { formatValue, formatValueFull } from "@/lib/api";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  type ChartConfig,
} from "@/components/ui/chart";

interface Props {
  financials: FinancialsResponse[];
}

import conceptMapData from "../../lib/concept_map.json";

const conceptMap = conceptMapData as Record<string, { tags: string[], category: string }>;

const BUYBACK_TAGS = conceptMap["stock_repurchase"]?.tags || [];
const DIVIDEND_TAGS = conceptMap["dividends_paid"]?.tags || [];

const COLORS = {
  buybacks:  "#f59e0b", // 주황 (자사주 매입)
  dividends: "#3b82f6", // 파랑 (배당)
};

function buildChartData(financials: FinancialsResponse[]) {
  const dateMap: Record<string, { buybacks?: number; dividends?: number }> = {};

  for (const series of financials) {
    const isBuyback = BUYBACK_TAGS.includes(series.tag);
    const isDividend = DIVIDEND_TAGS.includes(series.tag);
    if (!isBuyback && !isDividend) continue;

    const key = isBuyback ? "buybacks" : "dividends";

    for (const point of series.data) {
      const date = point.end_date;
      dateMap[date] ??= {};
      // CaPex처럼 현금흐름 상의 유출이므로 음수로 기입되었을 수 있으나, 주주환원은 절대값으로 양수 시각화가 일반적임
      const val = Math.abs(point.value);
      dateMap[date][key] = (dateMap[date][key] ?? 0) + val;
    }
  }

  return Object.entries(dateMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-12)
    .map(([date, vals]) => ({
      date: date.slice(0, 7),
      buybacks: vals.buybacks ?? 0,
      dividends: vals.dividends ?? 0,
    }));
}

function fmtDate(d: string) {
  try {
    return new Date(`${d}-15`).toLocaleDateString("en", { year: "numeric", month: "short" });
  } catch {
    return d;
  }
}

export default function ShareholderReturnChart({ financials }: Props) {
  const tc = useTranslations("chart");
  const tm = useTranslations("metrics");

  const chartConfig = {
    buybacks:  { label: tm("buybacks"),  color: COLORS.buybacks },
    dividends: { label: tm("dividends"), color: COLORS.dividends },
  } satisfies ChartConfig;

  const data = buildChartData(financials);

  if (!data.length || !data.some((d) => d.buybacks > 0 || d.dividends > 0)) {
    return <p className="text-gray-400 text-sm text-center py-8">{tc("noData")}</p>;
  }

  return (
    <ChartContainer config={chartConfig} className="h-[300px] w-full">
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
        <CartesianGrid vertical={false} stroke="#1a1d27" />
        <XAxis
          dataKey="date"
          tickLine={false}
          axisLine={false}
          tick={{ fill: "#9ca3af", fontSize: 11 }}
          tickFormatter={fmtDate}
          padding={{ left: 12, right: 12 }}
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          tick={{ fill: "#9ca3af", fontSize: 11 }}
          tickFormatter={(v) => formatValue(v, "USD").replace("$", "")}
        />
        <ReferenceLine y={0} stroke="#374151" strokeDasharray="4 2" />
        <ChartTooltip
          cursor={{ stroke: "#1a1d27" }}
          content={
            <ChartTooltipContent
              labelFormatter={fmtDate}
              formatter={(value, name) => [
                formatValueFull(Number(value), "USD"),
                chartConfig[name as keyof typeof chartConfig]?.label ?? String(name),
              ]}
            />
          }
        />
        <ChartLegend content={<ChartLegendContent />} />
        
        {/* Stacked Bars for shareholder return */}
        <Bar
          dataKey="dividends"
          fill={COLORS.dividends}
          stackId="a"
          radius={[0, 0, 0, 0]}
          maxBarSize={24}
        />
        <Bar
          dataKey="buybacks"
          fill={COLORS.buybacks}
          stackId="a"
          radius={[3, 3, 0, 0]}
          maxBarSize={24}
        />
      </BarChart>
    </ChartContainer>
  );
}
