import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: "https://divetopo.com/sitemap.xml",
    host: "https://divetopo.com",
  };
}
