import type { Metadata } from "next";
import { notFound } from "next/navigation";
import HomepageExperience from "../HomepageExperience";
import { getPreferences } from "../preferences";
import { homepageCopy } from "../../content/homepage-copy";
import {
  LANGUAGES,
  isLanguage,
  type Language,
} from "../../content/preferences";

const origin = "https://divetopo.com";

const metadataCopy = {
  fr: {
    title: "DiveTopo · Cartes de sites de plongée",
    socialTitle: "DiveTopo · Cartographies de sites de plongée",
    socialDescription:
      "Des plans 2D, perspectives 3D et reliefs interactifs de sites de plongée.",
    socialAlt: "DiveTopo, cartographies de sites de plongée",
    locale: "fr_FR",
  },
  en: {
    title: "DiveTopo · Dive site maps",
    socialTitle: "DiveTopo · Dive site maps",
    socialDescription:
      "2D maps, 3D views and interactive terrain for selected dive sites.",
    socialAlt: "DiveTopo, dive site maps",
    locale: "en_GB",
  },
} as const;

function localizedUrl(language: Language) {
  return `${origin}/${language}`;
}

function resolveLanguage(value: string): Language {
  if (!isLanguage(value)) {
    notFound();
  }

  return value;
}

export function generateStaticParams() {
  return LANGUAGES.map((language) => ({ language }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ language: string }>;
}): Promise<Metadata> {
  const language = resolveLanguage((await params).language);
  const text = metadataCopy[language];

  return {
    title: text.title,
    description: homepageCopy[language].metadataDescription,
    alternates: {
      canonical: localizedUrl(language),
      languages: {
        fr: localizedUrl("fr"),
        en: localizedUrl("en"),
        "x-default": `${origin}/`,
      },
    },
    openGraph: {
      title: text.socialTitle,
      description: text.socialDescription,
      locale: text.locale,
      type: "website",
      url: localizedUrl(language),
      images: [
        {
          url: "/og.png",
          width: 1200,
          height: 630,
          alt: text.socialAlt,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: text.socialTitle,
      description: text.socialDescription,
      images: [{ url: "/og.png", alt: text.socialAlt }],
    },
  };
}

export default async function LocalizedHomepage({
  params,
}: {
  params: Promise<{ language: string }>;
}) {
  const [{ language: requestedLanguage }, { theme }] = await Promise.all([
    params,
    getPreferences(),
  ]);
  const language = resolveLanguage(requestedLanguage);
  const canonicalUrl = localizedUrl(language);
  const overviewImageUrl = `${origin}/og.png`;
  const overviewImageId = `${overviewImageUrl}#image`;
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": `${origin}/#organization`,
        name: "DiveTopo",
        url: `${origin}/`,
        logo: `${origin}/app-icon-512.png`,
      },
      {
        "@type": "WebSite",
        "@id": `${origin}/#website`,
        url: `${origin}/`,
        name: "DiveTopo",
        publisher: { "@id": `${origin}/#organization` },
      },
      {
        "@type": "WebPage",
        "@id": `${canonicalUrl}#webpage`,
        url: canonicalUrl,
        name: homepageCopy[language].documentTitle,
        description: homepageCopy[language].metadataDescription,
        inLanguage: language,
        isPartOf: { "@id": `${origin}/#website` },
        primaryImageOfPage: { "@id": overviewImageId },
      },
      {
        "@type": "ImageObject",
        "@id": overviewImageId,
        contentUrl: overviewImageUrl,
        url: overviewImageUrl,
        width: 1200,
        height: 630,
        encodingFormat: "image/png",
        caption:
          language === "fr"
            ? "Relief terrestre et sous-marin de l’île de La Réunion."
            : "Land and underwater terrain around Réunion Island.",
        creator: {
          "@type": "Person",
          name: "Matthieu Foll",
        },
        creditText: "DiveTopo",
        copyrightNotice: "© 2026 Matthieu Foll",
        license:
          "https://creativecommons.org/licenses/by-nc-sa/4.0/deed.en",
        acquireLicensePage:
          "https://github.com/mfoll/divetopo/blob/main/LICENSE-MAPS.md",
      },
    ],
  };

  return (
    <>
      <script
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c"),
        }}
        type="application/ld+json"
      />
      <HomepageExperience language={language} theme={theme} />
    </>
  );
}
