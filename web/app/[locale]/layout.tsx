import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import "../globals.css";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const isKo = locale === "ko";

  const title = isKo ? "f-core | 미국 주식 재무 데이터" : "f-core | US Stock Financials";
  const description = isKo
    ? "SEC EDGAR 공시 데이터 기반 미국 주식 재무 정보"
    : "SEC EDGAR filing data for US market investors";

  return {
    title: { template: `%s | f-core`, default: title },
    description,
    ...(SITE_URL && {
      alternates: {
        canonical: `${SITE_URL}/${locale}`,
        languages: { en: `${SITE_URL}/en`, ko: `${SITE_URL}/ko` },
      },
      openGraph: {
        type: "website",
        locale: isKo ? "ko_KR" : "en_US",
        url: `${SITE_URL}/${locale}`,
        siteName: "f-core",
        title,
        description,
      },
    }),
  };
}

export async function generateStaticParams() {
  return [{ locale: "en" }, { locale: "ko" }];
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const messages = await getMessages();

  return (
    <html lang={locale}>
      <body className="min-h-screen bg-gray-950 text-gray-100 antialiased">
        <NextIntlClientProvider messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
