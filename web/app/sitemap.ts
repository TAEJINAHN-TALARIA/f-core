import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const LOCALES = ["en", "ko"] as const;

async function fetchCompanyCiks(): Promise<string[]> {
  const PAGE = 500;
  const ciks: string[] = [];
  let offset = 0;

  while (true) {
    try {
      const res = await fetch(
        `${API_URL}/companies?limit=${PAGE}&offset=${offset}`,
        { next: { revalidate: 86400 } }
      );
      if (!res.ok) break;
      const data: { cik: string }[] = await res.json();
      ciks.push(...data.map((c) => c.cik));
      if (data.length < PAGE) break;
      offset += PAGE;
    } catch {
      break;
    }
  }

  return ciks;
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
        languages: {
          en: `${SITE_URL}/en`,
          ko: `${SITE_URL}/ko`,
          "x-default": `${SITE_URL}/en`,
        },
      },
    },
    {
      url: `${SITE_URL}/ko`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1,
      alternates: {
        languages: {
          en: `${SITE_URL}/en`,
          ko: `${SITE_URL}/ko`,
          "x-default": `${SITE_URL}/en`,
        },
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
        "x-default": `${SITE_URL}/en/company/${cik}`,
      },
    },
  }));

  return [...homePages, ...companyPages];
}
