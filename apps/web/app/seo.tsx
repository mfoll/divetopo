import type { Metadata } from "next";
import type { Language } from "../content/preferences";
import { pacaMapManifest } from "../content/regional";
import {
  absoluteUrl,
  defaultSitePath,
  languagePath,
  localizedSitePath,
  pacaPublishedSites,
  publishedSites,
  regionalSeoText,
  siteRepresentativeImages,
  siteSeoText,
  siteSocialImage,
  TOPO_REUNION_ORIGIN,
  type PublishedSite,
} from "../content/routing";
import type { RegionSlug } from "../content/regional";

function languageAlternates(
  slug?: string,
  region: RegionSlug = "reunion",
) {
  const frenchPath = slug
    ? localizedSitePath("fr", slug, region)
    : languagePath("fr", region);
  const englishPath = slug
    ? localizedSitePath("en", slug, region)
    : languagePath("en", region);
  const defaultPath = slug
    ? defaultSitePath(slug, region)
    : region === "paca"
      ? "/paca"
      : "/reunion";

  return {
    fr: absoluteUrl(frenchPath),
    en: absoluteUrl(englishPath),
    "x-default": absoluteUrl(defaultPath),
  };
}

function socialMetadata(
  language: Language,
  title: string,
  description: string,
  canonicalUrl: string,
  image: { src: string; width: number; height: number },
  imageAlt: string,
): Pick<Metadata, "openGraph" | "twitter"> {
  const imageUrl = absoluteUrl(image.src);

  return {
    openGraph: {
      title,
      description,
      siteName: "DiveTopo",
      locale: language === "fr" ? "fr_FR" : "en_GB",
      alternateLocale: language === "fr" ? ["en_GB"] : ["fr_FR"],
      type: "website",
      url: canonicalUrl,
      images: [
        {
          url: imageUrl,
          width: image.width,
          height: image.height,
          alt: imageAlt,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [{ url: imageUrl, alt: imageAlt }],
    },
  };
}

export function regionalMetadata(
  language: Language,
  region: RegionSlug = "reunion",
): Metadata {
  const text = regionalSeoText(language, region);
  const canonicalUrl = absoluteUrl(languagePath(language, region));
  const image =
    region === "paca"
      ? {
          src: pacaMapManifest.westCoastLocator.src,
          width: pacaMapManifest.westCoastLocator.width,
          height: pacaMapManifest.westCoastLocator.height,
        }
      : { src: "/reunion-og.png", width: 1200, height: 630 };

  return {
    title: text.title,
    description: text.description,
    alternates: {
      canonical: canonicalUrl,
      languages: languageAlternates(undefined, region),
    },
    robots: {
      index: true,
      follow: true,
    },
    ...socialMetadata(
      language,
      text.title,
      text.description,
      canonicalUrl,
      image,
      text.socialAlt,
    ),
  };
}

export function siteMetadata(
  language: Language,
  site: PublishedSite,
  region: RegionSlug = "reunion",
): Metadata {
  const text = siteSeoText(language, site, region);
  const regionalText = regionalSeoText(language, region);
  const canonicalUrl = absoluteUrl(
    localizedSitePath(language, site.slug, region),
  );
  const image = siteSocialImage(site);

  return {
    title: regionalText.title,
    description: text.description,
    alternates: {
      canonical: canonicalUrl,
      languages: languageAlternates(site.slug, region),
    },
    robots: {
      index: true,
      follow: true,
    },
    ...socialMetadata(
      language,
      text.title,
      text.description,
      canonicalUrl,
      image,
      text.socialAlt,
    ),
  };
}

function safeJson(value: unknown) {
  return JSON.stringify(value).replace(/</g, "\\u003c");
}

export function RegionalStructuredData({
  language,
  region = "reunion",
}: {
  language: Language;
  region?: RegionSlug;
}) {
  const text = regionalSeoText(language, region);
  const sites = region === "paca" ? pacaPublishedSites : publishedSites;
  const pageUrl = absoluteUrl(languagePath(language, region));

  const data = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebSite",
        "@id": `${TOPO_REUNION_ORIGIN}/#website`,
        name: "DiveTopo",
        url: `${TOPO_REUNION_ORIGIN}/`,
        inLanguage: ["fr", "en"],
      },
      {
        "@type": "CollectionPage",
        "@id": `${pageUrl}#webpage`,
        name: text.title,
        description: text.description,
        url: pageUrl,
        inLanguage: language,
        isPartOf: { "@id": `${TOPO_REUNION_ORIGIN}/#website` },
        mainEntity: {
          "@type": "ItemList",
          numberOfItems: sites.length,
          itemListElement: sites.map((site, index) => ({
            "@type": "ListItem",
            position: index + 1,
            name: site.displayName,
            url: absoluteUrl(localizedSitePath(language, site.slug, region)),
          })),
        },
      },
    ],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: safeJson(data) }}
    />
  );
}

export function SiteStructuredData({
  language,
  site,
  region = "reunion",
}: {
  language: Language;
  site: PublishedSite;
  region?: RegionSlug;
}) {
  const text = siteSeoText(language, site, region);
  const pageUrl = absoluteUrl(
    localizedSitePath(language, site.slug, region),
  );
  const regionName =
    region === "paca"
      ? "Côte d’Azur"
      : language === "fr"
        ? "La Réunion"
        : "Réunion Island";
  const placeName =
    `${site.displayName}, ${site.location.city}, ${regionName}`;
  const imageObjects = siteRepresentativeImages(language, site).map(
    (image, index) => ({
      "@type": "ImageObject",
      contentUrl: absoluteUrl(image.src),
      url: absoluteUrl(image.src),
      width: image.width,
      height: image.height,
      encodingFormat: "image/jpeg",
      caption: image.caption,
      creator: {
        "@type": "Person",
        name: site.plateAuthor,
      },
      creditText:
        `© ${site.copyrightYear} ${site.plateAuthor} · ${site.mapLicense}`,
      copyrightNotice:
        `© ${site.copyrightYear} ${site.plateAuthor}`,
      license:
        "https://creativecommons.org/licenses/by-nc-sa/4.0/",
      acquireLicensePage:
        "https://github.com/mfoll/divetopo/blob/main/LICENSE-MAPS.md",
      representativeOfPage: index === 1,
    }),
  );

  const data = {
    "@context": "https://schema.org",
    "@type": "Map",
    "@id": `${pageUrl}#map`,
    name: text.title,
    description: text.description,
    url: pageUrl,
    image: imageObjects,
    inLanguage: language,
    author: {
      "@type": "Person",
      name: "Matthieu Foll",
    },
    license:
      "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    spatialCoverage: {
      "@type": "Place",
      name: placeName,
      geo: {
        "@type": "GeoCoordinates",
        latitude: site.location.latitude,
        longitude: site.location.longitude,
      },
    },
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: safeJson(data) }}
    />
  );
}
