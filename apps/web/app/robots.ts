import type { MetadataRoute } from "next";
import { DIVETOPO_ORIGIN } from "../content/routing";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: `${DIVETOPO_ORIGIN}/sitemap.xml`,
    host: DIVETOPO_ORIGIN,
  };
}
