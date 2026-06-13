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
  { id: "fcf-positive-10yr", labelKey: "fcfPositive10yr", descKey: "fcfPositive10yrDesc" },
  { id: "buyback-growth-5yr", labelKey: "buybackGrowth5yr", descKey: "buybackGrowth5yrDesc" },
  { id: "zero-debt-safe", labelKey: "zeroDebtSafe", descKey: "zeroDebtSafeDesc" },
  { id: "roe-consistent-10yr", labelKey: "roeConsistent10yr", descKey: "roeConsistent10yrDesc" },
  { id: "deleveraging-5yr", labelKey: "deleveraging5yr", descKey: "deleveraging5yrDesc" },
  { id: "shareholder-payout-high", labelKey: "shareholderPayoutHigh", descKey: "shareholderPayoutHighDesc" },
  { id: "fcf-to-revenue-high", labelKey: "fcfToRevenueHigh", descKey: "fcfToRevenueHighDesc" },
];

export default function ThemedShowcase({ locale }: Props) {
  const t = useTranslations("home.themedShowcase");
  const [activeTab, setActiveTab] = useState("operating-margin-growth");
  const [companies, setCompanies] = useState<ThemeCompany[]>([]);
  const [isPending, startTransition] = useTransition();
  const [isPaused, setIsPaused] = useState(false);

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

  // 10초 간격 자동 롤링 타이머
  useEffect(() => {
    if (isPaused) return;

    const interval = setInterval(() => {
      setActiveTab((prev) => {
        const idx = THEMES.findIndex((t) => t.id === prev);
        const nextIdx = (idx + 1) % THEMES.length;
        return THEMES[nextIdx].id;
      });
    }, 10000); // 10초

    return () => clearInterval(interval);
  }, [isPaused, activeTab]);

  function renderValue(item: ThemeCompany) {
    if (activeTab === "operating-margin-growth") {
      return (
        <span className="text-emerald-400 font-bold font-mono text-xs">
          {item.value}%
        </span>
      );
    }
    if (activeTab === "dividend-growth" || activeTab === "buyback-growth-5yr" || activeTab === "fcf-positive-10yr") {
      const colorClass = 
        activeTab === "dividend-growth" ? "text-amber-400" :
        activeTab === "buyback-growth-5yr" ? "text-blue-400" : "text-emerald-400";
      return (
        <span className={cn("font-bold font-mono text-xs", colorClass)}>
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
    if (activeTab === "zero-debt-safe") {
      return (
        <span className="text-sky-400 font-bold font-mono text-xs">
          부채 {item.value}%
        </span>
      );
    }
    if (activeTab === "roe-consistent-10yr") {
      return (
        <span className="text-amber-400 font-bold font-mono text-xs">
          ROE {item.value}%
        </span>
      );
    }
    if (activeTab === "deleveraging-5yr") {
      return (
        <span className="text-cyan-400 font-bold font-mono text-xs">
          부채 {item.value}%
        </span>
      );
    }
    if (activeTab === "shareholder-payout-high") {
      return (
        <span className="text-rose-400 font-bold font-mono text-xs">
          {item.value}%
        </span>
      );
    }
    if (activeTab === "fcf-to-revenue-high") {
      return (
        <span className="text-indigo-400 font-bold font-mono text-xs">
          {item.value}%
        </span>
      );
    }
    return null;
  }

  function getLatestLabel() {
    if (activeTab === "operating-margin-growth") return t("latestMargin");
    if (activeTab === "dividend-growth") return t("latestDividend");
    if (activeTab === "high-roe") return t("latestRoe");
    if (activeTab === "fcf-positive-10yr") return t("latestFcf");
    if (activeTab === "buyback-growth-5yr") return t("latestBuyback");
    if (activeTab === "zero-debt-safe") return t("latestDebtToEquity");
    if (activeTab === "roe-consistent-10yr") return t("latestRoe");
    if (activeTab === "deleveraging-5yr") return t("latestDebtToEquity");
    if (activeTab === "shareholder-payout-high") return t("latestPayoutRatio");
    if (activeTab === "fcf-to-revenue-high") return t("latestFcfMargin");
    return "";
  }

  return (
    <div 
      className="w-full max-w-4xl px-4 mt-8 space-y-6"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <div className="text-center sm:text-left">
        <h2 className="text-lg font-bold text-gray-200 tracking-tight">{t("title")}</h2>
        <p className="text-xs text-gray-500 mt-1">
          {t(THEMES.find((th) => th.id === activeTab)?.descKey as any)}
        </p>
      </div>

      {/* Tabs list */}
      <div className="flex flex-nowrap items-center gap-2 border-b border-border/40 pb-3 overflow-x-auto scrollbar-none snap-x">
        {THEMES.map((theme) => (
          <button
            key={theme.id}
            onClick={() => setActiveTab(theme.id)}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs font-semibold tracking-tight transition-all duration-200 cursor-pointer snap-center shrink-0",
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
