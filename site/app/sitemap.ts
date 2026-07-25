import type { MetadataRoute } from "next";
import {
  absoluteUrl,
  defaultSitePath,
  languagePath,
  localizedSitePath,
  publishedSites,
  siteSocialImage,
} from "../content/routing";

export default function sitemap(): MetadataRoute.Sitemap {
  const overviewLanguages = {
    fr: absoluteUrl(languagePath("fr")),
    en: absoluteUrl(languagePath("en")),
    "x-default": absoluteUrl("/"),
  };

  const overviewEntries: MetadataRoute.Sitemap = [
    {
      url: overviewLanguages.fr,
      changeFrequency: "monthly",
      priority: 1,
      alternates: { languages: overviewLanguages },
    },
    {
      url: overviewLanguages.en,
      changeFrequency: "monthly",
      priority: 1,
      alternates: { languages: overviewLanguages },
    },
  ];

  const siteEntries = publishedSites.flatMap((site) => {
    const languages = {
      fr: absoluteUrl(localizedSitePath("fr", site.slug)),
      en: absoluteUrl(localizedSitePath("en", site.slug)),
      "x-default": absoluteUrl(defaultSitePath(site.slug)),
    };

    return [
      {
        url: languages.fr,
        changeFrequency: "monthly" as const,
        priority: 0.8,
        alternates: { languages },
        images: [absoluteUrl(siteSocialImage(site).src)],
      },
      {
        url: languages.en,
        changeFrequency: "monthly" as const,
        priority: 0.8,
        alternates: { languages },
        images: [absoluteUrl(siteSocialImage(site).src)],
      },
    ];
  });

  return [...overviewEntries, ...siteEntries];
}
