import type { MetadataRoute } from "next";
import {
  absoluteUrl,
  defaultSitePath,
  languagePath,
  localizedSitePath,
  publishedSites,
  siteRepresentativeImages,
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
    const images = siteRepresentativeImages("fr", site).map((image) =>
      absoluteUrl(image.src),
    );

    return [
      {
        url: languages.fr,
        changeFrequency: "monthly" as const,
        priority: 0.8,
        alternates: { languages },
        images,
      },
      {
        url: languages.en,
        changeFrequency: "monthly" as const,
        priority: 0.8,
        alternates: { languages },
        images,
      },
    ];
  });

  return [...overviewEntries, ...siteEntries];
}
