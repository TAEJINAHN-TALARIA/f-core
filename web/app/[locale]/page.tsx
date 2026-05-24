import { useTranslations } from "next-intl";
import CompanySearch from "@/components/CompanySearch";
import LocaleSwitcher from "@/components/LocaleSwitcher";

export default function HomePage() {
  const t = useTranslations("home");
  const tn = useTranslations("nav");

  return (
    <main className="min-h-screen flex flex-col bg-gray-950">
      <header className="bg-gray-950 border-b border-gray-800 px-6 py-3 flex items-center justify-between">
        <span className="font-bold text-gray-100 text-lg tracking-tight">f-core</span>
        <LocaleSwitcher />
      </header>

      <div className="flex-1 flex flex-col items-center justify-center px-4 py-16 gap-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-100 mb-2">{t("title")}</h1>
          <p className="text-gray-400">{t("subtitle")}</p>
        </div>
        <CompanySearch />
        <p className="text-gray-600 text-sm">{t("searchHint")}</p>
      </div>
    </main>
  );
}
