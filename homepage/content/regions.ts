export const regions = [
  {
    slug: "la-reunion",
    name: "La Réunion",
    location: "Océan Indien",
    href: "https://reunion.divetopo.com",
    status: "Atlas disponible",
    description:
      "Explorez sept sites de la côte ouest à travers leurs plans, perspectives et reliefs interactifs.",
    features: ["7 sites", "Plans 2D", "Vues 3D", "Reliefs interactifs"],
    image: {
      src: "/reunion-overview.webp",
      width: 1000,
      height: 840,
      alt: "Relief terrestre et sous-marin de l’île de La Réunion.",
    },
  },
] as const;
