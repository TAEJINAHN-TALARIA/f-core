import { useTranslations } from "next-intl";
import CompanySearch from "@/components/CompanySearch";
import LocaleSwitcher from "@/components/LocaleSwitcher";
import ThemedShowcase from "@/components/ThemedShowcase";

export default async function HomePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = useTranslations("home");

  return (
    <main className="min-h-screen flex flex-col bg-background relative overflow-hidden">
      {/* 장식용 은은한 radial-gradient 광원 (가독성 영향 없음) */}
      <div className="absolute top-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-[radial-gradient(circle,rgba(59,130,246,0.025)_0%,rgba(0,0,0,0)_70%)] pointer-events-none" />
      <div className="absolute bottom-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-[radial-gradient(circle,rgba(139,92,246,0.02)_0%,rgba(0,0,0,0)_70%)] pointer-events-none" />

      <header className="bg-background/80 backdrop-blur-md border-b border-border px-6 py-3 flex items-center justify-between z-10">
        <span className="font-bold text-gray-100 text-lg tracking-tight hover:text-blue-400 transition-colors">
          f-core
        </span>
        <LocaleSwitcher />
      </header>

      <div className="flex-1 flex flex-col items-center justify-start px-4 py-16 sm:py-24 gap-8 z-10 overflow-y-auto">
        <div className="text-center">
          <h1 className="text-4xl font-extrabold text-gray-100 tracking-tight mb-3">
            {t("title")}
          </h1>
          <p className="text-gray-400 text-sm max-w-md mx-auto">
            {t("subtitle")}
          </p>
        </div>
        
        <div className="w-full max-w-xl flex flex-col items-center gap-2">
          <CompanySearch />
          <p className="text-gray-600 text-[11px] mt-1">{t("searchHint")}</p>
        </div>

        {/* 가치투자 테마별 기업 추천 쇼케이스 */}
        <ThemedShowcase locale={locale} />
      </div>
    </main>
  );
}
