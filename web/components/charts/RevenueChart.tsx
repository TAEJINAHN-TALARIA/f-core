"use client";

import {
  ComposedChart,
  Area,
  Bar,
  Line,
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

const PRIORITY = [
  "Revenues",
  "RevenueFromContractWithCustomerExcludingAssessedTax",
  "OperatingIncomeLoss",
  "NetIncomeLoss",
];

const TAG_KEY: Record<string, string> = {
  Revenues: "revenue",
  RevenueFromContractWithCustomerExcludingAssessedTax: "revenue",
  OperatingIncomeLoss: "operatingIncome",
  NetIncomeLoss: "netIncome",
};

const COLORS: Record<string, string> = {
  revenue:         "#3b82f6",
  operatingIncome: "#10b981",
  netIncome:       "#8b5cf6",
};

function buildChartData(financials: FinancialsResponse[]) {
  const available = financials.filter((f) => PRIORITY.includes(f.tag));
  const hasRevenues = available.some((f) => f.tag === "Revenues");
  const filtered = available.filter(
    (f) => f.tag !== "RevenueFromContractWithCustomerExcludingAssessedTax" || !hasRevenues
  );

  const dateMap: Record<string, Record<string, number>> = {};
  for (const series of filtered) {
    const key = TAG_KEY[series.tag];
    if (!key) continue;
    for (const point of series.data) {
      dateMap[point.end_date] ??= {};
      dateMap[point.end_date][key] = point.value;
    }
  }

  return Object.entries(dateMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-12)
    .map(([date, vals]) => ({ date: date.slice(0, 7), ...vals }));
}

function fmtDate(d: string) {
  try {
    return new Date(`${d}-15`).toLocaleDateString("en", { year: "numeric", month: "short" });
  } catch {
    return d;
  }
}

export default function RevenueChart({ financials }: Props) {
  const tc = useTranslations("chart");
  const tm = useTranslations("metrics");

  const chartConfig = {
    revenue:         { label: tm("revenue"),         color: COLORS.revenue },
    operatingIncome: { label: tm("operatingIncome"),  color: COLORS.operatingIncome },
    netIncome:       { label: tm("netIncome"),        color: COLORS.netIncome },
  } satisfies ChartConfig;

  const data = buildChartData(financials);

  const presentKeys = (Object.keys(chartConfig) as (keyof typeof chartConfig)[]).filter(
    (k) => data.some((d) => k in d)
  );

  if (!data.length) {
    return <p className="text-gray-400 text-sm text-center py-8">{tc("noData")}</p>;
  }

  return (
    <ChartContainer config={chartConfig} className="h-[300px] w-full">
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
        <defs>
          <linearGradient id="grad-revenue" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor={COLORS.revenue} stopOpacity={0.2} />
            <stop offset="95%" stopColor={COLORS.revenue} stopOpacity={0} />
          </linearGradient>
        </defs>
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
          yAxisId="left"
          tickLine={false}
          axisLine={false}
          tick={{ fill: COLORS.revenue, fontSize: 11, fontWeight: 600 }}
          tickFormatter={(v) => formatValue(v, "USD").replace("$", "")}
        />
        <YAxis
          yAxisId="right"
          orientation="right"
          tickLine={false}
          axisLine={false}
          tick={{ fill: COLORS.operatingIncome, fontSize: 11, fontWeight: 600 }}
          tickFormatter={(v) => formatValue(v, "USD").replace("$", "")}
        />
        <ReferenceLine y={0} yAxisId="right" stroke="#374151" strokeDasharray="4 2" />
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
        
        {presentKeys.includes("revenue") && (
          <Bar
            yAxisId="left"
            dataKey="revenue"
            fill={COLORS.revenue}
            radius={[4, 4, 0, 0]}
            maxBarSize={36}
            opacity={0.75}
          />
        )}
        
        {presentKeys.includes("operatingIncome") && (
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="operatingIncome"
            stroke={COLORS.operatingIncome}
            strokeWidth={3}
            dot={{ r: 3, fill: COLORS.operatingIncome, strokeWidth: 0 }}
            activeDot={{ r: 6, strokeWidth: 2, stroke: "#fff", fill: COLORS.operatingIncome }}
          />
        )}
        
        {presentKeys.includes("netIncome") && (
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="netIncome"
            stroke={COLORS.netIncome}
            strokeWidth={3}
            dot={{ r: 3, fill: COLORS.netIncome, strokeWidth: 0 }}
            activeDot={{ r: 6, strokeWidth: 2, stroke: "#fff", fill: COLORS.netIncome }}
          />
        )}
      </ComposedChart>
    </ChartContainer>
  );
}
