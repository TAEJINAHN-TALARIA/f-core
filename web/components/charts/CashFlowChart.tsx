"use client";

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
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
  cashflow: FinancialsResponse[];
}

const TAG_KEY: Record<string, string> = {
  NetCashProvidedByUsedInOperatingActivities: "operatingCF",
  NetCashProvidedByUsedInInvestingActivities: "investingCF",
  NetCashProvidedByUsedInFinancingActivities: "financingCF",
  PaymentsToAcquirePropertyPlantAndEquipment: "capex",
};

const COLORS: Record<string, string> = {
  operatingCF: "#3b82f6",
  investingCF: "#f59e0b",
  financingCF: "#6b7280",
  capex:       "#ef4444",
};

function fmtDate(d: string) {
  try {
    return new Date(`${d}-15`).toLocaleDateString("en", { year: "numeric", month: "short" });
  } catch {
    return d;
  }
}

export default function CashFlowChart({ cashflow }: Props) {
  const tc = useTranslations("chart");
  const tm = useTranslations("metrics");

  const chartConfig = {
    operatingCF: { label: tm("operatingCF"), color: COLORS.operatingCF },
    investingCF: { label: tm("investingCF"), color: COLORS.investingCF },
    financingCF: { label: tm("financingCF"), color: COLORS.financingCF },
    capex:       { label: tm("capex"),       color: COLORS.capex },
  } satisfies ChartConfig;

  const dateMap: Record<string, Record<string, number>> = {};
  for (const series of cashflow) {
    const key = TAG_KEY[series.tag];
    if (!key) continue;
    for (const point of series.data) {
      dateMap[point.end_date] ??= {};
      dateMap[point.end_date][key] =
        series.tag === "PaymentsToAcquirePropertyPlantAndEquipment"
          ? -Math.abs(point.value)
          : point.value;
    }
  }

  const data = Object.entries(dateMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-12)
    .map(([date, vals]) => ({ date: date.slice(0, 7), ...vals }));

  if (!data.length) {
    return <p className="text-gray-400 text-sm text-center py-8">{tc("noData")}</p>;
  }

  const barKeys = (["operatingCF", "investingCF", "financingCF"] as const).filter(
    (k) => data.some((d) => k in d)
  );
  const hasCapex = data.some((d) => "capex" in d);

  return (
    <ChartContainer config={chartConfig} className="h-[300px] w-full">
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
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
          tick={{ fill: "#9ca3af", fontSize: 11 }}
          tickFormatter={(v) => formatValue(v, "USD").replace("$", "")}
        />
        <YAxis
          yAxisId="right"
          orientation="right"
          tickLine={false}
          axisLine={false}
          tick={{ fill: "#9ca3af", fontSize: 11 }}
          tickFormatter={(v) => formatValue(v, "USD").replace("$", "")}
        />
        <ReferenceLine y={0} yAxisId="left" stroke="#374151" strokeDasharray="4 2" />
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
        {barKeys.map((key) => (
          <Bar key={key} yAxisId="left" dataKey={key} fill={COLORS[key]} radius={[3, 3, 0, 0]} maxBarSize={28} />
        ))}
        {hasCapex && (
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="capex"
            stroke={COLORS.capex}
            strokeWidth={2.5}
            dot={{ r: 3, fill: COLORS.capex, strokeWidth: 0 }}
            activeDot={{ r: 6, strokeWidth: 2, stroke: "#fff", fill: COLORS.capex }}
          />
        )}
      </ComposedChart>
    </ChartContainer>
  );
}
