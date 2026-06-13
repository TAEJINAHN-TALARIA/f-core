import type { MetadataRoute } from "next";

const rawSiteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://f-core-omega.vercel.app";
const SITE_URL = rawSiteUrl.endsWith("/") ? rawSiteUrl.slice(0, -1) : rawSiteUrl;

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: SITE_URL ? `${SITE_URL}/sitemap.xml` : undefined,
  };
}
