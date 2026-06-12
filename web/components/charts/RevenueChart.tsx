"use client";

import {
  ComposedChart,
  Area,
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
        <CartesianGrid vertical={false} stroke="#e5e7eb" />
        <XAxis
          dataKey="date"
          tickLine={false}
          axisLine={false}
          tick={{ fill: "#6b7280", fontSize: 11 }}
          tickFormatter={fmtDate}
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          tick={{ fill: "#6b7280", fontSize: 11 }}
          tickFormatter={(v) => formatValue(v, "USD").replace("$", "")}
        />
        <ReferenceLine y={0} stroke="#9ca3af" strokeDasharray="4 2" />
        <ChartTooltip
          contentStyle={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 8 }}
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
          <Area
            type="monotone"
            dataKey="revenue"
            stroke={COLORS.revenue}
            strokeWidth={2}
            fill="url(#grad-revenue)"
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0, fill: COLORS.revenue }}
          />
        )}
        
        {presentKeys.includes("operatingIncome") && (
          <Bar
            dataKey="operatingIncome"
            fill={COLORS.operatingIncome}
            radius={[3, 3, 0, 0]}
            maxBarSize={18}
          />
        )}
        
        {presentKeys.includes("netIncome") && (
          <Bar
            dataKey="netIncome"
            fill={COLORS.netIncome}
            radius={[3, 3, 0, 0]}
            maxBarSize={18}
          />
        )}
      </ComposedChart>
    </ChartContainer>
  );
}
