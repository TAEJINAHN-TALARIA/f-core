"use client";

import { useEffect, useState, useTransition } from "react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { getThemeCompanies, type ThemeCompany, formatValue } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  locale: string;
}

const THEMES = [
  { id: "operating-margin-growth", labelKey: "operatingMarginGrowth", descKey: "operatingMarginGrowthDesc" },
  { id: "dividend-growth", labelKey: "dividendGrowth", descKey: "dividendGrowthDesc" },
  { id: "high-roe", labelKey: "highRoe", descKey: "highRoeDesc" },
];

export default function ThemedShowcase({ locale }: Props) {
  const t = useTranslations("home.themedShowcase");
  const [activeTab, setActiveTab] = useState("operating-margin-growth");
  const [companies, setCompanies] = useState<ThemeCompany[]>([]);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    startTransition(async () => {
      try {
        const data = await getThemeCompanies(activeTab, 8);
        setCompanies(data);
      } catch (err) {
        console.error("Failed to fetch themed companies", err);
        setCompanies([]);
      }
    });
  }, [activeTab]);

  function renderValue(item: ThemeCompany) {
    if (activeTab === "operating-margin-growth") {
      return (
        <span className="text-emerald-400 font-bold font-mono text-xs">
          {item.value}%
        </span>
      );
    }
    if (activeTab === "dividend-growth") {
      return (
        <span className="text-amber-400 font-bold font-mono text-xs">
          {formatValue(item.value, "USD")}
        </span>
      );
    }
    if (activeTab === "high-roe") {
      const roe = item.value;
      const debt = item.history && item.history[1] != null ? item.history[1] : null;
      return (
        <div className="flex flex-col items-end">
          <span className="text-emerald-400 font-bold font-mono text-xs">ROE {roe}%</span>
          {debt != null && (
            <span className="text-gray-500 text-[9px] font-mono mt-0.5">
              부채: {debt}%
            </span>
          )}
        </div>
      );
    }
    return null;
  }

  function getLatestLabel() {
    if (activeTab === "operating-margin-growth") return t("latestMargin");
    if (activeTab === "dividend-growth") return t("latestDividend");
    if (activeTab === "high-roe") return t("latestRoe");
    return "";
  }

  return (
    <div className="w-full max-w-4xl px-4 mt-8 space-y-6">
      <div className="text-center sm:text-left">
        <h2 className="text-lg font-bold text-gray-200 tracking-tight">{t("title")}</h2>
        <p className="text-xs text-gray-500 mt-1">
          {t(THEMES.find((th) => th.id === activeTab)?.descKey as any)}
        </p>
      </div>

      {/* Tabs list */}
      <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 border-b border-border/40 pb-3">
        {THEMES.map((theme) => (
          <button
            key={theme.id}
            onClick={() => setActiveTab(theme.id)}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs font-semibold tracking-tight transition-all duration-200 cursor-pointer",
              activeTab === theme.id
                ? "bg-blue-600 text-white shadow-md shadow-blue-900/30"
                : "text-gray-400 hover:text-gray-200 bg-secondary hover:bg-secondary/80"
            )}
          >
            {t(theme.labelKey as any)}
          </button>
        ))}
      </div>

      {/* Showcase Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        {isPending
          ? Array.from({ length: 4 }).map((_, idx) => (
              <div
                key={idx}
                className="bg-card border border-border/60 rounded-xl p-4 space-y-3 animate-pulse h-[110px]"
              >
                <div className="h-3 w-16 bg-gray-800 rounded" />
                <div className="h-4 w-32 bg-gray-800 rounded" />
                <div className="h-3 w-24 bg-gray-800 rounded" />
              </div>
            ))
          : companies.length > 0
          ? companies.map((item) => (
              <Link
                key={item.cik}
                href={`/${locale}/company/${item.cik}`}
                className="group bg-card border border-border hover:border-blue-500/40 hover:-translate-y-0.5 transition-all duration-300 rounded-xl p-4 shadow-md hover:shadow-blue-950/20 flex flex-col justify-between h-[118px] select-none"
              >
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-blue-400 tracking-wider uppercase">
                      {item.ticker || "N/A"}
                    </span>
                    <span className="text-[9px] text-gray-500 tracking-tight">
                      {item.exchange || "SEC"}
                    </span>
                  </div>
                  <h3 className="font-bold text-gray-200 text-xs tracking-tight line-clamp-1 group-hover:text-blue-400 transition-colors">
                    {item.name}
                  </h3>
                  {item.sic_description && (
                    <p className="text-[9px] text-gray-500 line-clamp-1">
                      {item.sic_description}
                    </p>
                  )}
                </div>

                <div className="flex items-end justify-between border-t border-border/40 pt-2 mt-2">
                  <span className="text-[9px] text-gray-400 font-medium">
                    {getLatestLabel()}
                  </span>
                  {renderValue(item)}
                </div>
              </Link>
            ))
          : (
            <div className="col-span-full py-12 text-center">
              <p className="text-sm text-gray-500">{t("noThemeData")}</p>
            </div>
          )}
      </div>
    </div>
  );
}
