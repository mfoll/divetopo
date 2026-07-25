import { topoReunionCopy } from "./copy";
import type { Language } from "./preferences";
import mapManifestJson from "../public/maps/manifest.json";
import siteDetailsJson from "./site-details.json";

export const TOPO_REUNION_ORIGIN = "https://reunion.divetopo.com";
export const SUPPORTED_LANGUAGES = ["fr", "en"] as const;

type AssetVariant = {
  src: string;
  width: number;
  height: number;
};

type PublishedSite = {
  slug: string;
  displayName: string;
  location: {
    city: string;
    latitude: number;
    longitude: number;
  };
  maxDepthM: number;
  planMaxDepthM: number;
  plateAuthor: string;
  copyrightYear: number;
  mapLicense: string;
  maps: Array<{
    view: "2d" | "3d";
    style: "topographic" | "orthophoto";
    variants: AssetVariant[];
  }>;
  planches: Array<{
    style: "topographic" | "orthophoto";
    preview: AssetVariant;
  }>;
};

type PublishedMapManifest = {
  sites: PublishedSite[];
};

type LocalizedSiteContent = {
  sentences: string[];
  metadataDescription: string;
};

type SiteDetails = {
  city: string;
  content: Record<Language, LocalizedSiteContent>;
};

const mapManifest = mapManifestJson as PublishedMapManifest;
const siteDetails = siteDetailsJson as Record<string, SiteDetails>;

export const publishedSites = mapManifest.sites;
export const defaultSite = publishedSites[0];

if (!defaultSite) {
  throw new Error("Topo Réunion requires at least one published site");
}

for (const site of publishedSites) {
  const details = siteDetails[site.slug];
  if (!details) {
    throw new Error(`Missing website content for ${site.slug}`);
  }
  if (details.city !== site.location.city) {
    throw new Error(`Municipality mismatch for ${site.slug}`);
  }
  for (const language of SUPPORTED_LANGUAGES) {
    const content = details.content[language];
    if (
      !content ||
      content.sentences.length < 2 ||
      content.sentences.length > 4 ||
      !content.metadataDescription.trim()
    ) {
      throw new Error(`Incomplete ${language} website content for ${site.slug}`);
    }
  }
}

export function isLanguage(value: string): value is Language {
  return SUPPORTED_LANGUAGES.includes(value as Language);
}

export function findPublishedSite(slug: string) {
  return publishedSites.find((site) => site.slug === slug);
}

export function languagePath(language: Language) {
  return `/${language}`;
}

export function localizedSitePath(language: Language, slug: string) {
  return `/${language}/sites/${slug}`;
}

export function defaultSitePath(slug: string) {
  return `/sites/${slug}`;
}

export function absoluteUrl(path: string) {
  return new URL(path, TOPO_REUNION_ORIGIN).toString();
}

export type TopoRoute =
  | { kind: "overview"; language: Language }
  | { kind: "site"; language: Language; slug: string };

export function parseTopoRoute(pathname: string): TopoRoute | null {
  const siteMatch = pathname.match(
    /^\/(fr|en)\/sites\/([^/]+)\/?$/,
  );
  if (siteMatch) {
    return {
      kind: "site",
      language: siteMatch[1] as Language,
      slug: siteMatch[2],
    };
  }

  const overviewMatch = pathname.match(/^\/(fr|en)\/?$/);
  if (overviewMatch) {
    return {
      kind: "overview",
      language: overviewMatch[1] as Language,
    };
  }

  return null;
}

export function regionalSeoText(language: Language) {
  const copy = topoReunionCopy[language];
  return {
    heading: copy.topoReunionTitle,
    title: copy.topoReunionTitle,
    description: copy.metadataDescription,
    socialAlt: copy.topoReunionTitle,
  };
}

export function siteContentText(language: Language, slug: string) {
  const content = siteDetails[slug]?.content[language];
  if (!content) {
    throw new Error(`Missing ${language} website content for ${slug}`);
  }
  return content;
}

export function siteSeoText(language: Language, site: PublishedSite) {
  const content = siteContentText(language, site.slug);

  if (language === "fr") {
    const heading =
      `Plan du site de plongée ${site.displayName} à La Réunion`;
    return {
      heading,
      title: `${heading} | DiveTopo`,
      description: content.metadataDescription,
      socialAlt: `Vue 3D du relief de ${site.displayName} à La Réunion`,
    };
  }

  const heading =
    `${site.displayName} dive site map, Réunion Island`;
  return {
    heading,
    title: `${heading} | DiveTopo`,
    description: content.metadataDescription,
    socialAlt: `3D terrain view of ${site.displayName}, Réunion Island`,
  };
}

function mapImage(
  site: PublishedSite,
  view: "2d" | "3d",
): AssetVariant | undefined {
  const map = site.maps.find(
    (candidate) =>
      candidate.view === view && candidate.style === "orthophoto",
  );
  return (
    map?.variants.find((candidate) => candidate.width === 1600) ??
    map?.variants.at(-1)
  );
}

export function siteSocialImage(site: PublishedSite) {
  const image = mapImage(site, "3d");

  if (!image) {
    return {
      src: "/og.png",
      width: 1200,
      height: 630,
    };
  }

  return image;
}

export function siteRepresentativeImages(
  language: Language,
  site: PublishedSite,
) {
  const twoD = mapImage(site, "2d");
  const threeD = mapImage(site, "3d");
  const plate = site.planches.find(
    (candidate) => candidate.style === "orthophoto",
  )?.preview;

  if (!twoD || !threeD || !plate) {
    throw new Error(`Missing representative images for ${site.slug}`);
  }

  if (language === "fr") {
    return [
      {
        ...twoD,
        caption:
          `Plan topo-bathymétrique 2D de ${site.displayName} avec vue ` +
          `aérienne, jusqu’à −${site.planMaxDepthM} m.`,
      },
      {
        ...threeD,
        caption:
          `Perspective topo-bathymétrique 3D de ${site.displayName} avec ` +
          `vue aérienne, jusqu’à −${site.maxDepthM} m.`,
      },
      {
        ...plate,
        caption:
          `Planche imprimable de ${site.displayName} réunissant la ` +
          `localisation, le plan 2D et la perspective 3D.`,
      },
    ];
  }

  return [
    {
      ...twoD,
      caption:
        `2D topographic-bathymetric map of ${site.displayName} with ` +
        `aerial imagery, to −${site.planMaxDepthM} m.`,
    },
    {
      ...threeD,
      caption:
        `3D topographic-bathymetric perspective of ${site.displayName} ` +
        `with aerial imagery, to −${site.maxDepthM} m.`,
    },
    {
      ...plate,
      caption:
        `Printable map sheet for ${site.displayName}, combining the ` +
        `island locator, 2D map and 3D perspective.`,
    },
  ];
}
