"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter, usePathname } from "next/navigation";

export default function LocaleSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations("nav");

  function switchLocale(next: string) {
    // Replace /en/... with /ko/... or vice versa
    const newPath = pathname.replace(`/${locale}`, `/${next}`);
    router.push(newPath);
  }

  return (
    <div className="flex items-center gap-1 text-sm">
      <span className="text-gray-400 mr-1">{t("language")}:</span>
      {(["en", "ko"] as const).map((l) => (
        <button
          key={l}
          onClick={() => switchLocale(l)}
          className={`px-2 py-0.5 rounded transition-colors ${
            locale === l
              ? "bg-blue-600 text-white"
              : "text-gray-400 hover:text-white"
          }`}
        >
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
