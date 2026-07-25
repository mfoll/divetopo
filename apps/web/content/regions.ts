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
      fr: "Explorez une sélection non exhaustive de sept sites de la côte ouest à travers leurs plans, perspectives et reliefs interactifs.",
      en: "Explore a non-exhaustive selection of seven sites along the west coast through 2D maps, 3D views and interactive terrain.",
    },
    features: [
      { fr: "7 sites", en: "7 sites" },
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
] as const;
