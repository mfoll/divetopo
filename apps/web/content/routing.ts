import type { Language } from "./preferences";
import { regionCopy, regionLabel } from "./region-catalog";
import {
  pacaMapManifest,
  regionalMapManifests,
  reunionMapManifest,
  type RegionalAssetSite,
  type RegionSlug,
} from "./regional";

export const DIVETOPO_ORIGIN = "https://divetopo.com";
export const DIVETOPO_RELEASE_TAG = "v1.5.0";
export const DIVETOPO_RELEASE_ASSET_BASE =
  `https://github.com/mfoll/divetopo/releases/download/${DIVETOPO_RELEASE_TAG}`;
export const TOPO_REUNION_ORIGIN = DIVETOPO_ORIGIN;
export const REUNION_BASE_PATH = "/reunion";
export const PACA_BASE_PATH = "/paca";
export const SUPPORTED_LANGUAGES = ["fr", "en"] as const;

type AssetVariant = {
  src: string;
  width: number;
  height: number;
};

export type PublishedSite = RegionalAssetSite;

const mapManifest = reunionMapManifest;

export const publishedSites = mapManifest.sites;
export const pacaPublishedSites = pacaMapManifest.sites;
export const defaultSite = publishedSites[0];
export const defaultPacaSite = pacaPublishedSites[0];

const reunionSiteSlugAliases: Readonly<Record<string, string>> = {
  "pont-rouge-la-tortue": "pont-rouge",
};

if (!defaultSite) {
  throw new Error("Topo Réunion requires at least one published site");
}

if (!defaultPacaSite) {
  throw new Error("PACA requires at least one published site");
}

export function isLanguage(value: string): value is Language {
  return SUPPORTED_LANGUAGES.includes(value as Language);
}

export function findPublishedSite(slug: string) {
  return publishedSites.find((site) => site.slug === slug);
}

export function canonicalReunionSiteSlug(slug: string) {
  return reunionSiteSlugAliases[slug] ?? slug;
}

export function findPacaSite(slug: string) {
  return pacaPublishedSites.find((site) => site.slug === slug);
}

function basePath(region: RegionSlug) {
  return region === "reunion"
    ? REUNION_BASE_PATH
    : region === "paca"
      ? PACA_BASE_PATH
      : `/${region}`;
}

export function publishedSitesForRegion(region: RegionSlug) {
  return regionalMapManifests[region].sites;
}

export function findRegionalSite(region: RegionSlug, slug: string) {
  return publishedSitesForRegion(region).find((site) => site.slug === slug);
}

export function languagePath(
  language: Language,
  region: RegionSlug = "reunion",
) {
  return `${basePath(region)}/${language}`;
}

export function localizedSitePath(
  language: Language,
  slug: string,
  region: RegionSlug = "reunion",
) {
  return `${languagePath(language, region)}/sites/${slug}`;
}

export function defaultSitePath(
  slug: string,
  region: RegionSlug = "reunion",
) {
  return `${basePath(region)}/sites/${slug}`;
}

export function absoluteUrl(path: string) {
  return new URL(path, TOPO_REUNION_ORIGIN).toString();
}

export function releaseAssetUrl(filename: string) {
  return `${DIVETOPO_RELEASE_ASSET_BASE}/${encodeURIComponent(filename)}`;
}

export type TopoRoute =
  | { kind: "overview"; language: Language }
  | { kind: "site"; language: Language; slug: string };

export function parseTopoRoute(
  pathname: string,
  region: RegionSlug = "reunion",
): TopoRoute | null {
  const prefix = basePath(region);
  const siteMatch = pathname.match(
    new RegExp(`^${prefix}/(fr|en)/sites/([^/]+)/?$`),
  );
  if (siteMatch) {
    return {
      kind: "site",
      language: siteMatch[1] as Language,
      slug: siteMatch[2],
    };
  }

  const overviewMatch = pathname.match(
    new RegExp(`^${prefix}/(fr|en)/?$`),
  );
  if (overviewMatch) {
    return {
      kind: "overview",
      language: overviewMatch[1] as Language,
    };
  }

  return null;
}

export function regionalSeoText(
  language: Language,
  region: RegionSlug = "reunion",
) {
  const copy = regionCopy(region)[language];
  return {
    heading: copy.topoReunionTitle,
    title: copy.topoReunionTitle,
    description: copy.metadataDescription,
    socialAlt: copy.topoReunionTitle,
  };
}

export function siteSeoText(
  language: Language,
  site: PublishedSite,
  region: RegionSlug = "reunion",
) {
  const localizedRegionLabel = regionLabel(region, language);

  if (language === "fr") {
    const heading =
      `Plan du site de plongée ${site.displayName} en ${localizedRegionLabel}`;
    return {
      heading,
      title: `Plan de plongée ${site.displayName} à ${site.location.city} | DiveTopo`,
      description:
        `Cartes topo-bathymétriques 2D et vue 3D interactive du site de ` +
        `plongée ${site.displayName}, à ${site.location.city}, jusqu’à ` +
        `−${site.planMaxDepthM} m.`,
      socialAlt:
        `Vue 3D du relief de ${site.displayName} en ${localizedRegionLabel}`,
    };
  }

  const heading =
    `${site.displayName} dive site map, ${localizedRegionLabel}`;
  return {
    heading,
    title: `${site.displayName} dive site map, ${site.location.city} | DiveTopo`,
    description:
      `Explore 2D topographic-bathymetric maps and an interactive 3D view ` +
      `of the ${site.displayName} dive site in ${site.location.city}, to ` +
      `−${site.planMaxDepthM} m.`,
    socialAlt:
      `3D terrain view of ${site.displayName}, ${localizedRegionLabel}`,
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
  return map?.download;
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
  const plate = site.planches?.find(
    (candidate) => candidate.style === "orthophoto",
  )?.download;
  const releasedPlate = plate
    ? { ...plate, src: releaseAssetUrl(plate.filename) }
    : undefined;

  if (!twoD || !threeD) {
    throw new Error(`Missing representative images for ${site.slug}`);
  }

  const images = [
    language === "fr"
      ? {
          ...twoD,
          caption:
            `Plan topo-bathymétrique 2D de ${site.displayName} avec vue ` +
            `aérienne, jusqu’à −${site.planMaxDepthM} m.`,
        }
      : {
          ...twoD,
          caption:
            `2D topographic-bathymetric map of ${site.displayName} with ` +
            `aerial imagery, to −${site.planMaxDepthM} m.`,
        },
    language === "fr"
      ? {
          ...threeD,
          caption:
            `Perspective topo-bathymétrique 3D de ${site.displayName} avec ` +
            `vue aérienne, jusqu’à −${site.maxDepthM} m.`,
        }
      : {
          ...threeD,
          caption:
            `3D topographic-bathymetric perspective of ${site.displayName} ` +
            `with aerial imagery, to −${site.maxDepthM} m.`,
        },
  ];

  if (!releasedPlate) {
    return images;
  }

  if (language === "fr") {
    return [
      ...images,
      {
        ...releasedPlate,
        caption:
          `Planche imprimable de ${site.displayName} réunissant la ` +
          `localisation, le plan 2D et la perspective 3D.`,
      },
    ];
  }

  return [
    ...images,
    {
      ...releasedPlate,
      caption:
        `Printable map sheet for ${site.displayName}, combining the ` +
        `island locator, 2D map and 3D perspective.`,
    },
  ];
}
