import type { MetadataRoute } from "next";
import {
  absoluteUrl,
  defaultSitePath,
  languagePath,
  localizedSitePath,
  publishedSites,
  siteRepresentativeImages,
} from "../content/routing";
import { LANGUAGES } from "../content/preferences";

const origin = "https://divetopo.com";

function homepageUrl(language: "fr" | "en") {
  return `${origin}/${language}`;
}

export default function sitemap(): MetadataRoute.Sitemap {
  const homepageLanguages = {
    fr: homepageUrl("fr"),
    en: homepageUrl("en"),
    "x-default": `${origin}/`,
  };
  const homepageEntries: MetadataRoute.Sitemap = LANGUAGES.map(
    (language) => ({
      url: homepageUrl(language),
      changeFrequency: "monthly",
      priority: 1,
      images: [`${origin}/og.png`],
      alternates: { languages: homepageLanguages },
    }),
  );

  const reunionLanguages = {
    fr: absoluteUrl(languagePath("fr")),
    en: absoluteUrl(languagePath("en")),
    "x-default": absoluteUrl("/reunion"),
  };
  const reunionEntries: MetadataRoute.Sitemap = LANGUAGES.map(
    (language) => ({
      url: absoluteUrl(languagePath(language)),
      changeFrequency: "monthly",
      priority: 0.9,
      images: [`${origin}/reunion-og.png`],
      alternates: { languages: reunionLanguages },
    }),
  );

  const siteEntries = publishedSites.flatMap((site) => {
    const languages = {
      fr: absoluteUrl(localizedSitePath("fr", site.slug)),
      en: absoluteUrl(localizedSitePath("en", site.slug)),
      "x-default": absoluteUrl(defaultSitePath(site.slug)),
    };
    const images = siteRepresentativeImages("fr", site).map((image) =>
      absoluteUrl(image.src),
    );

    return LANGUAGES.map((language) => ({
      url: absoluteUrl(localizedSitePath(language, site.slug)),
      changeFrequency: "monthly" as const,
      priority: 0.8,
      alternates: { languages },
      images,
    }));
  });

  return [...homepageEntries, ...reunionEntries, ...siteEntries];
}
