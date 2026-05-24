"use client";

import Link from "next/link";
import { usePathname, useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

interface Props {
  cik: string;
}

export default function CompanyNav({ cik }: Props) {
  const t = useTranslations("company");
  const pathname = usePathname();
  const params = useParams();
  const locale = params.locale as string;

  const base = `/${locale}/company/${cik}`;
  const tabs = [
    { label: t("overview"), href: base },
    { label: t("income"), href: `${base}/income` },
    { label: t("balance"), href: `${base}/balance` },
    { label: t("cashflow"), href: `${base}/cashflow` },
    { label: t("filings"), href: `${base}/filings` },
  ];

  return (
    <nav className="flex gap-0.5 mb-6 overflow-x-auto border-b border-gray-800 [&::-webkit-scrollbar]:hidden [scrollbar-width:none]">
      {tabs.map((tab) => {
        const active =
          tab.href === base
            ? pathname === base || pathname === `${base}/`
            : pathname.startsWith(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              "px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 -mb-px transition-colors",
              active
                ? "border-blue-500 text-blue-400"
                : "border-transparent text-gray-500 hover:text-gray-200 hover:border-gray-600"
            )}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
