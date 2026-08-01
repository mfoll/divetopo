import { pacaMapManifest } from "./regional";

const pacaSiteCount = pacaMapManifest.sites.length;

export const regions = [
  {
    slug: "la-reunion",
    name: {
      fr: "La Réunion",
      en: "Réunion Island",
    },
    location: {
      fr: "Océan Indien",
      en: "Indian Ocean",
    },
    href: "/reunion",
    description: {
      fr: "Explorez une sélection non exhaustive de onze sites de la côte ouest à travers leurs plans, perspectives et reliefs interactifs.",
      en: "Explore a non-exhaustive selection of eleven sites along the west coast through 2D maps, 3D views and interactive terrain.",
    },
    features: [
      { fr: "11 sites", en: "11 sites" },
      { fr: "Plans 2D", en: "2D maps" },
      { fr: "Vues 3D", en: "3D views" },
      { fr: "Reliefs interactifs", en: "Interactive terrain" },
    ],
    image: {
      src: "/reunion-overview.webp",
      width: 1000,
      height: 840,
      alt: {
        fr: "Relief terrestre et sous-marin de l’île de La Réunion.",
        en: "Land and underwater terrain around Réunion Island.",
      },
    },
  },
  {
    slug: "paca",
    name: {
      fr: "Côte d’Azur",
      en: "Côte d’Azur",
    },
    location: {
      fr: "Méditerranée française",
      en: "French Mediterranean",
    },
    href: "/paca",
    description: {
      fr: `Explorez cinq sites validés de la côte méditerranéenne à travers leurs plans, posters 3D et reliefs interactifs.`,
      en: `Explore five validated Mediterranean sites through their maps, 3D posters and interactive terrain.`,
    },
    features: [
      { fr: `${pacaSiteCount} sites`, en: `${pacaSiteCount} sites` },
      { fr: "Plans 2D", en: "2D maps" },
      { fr: "Vues 3D", en: "3D views" },
      { fr: "Reliefs interactifs", en: "Interactive terrain" },
    ],
    image: {
      src: pacaMapManifest.westCoastLocator.src,
      width: pacaMapManifest.westCoastLocator.width,
      height: pacaMapManifest.westCoastLocator.height,
      alt: {
        fr: "Relief régional de la Côte d’Azur avec cinq sites de plongée repérés.",
        en: "Regional relief of the Côte d’Azur with five dive sites marked.",
      },
    },
  },
] as const;
