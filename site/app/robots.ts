import type { MetadataRoute } from "next";
import { TOPO_REUNION_ORIGIN } from "../content/routing";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: `${TOPO_REUNION_ORIGIN}/sitemap.xml`,
    host: TOPO_REUNION_ORIGIN,
  };
}
