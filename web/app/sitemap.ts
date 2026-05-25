import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const LOCALES = ["en", "ko"] as const;

async function fetchCompanyCiks(): Promise<string[]> {
  try {
    const res = await fetch(`${API_URL}/companies?limit=10000`, {
      next: { revalidate: 86400 },
    });
    if (!res.ok) return [];
    const data: { cik: string }[] = await res.json();
    return data.map((c) => c.cik);
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  if (!SITE_URL) return [];

  const ciks = await fetchCompanyCiks();

  const homePages: MetadataRoute.Sitemap = [
    {
      url: `${SITE_URL}/en`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1,
      alternates: {
        languages: { en: `${SITE_URL}/en`, ko: `${SITE_URL}/ko` },
      },
    },
  ];

  const companyPages: MetadataRoute.Sitemap = ciks.map((cik) => ({
    url: `${SITE_URL}/en/company/${cik}`,
    changeFrequency: "weekly" as const,
    priority: 0.7,
    alternates: {
      languages: {
        en: `${SITE_URL}/en/company/${cik}`,
        ko: `${SITE_URL}/ko/company/${cik}`,
      },
    },
  }));

  return [...homePages, ...companyPages];
}
