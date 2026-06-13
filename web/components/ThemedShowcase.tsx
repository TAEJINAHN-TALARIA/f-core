"use client";

import { useEffect, useState, useTransition, useRef } from "react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { getThemeCompanies, type ThemeCompany, formatValue } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  locale: string;
}

const THEMES = [
  { id: "high-roe-low-debt", labelKey: "highRoeLowDebt", descKey: "highRoeLowDebtDesc" },
  { id: "dividend-growth-5yr", labelKey: "dividendGrowth5yr", descKey: "dividendGrowth5yrDesc" },
  { id: "fcf-positive-10yr", labelKey: "fcfPositive10yr", descKey: "fcfPositive10yrDesc" },
  { id: "shareholder-return-high-3yr", labelKey: "shareholderReturnHigh3yr", descKey: "shareholderReturnHigh3yrDesc" },
  { id: "roe-consistent-7yr", labelKey: "roeConsistent7yr", descKey: "roeConsistent7yrDesc" },
  { id: "fcf-margin-high-industry", labelKey: "fcfMarginHighIndustry", descKey: "fcfMarginHighIndustryDesc" },
  { id: "fcf-margin-growth-3yr", labelKey: "fcfMarginGrowth3yr", descKey: "fcfMarginGrowth3yrDesc" },
  { id: "earnings-quality-high", labelKey: "earningsQualityHigh", descKey: "earningsQualityHighDesc" },
  { id: "zero-debt-strict", labelKey: "zeroDebtStrict", descKey: "zeroDebtStrictDesc" },
];

export default function ThemedShowcase({ locale }: Props) {
  const t = useTranslations("home.themedShowcase");
  const [activeTab, setActiveTab] = useState("high-roe-low-debt");
  const [companies, setCompanies] = useState<ThemeCompany[]>([]);
  const [isPending, startTransition] = useTransition();
  const [isPaused, setIsPaused] = useState(false);
  const tabsRef = useRef<HTMLDivElement>(null);

  const scrollTabs = (direction: "left" | "right") => {
    if (tabsRef.current) {
      const scrollAmount = 200;
      tabsRef.current.scrollBy({
        left: direction === "left" ? -scrollAmount : scrollAmount,
        behavior: "smooth",
      });
    }
  };

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
    if (activeTab === "high-roe-low-debt") {
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
    if (activeTab === "dividend-growth-5yr" || activeTab === "fcf-positive-10yr") {
      const colorClass = activeTab === "dividend-growth-5yr" ? "text-amber-400" : "text-emerald-400";
      return (
        <span className={cn("font-bold font-mono text-xs", colorClass)}>
          {formatValue(item.value, "USD")}
        </span>
      );
    }
    if (activeTab === "shareholder-return-high-3yr") {
      return (
        <span className="text-rose-400 font-bold font-mono text-xs">
          {item.value}%
        </span>
      );
    }
    if (activeTab === "roe-consistent-7yr") {
      return (
        <span className="text-amber-400 font-bold font-mono text-xs">
          ROE {item.value}%
        </span>
      );
    }
    if (activeTab === "fcf-margin-high-industry" || activeTab === "fcf-margin-growth-3yr") {
      const colorClass = activeTab === "fcf-margin-high-industry" ? "text-indigo-400" : "text-sky-400";
      return (
        <span className={cn("font-bold font-mono text-xs", colorClass)}>
          {item.value}%
        </span>
      );
    }
    if (activeTab === "earnings-quality-high") {
      return (
        <span className="text-teal-400 font-bold font-mono text-xs">
          {item.value}%
        </span>
      );
    }
    if (activeTab === "zero-debt-strict") {
      return (
        <span className="text-sky-400 font-bold font-mono text-xs">
          부채 {item.value}%
        </span>
      );
    }
    return null;
  }

  function getLatestLabel() {
    if (activeTab === "high-roe-low-debt") return t("latestRoe");
    if (activeTab === "dividend-growth-5yr") return t("latestDividend");
    if (activeTab === "fcf-positive-10yr") return t("latestFcf");
    if (activeTab === "shareholder-return-high-3yr") return t("avgPayoutRatio");
    if (activeTab === "roe-consistent-7yr") return t("latestRoe");
    if (activeTab === "fcf-margin-high-industry") return t("latestFcfMargin");
    if (activeTab === "fcf-margin-growth-3yr") return t("latestFcfMargin");
    if (activeTab === "earnings-quality-high") return t("avgEarningsQuality");
    if (activeTab === "zero-debt-strict") return t("latestDebtToEquity");
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

      {/* Tabs list with Arrow Navigators */}
      <div className="relative w-full group/arrows">
        {/* Left Arrow */}
        <button
          onClick={() => scrollTabs("left")}
          className="absolute left-0 top-1/2 -translate-y-1/2 -ml-3 z-10 p-1.5 bg-card/90 border border-border rounded-full text-gray-400 hover:text-gray-200 hover:bg-secondary transition-all opacity-0 group-hover/arrows:opacity-100 focus:opacity-100 cursor-pointer shadow-lg hover:scale-105 active:scale-95 duration-200"
          aria-label="Scroll Left"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        {/* Tabs Scroll Area */}
        <div
          ref={tabsRef}
          className="flex flex-nowrap items-center gap-2 border-b border-border/40 pb-3 overflow-x-auto scrollbar-none snap-x px-3 scroll-smooth"
        >
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

        {/* Right Arrow */}
        <button
          onClick={() => scrollTabs("right")}
          className="absolute right-0 top-1/2 -translate-y-1/2 -mr-3 z-10 p-1.5 bg-card/90 border border-border rounded-full text-gray-400 hover:text-gray-200 hover:bg-secondary transition-all opacity-0 group-hover/arrows:opacity-100 focus:opacity-100 cursor-pointer shadow-lg hover:scale-105 active:scale-95 duration-200"
          aria-label="Scroll Right"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
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
