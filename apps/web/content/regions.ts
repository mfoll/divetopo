import { publicRegions, regionCatalog } from "./region-catalog";
import { regionalMapManifests } from "./regional";

export const regions = publicRegions.map((region) => {
  const catalog = regionCatalog[region];
  const manifest = regionalMapManifests[region];
  const count = manifest.sites.length;
  if (region === "reunion") {
    return {
      slug: "la-reunion",
      name: catalog.names,
      location: catalog.location,
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
      sitePositions: manifest.sites.map((site) => ({
        slug: site.slug,
        position: site.reunionOverviewPosition,
      })),
    };
  }

  return {
    slug: region,
    name: catalog.names,
    location: catalog.location,
    href: `/${region}`,
    description: {
      fr:
        count > 0
          ? `Explorez les ${count} sites actuellement publiés dans cette zone. Les nouveaux rendus restent masqués jusqu’à leur validation.`
          : "Découvrez la zone et suivez la préparation des cinq premières cartographies, encore masquées jusqu’à leur validation.",
      en:
        count > 0
          ? `Explore the ${count} sites currently published in this area. New renders remain hidden until validation.`
          : "Discover the area and follow the preparation of its first five maps, still hidden until validation.",
    },
    features: [
      {
        fr: count > 0 ? `${count} sites publiés` : "5 sites en préparation",
        en: count > 0 ? `${count} published sites` : "5 sites in preparation",
      },
      { fr: "Plans 2D", en: "2D maps" },
      { fr: "Vues 3D", en: "3D views" },
      { fr: "Publication après QA", en: "Published after QA" },
    ],
    image: {
      src: manifest.westCoastLocator.src,
      width: manifest.westCoastLocator.width,
      height: manifest.westCoastLocator.height,
      alt: {
        fr: `Relief régional de ${catalog.names.fr}.`,
        en: `Regional relief of ${catalog.names.en}.`,
      },
    },
    sitePositions: manifest.sites.map((site) => ({
      slug: site.slug,
      position: site.westCoastLocatorPosition,
    })),
  };
});
