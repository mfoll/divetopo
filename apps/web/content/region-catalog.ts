import { pacaCopy, topoReunionCopy } from "./copy";
import type { Language } from "./preferences";
import {
  regionalMapManifests,
  type AutonomousMediterraneanRegionSlug,
  type RegionSlug,
} from "./regional";

export const autonomousMediterraneanRegions = [
  "bouches-du-rhone",
  "var-ouest",
  "var-centre",
  "var-est",
  "alpes-maritimes",
] as const satisfies readonly AutonomousMediterraneanRegionSlug[];

export const publicRegions = [
  "reunion",
  ...autonomousMediterraneanRegions,
] as const satisfies readonly RegionSlug[];

export const regionCatalog = {
  reunion: {
    names: { fr: "La Réunion", en: "Réunion Island" },
    location: { fr: "Océan Indien", en: "Indian Ocean" },
  },
  paca: {
    names: { fr: "Côte d’Azur", en: "Côte d’Azur" },
    location: { fr: "Méditerranée française", en: "French Mediterranean" },
  },
  "bouches-du-rhone": {
    names: { fr: "Bouches-du-Rhône", en: "Bouches-du-Rhône" },
    location: {
      fr: "Marseille, Frioul, Riou et Calanques",
      en: "Marseille, Frioul, Riou and Calanques",
    },
  },
  "var-ouest": {
    names: { fr: "Var Ouest", en: "Western Var" },
    location: {
      fr: "Sanary, Six-Fours et Cap Sicié",
      en: "Sanary, Six-Fours and Cap Sicié",
    },
  },
  "var-centre": {
    names: { fr: "Var Centre", en: "Central Var" },
    location: {
      fr: "Giens, Porquerolles et Port-Cros",
      en: "Giens, Porquerolles and Port-Cros",
    },
  },
  "var-est": {
    names: { fr: "Var Est", en: "Eastern Var" },
    location: {
      fr: "Estérel et Saint-Raphaël",
      en: "Estérel and Saint-Raphaël",
    },
  },
  "alpes-maritimes": {
    names: { fr: "Alpes-Maritimes", en: "Alpes-Maritimes" },
    location: {
      fr: "Cannes, Théoule et Cap-Ferrat",
      en: "Cannes, Théoule and Cap-Ferrat",
    },
  },
} as const;

export function regionLabel(region: RegionSlug, language: Language) {
  return regionCatalog[region].names[language];
}

function mediterraneanSourceCards(
  region: AutonomousMediterraneanRegionSlug,
  language: Language,
) {
  const cards = pacaCopy[language].sources.cards;
  if (region !== "alpes-maritimes") return cards;
  return cards.map((card, index) =>
    index === 0
      ? {
          ...card,
          description:
            card.description +
            (language === "fr"
              ? " Sur certains sites, les isobathes 2007 de la Métropole Nice Côte d’Azur servent uniquement de contrôle de cohérence et ne sont pas interpolées dans le MNT."
              : " At selected sites, 2007 Métropole Nice Côte d’Azur isobaths are used only as a consistency check and are not interpolated into the DTM."),
          links: [
            ...card.links,
            {
              label: "Métropole Nice Côte d’Azur — Bathymétrie",
              href: "https://www.data.gouv.fr/datasets/bathymetrie",
            },
          ],
        }
      : card,
  );
}

export function regionCopy(region: RegionSlug) {
  if (region === "reunion") return topoReunionCopy;
  if (region === "paca") return pacaCopy;

  const names = regionCatalog[region].names;
  const count = regionalMapManifests[region].sites.length;
  const frenchInRegion =
    region === "alpes-maritimes"
      ? "dans les Alpes-Maritimes"
      : "en " + names.fr;
  const frenchOfRegion =
    region === "alpes-maritimes"
      ? "des Alpes-Maritimes"
      : "de " + names.fr;
  return {
    fr: {
      ...pacaCopy.fr,
      topoReunionTitle: "Plans des sites de plongée " + frenchOfRegion,
      metadataDescription:
        "Plans topo-bathymétriques 2D, perspectives 3D et reliefs " +
        "interactifs des sites publiés " + frenchInRegion + ".",
      islandName: names.fr,
      picker: {
        ...pacaCopy.fr.picker,
        chooseDiveSite: "Choisir un site " + frenchInRegion,
        westCoastAlt:
          "Relief terrestre et sous-marin " + frenchOfRegion + ", avec " +
          count + " site" + (count > 1 ? "s" : "") + " publié" +
          (count > 1 ? "s" : "") + ".",
      },
      sources: {
        ...pacaCopy.fr.sources,
        lead:
          "Les sites publiés " + frenchInRegion + " utilisent les sources " +
          "déclarées dans leur configuration régionale.",
        cards: mediterraneanSourceCards(region, "fr"),
      },
      contact: {
        ...pacaCopy.fr.contact,
        question:
          "Une question ou une remarque sur les cartes " + frenchOfRegion + "\u00a0?",
      },
    },
    en: {
      ...pacaCopy.en,
      topoReunionTitle: "Dive site maps in " + names.en,
      metadataDescription:
        "2D topographic-bathymetric maps, 3D views and interactive terrain " +
        "for published sites in " + names.en + ".",
      islandName: names.en,
      picker: {
        ...pacaCopy.en.picker,
        chooseDiveSite: "Choose a dive site in " + names.en,
        westCoastAlt:
          "Land and underwater terrain in " + names.en + ", with " + count +
          " published site" + (count === 1 ? "" : "s") + ".",
      },
      sources: {
        ...pacaCopy.en.sources,
        lead:
          "Published sites in " + names.en + " use the sources declared " +
          "in their regional configuration.",
        cards: mediterraneanSourceCards(region, "en"),
      },
      contact: {
        ...pacaCopy.en.contact,
        question: "Have a question or comment about the " + names.en + " maps?",
      },
    },
  };
}
