import type { Metadata } from "next";
import type { Language } from "../content/preferences";
import {
  absoluteUrl,
  defaultSitePath,
  languagePath,
  localizedSitePath,
  publishedSites,
  regionalSeoText,
  siteRepresentativeImages,
  siteSeoText,
  siteSocialImage,
  TOPO_REUNION_ORIGIN,
} from "../content/routing";

type PublishedSite = (typeof publishedSites)[number];

function languageAlternates(slug?: string) {
  const frenchPath = slug
    ? localizedSitePath("fr", slug)
    : languagePath("fr");
  const englishPath = slug
    ? localizedSitePath("en", slug)
    : languagePath("en");
  const defaultPath = slug ? defaultSitePath(slug) : "/";

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

export function regionalMetadata(language: Language): Metadata {
  const text = regionalSeoText(language);
  const canonicalUrl = absoluteUrl(languagePath(language));
  const image = { src: "/og.png", width: 1200, height: 630 };

  return {
    title: text.title,
    description: text.description,
    alternates: {
      canonical: canonicalUrl,
      languages: languageAlternates(),
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
): Metadata {
  const text = siteSeoText(language, site);
  const canonicalUrl = absoluteUrl(
    localizedSitePath(language, site.slug),
  );
  const image = siteSocialImage(site);

  return {
    title: text.title,
    description: text.description,
    alternates: {
      canonical: canonicalUrl,
      languages: languageAlternates(site.slug),
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
}: {
  language: Language;
}) {
  const text = regionalSeoText(language);
  const pageUrl = absoluteUrl(languagePath(language));

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
          numberOfItems: publishedSites.length,
          itemListElement: publishedSites.map((site, index) => ({
            "@type": "ListItem",
            position: index + 1,
            name: site.displayName,
            url: absoluteUrl(localizedSitePath(language, site.slug)),
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
}: {
  language: Language;
  site: PublishedSite;
}) {
  const text = siteSeoText(language, site);
  const pageUrl = absoluteUrl(localizedSitePath(language, site.slug));
  const placeName =
    language === "fr"
      ? `${site.displayName}, ${site.location.city}, La Réunion`
      : `${site.displayName}, ${site.location.city}, Réunion Island`;
  const imageObjects = siteRepresentativeImages(language, site).map(
    (image, index) => ({
      "@type": "ImageObject",
      contentUrl: absoluteUrl(image.src),
      url: absoluteUrl(image.src),
      width: image.width,
      height: image.height,
      encodingFormat: "image/webp",
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
        "https://github.com/mfoll/reunion-topobathy/blob/main/LICENSE-MAPS.md",
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
