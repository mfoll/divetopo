import { topoReunionCopy } from "./copy";
import type { Language } from "./preferences";
import mapManifestJson from "../public/maps/manifest.json";

export const TOPO_REUNION_ORIGIN = "https://reunion.divetopo.com";
export const SUPPORTED_LANGUAGES = ["fr", "en"] as const;

type PublishedSite = {
  slug: string;
  displayName: string;
  location: {
    city: string;
    latitude: number;
    longitude: number;
  };
  maps: Array<{
    view: "2d" | "3d";
    style: "topographic" | "orthophoto";
    variants: Array<{
      src: string;
      width: number;
      height: number;
    }>;
  }>;
};

type PublishedMapManifest = {
  sites: PublishedSite[];
};

const mapManifest = mapManifestJson as PublishedMapManifest;

export const publishedSites = mapManifest.sites;
export const defaultSite = publishedSites[0];

if (!defaultSite) {
  throw new Error("Topo Réunion requires at least one published site");
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
    title: copy.topoReunionTitle,
    description: copy.metadataDescription,
    socialAlt: copy.topoReunionTitle,
  };
}

export function siteSeoText(language: Language, site: PublishedSite) {
  if (language === "fr") {
    return {
      title:
        `Plan du site de plongée ${site.displayName} à La Réunion | DiveTopo`,
      description:
        `Explorez les plans topo-bathymétriques 2D, la vue 3D et le relief ` +
        `interactif de ${site.displayName}, ${site.location.city}, à La Réunion.`,
      socialAlt: `Vue 3D du relief de ${site.displayName} à La Réunion`,
    };
  }

  return {
    title: `${site.displayName} dive site map, Réunion Island | DiveTopo`,
    description:
      `Explore 2D topographic-bathymetric maps, a 3D view and interactive ` +
      `terrain for ${site.displayName}, ${site.location.city}, Réunion Island.`,
    socialAlt: `3D terrain view of ${site.displayName}, Réunion Island`,
  };
}

export function siteSocialImage(site: PublishedSite) {
  const map = site.maps.find(
    (candidate) =>
      candidate.view === "3d" && candidate.style === "orthophoto",
  );
  const image =
    map?.variants.find((candidate) => candidate.width === 1600) ??
    map?.variants.at(-1);

  if (!image) {
    return {
      src: "/og.png",
      width: 1200,
      height: 630,
    };
  }

  return image;
}
