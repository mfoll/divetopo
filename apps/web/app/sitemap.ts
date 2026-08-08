import type { MetadataRoute } from "next";
import {
  absoluteUrl,
  defaultSitePath,
  languagePath,
  localizedSitePath,
  publishedSitesForRegion,
  siteRepresentativeImages,
} from "../content/routing";
import { LANGUAGES } from "../content/preferences";
import { publicRegions } from "../content/region-catalog";
import { regionalMapManifests } from "../content/regional";

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

  const regionEntries: MetadataRoute.Sitemap = publicRegions.flatMap(
    (region) => {
      const languages = {
        fr: absoluteUrl(languagePath("fr", region)),
        en: absoluteUrl(languagePath("en", region)),
        "x-default": absoluteUrl(`/${region}`),
      };
      const manifest = regionalMapManifests[region];
      const image =
        region === "reunion"
          ? "/reunion-og.png"
          : manifest.westCoastLocator.src;
      return LANGUAGES.map((language) => ({
        url: absoluteUrl(languagePath(language, region)),
        changeFrequency: "monthly" as const,
        priority: 0.9,
        images: [absoluteUrl(image)],
        alternates: { languages },
      }));
    },
  );

  const siteEntries: MetadataRoute.Sitemap = publicRegions.flatMap(
    (region) =>
      publishedSitesForRegion(region).flatMap((site) => {
        const languages = {
          fr: absoluteUrl(localizedSitePath("fr", site.slug, region)),
          en: absoluteUrl(localizedSitePath("en", site.slug, region)),
          "x-default": absoluteUrl(defaultSitePath(site.slug, region)),
        };
        const images = siteRepresentativeImages("fr", site).map((image) =>
          absoluteUrl(image.src),
        );
        return LANGUAGES.map((language) => ({
          url: absoluteUrl(localizedSitePath(language, site.slug, region)),
          changeFrequency: "monthly" as const,
          priority: 0.8,
          alternates: { languages },
          images,
        }));
      }),
  );

  return [
    ...homepageEntries,
    ...regionEntries,
    ...siteEntries,
  ];
}
