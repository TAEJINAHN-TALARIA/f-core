"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useTranslations, useLocale } from "next-intl";
import { useRouter } from "next/navigation";
import { searchCompanies, type Company } from "@/lib/api";

export default function CompanySearch() {
  const t = useTranslations("home");
  const locale = useLocale();
  const router = useRouter();

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Company[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const search = useCallback(async (q: string) => {
    if (q.trim().length < 1) {
      setResults([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    try {
      const data = await searchCompanies(q.trim());
      setResults(data);
      setOpen(true);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(query), 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, search]);

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function navigate(company: Company) {
    setOpen(false);
    setQuery("");
    router.push(`/${locale}/company/${company.cik}`);
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-2xl mx-auto">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("searchPlaceholder")}
          className="w-full px-4 py-3 pl-11 rounded-xl bg-gray-800 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-base"
        />
        <svg
          className="absolute left-3.5 top-3.5 w-5 h-5 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        {loading && (
          <div className="absolute right-3 top-3.5 w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
        )}
      </div>

      {open && results.length > 0 && (
        <ul className="absolute z-50 w-full mt-1 bg-gray-800 border border-gray-700 rounded-xl shadow-xl overflow-hidden">
          {results.map((company) => (
            <li key={company.cik}>
              <button
                onClick={() => navigate(company)}
                className="w-full px-4 py-3 text-left hover:bg-gray-700 transition-colors flex items-center gap-3"
              >
                <span className="font-mono text-blue-400 text-sm font-bold w-16 shrink-0">
                  {company.ticker ?? "—"}
                </span>
                <span className="text-white text-sm truncate">{company.name}</span>
                {company.exchange && (
                  <span className="ml-auto text-gray-500 text-xs shrink-0">
                    {company.exchange}
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
