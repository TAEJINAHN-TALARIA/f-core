"use client";

import { Line, LineChart, CartesianGrid, XAxis, YAxis, ReferenceLine } from "recharts";
import { useTranslations } from "next-intl";
import type { MetricPoint } from "@/lib/api";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  type ChartConfig,
} from "@/components/ui/chart";

interface Props {
  metrics: MetricPoint[];
}

const COLORS: Record<string, string> = {
  gross_margin:     "#10b981",
  operating_margin: "#f59e0b",
  net_margin:       "#8b5cf6",
};

const METRIC_KEYS = ["gross_margin", "operating_margin", "net_margin"] as const;
type MetricKey = (typeof METRIC_KEYS)[number];

const I18N_KEY: Record<MetricKey, string> = {
  gross_margin:     "grossMargin",
  operating_margin: "operatingMargin",
  net_margin:       "netMargin",
};

function fmtDate(d: string) {
  try {
    return new Date(`${d}-15`).toLocaleDateString("en", { year: "numeric", month: "short" });
  } catch {
    return d;
  }
}

export default function MarginChart({ metrics }: Props) {
  const tc = useTranslations("chart");
  const tm = useTranslations("metrics");

  const chartConfig = {
    gross_margin:     { label: tm(I18N_KEY.gross_margin),     color: COLORS.gross_margin },
    operating_margin: { label: tm(I18N_KEY.operating_margin), color: COLORS.operating_margin },
    net_margin:       { label: tm(I18N_KEY.net_margin),       color: COLORS.net_margin },
  } satisfies ChartConfig;

  const dateMap: Record<string, Record<string, number>> = {};
  for (const m of metrics) {
    if (!(m.metric in chartConfig)) continue;
    dateMap[m.end_date] ??= {};
    dateMap[m.end_date][m.metric] = m.value * 100;
  }

  const data = Object.entries(dateMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-12)
    .map(([date, vals]) => ({ date: date.slice(0, 7), ...vals }));

  const presentKeys = METRIC_KEYS.filter((k) => data.some((d) => k in d));

  if (!data.length) {
    return <p className="text-gray-400 text-sm text-center py-8">{tc("noData")}</p>;
  }

  return (
    <ChartContainer config={chartConfig} className="h-[300px] w-full">
      <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
        <defs>
          {presentKeys.map((key) => (
            <linearGradient key={key} id={`mgrad-${key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={COLORS[key]} stopOpacity={0.15} />
              <stop offset="95%" stopColor={COLORS[key]} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid vertical={false} stroke="#1a1d27" />
        <XAxis
          dataKey="date"
          tickLine={false}
          axisLine={false}
          tick={{ fill: "#9ca3af", fontSize: 11 }}
          tickFormatter={fmtDate}
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          tick={{ fill: "#9ca3af", fontSize: 11 }}
          tickFormatter={(v) => `${v.toFixed(0)}%`}
        />
        <ReferenceLine y={0} stroke="#374151" strokeDasharray="4 2" />
        <ChartTooltip
          cursor={{ stroke: "#1a1d27" }}
          content={
            <ChartTooltipContent
              labelFormatter={fmtDate}
              formatter={(value, name) => [
                `${Number(value).toFixed(1)}%`,
                chartConfig[name as keyof typeof chartConfig]?.label ?? String(name),
              ]}
            />
          }
        />
        <ChartLegend content={<ChartLegendContent />} />
        {presentKeys.map((key) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            stroke={COLORS[key]}
            strokeWidth={2.5}
            dot={{ r: 3, fill: COLORS[key], strokeWidth: 0 }}
            activeDot={{ r: 6, strokeWidth: 2, stroke: "#fff", fill: COLORS[key] }}
          />
        ))}
      </LineChart>
    </ChartContainer>
  );
}
