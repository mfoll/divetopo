const sourceLinks = {
  bathymetry: [
    {
      label: "HYSCORES 2015",
      href: "https://doi.org/10.12770/ee059de2-2c81-46ce-88de-0fb5517046af",
    },
    { label: "Ifremer", href: "https://www.ifremer.fr/fr" },
    { label: "UBO", href: "https://www.univ-brest.fr/fr" },
    {
      label: "Office de l’eau Réunion",
      href: "https://donnees.eaureunion.fr/",
    },
  ],
  topography: [
    {
      label: "IGN RGE ALTI",
      href: "https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_RGE-ALTI",
    },
  ],
  imagery: [
    {
      label: "IGN BD ORTHO",
      href: "https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_BD-ORTHO",
    },
  ],
  regional: [
    {
      label: "GEBCO 2024",
      href: "https://www.gebco.net/data-products-gridded-bathymetry-data/gebco2024-grid",
    },
  ],
} as const;

export const atlasCopy = {
  fr: {
    header: {
      homeLabel: "DiveTopo, revenir au site principal",
      brand: "DiveTopo",
      navigationLabel: "Navigation principale",
      explore: "Explorer",
      methodSources: "Méthode et sources",
      githubNewWindow: "GitHub (nouvelle fenêtre)",
    },
    preferences: {
      languageGroup: "Langue",
      french: "Afficher le site en français",
      english: "Afficher le site en anglais",
      themeGroup: "Thème",
      light: "Utiliser le thème clair",
      dark: "Utiliser le thème sombre",
      auto: "Utiliser le thème du système",
    },
    atlasTitle: "Plans des sites de plongée à La Réunion",
    metadataDescription:
      "Plans topo-bathymétriques 2D, perspectives 3D et reliefs interactifs de sites de plongée à La Réunion.",
    islandName: "La Réunion",
    surfaces: {
      orthophoto: {
        label: "Vue aérienne",
        description: "un fond en vue aérienne",
      },
      topographic: {
        label: "Topographie",
        description: "un fond topographique",
      },
    },
    views: {
      group: "Type de vue",
      twoD: "Plan 2D",
      threeD: "Vue 3D",
      interactive: "3D interactive",
    },
    surfaceGroup: "Fond de carte",
    picker: {
      chooseDiveSite: "Choisir un site de plongée",
      chooseSite: "Choisir un site",
      sites: "Sites :",
      instruction: "Sélectionnez un site sur la carte.",
      westCoastAlt:
        "Relief terrestre et sous-marin de la côte ouest de La Réunion, du Cap La Houssaye à Saint-Leu.",
      north: "Nord",
      showSite: "Afficher",
      fiveKilometreScale: "Échelle de cinq kilomètres",
      openIslandMap: "Ouvrir la carte de La Réunion en grand",
      islandOverviewAlt:
        "Relief terrestre et sous-marin de La Réunion. Un rectangle situe la zone ouest détaillée ci-dessus.",
    },
    activeSite: {
      googleMaps: "Voir le site sur Google Maps",
    },
    map: {
      preparingTerrain: "Préparation du relief…",
      openLarge: "Ouvrir en grand",
      openMap: "Ouvrir la carte de",
      download: "Télécharger",
      downloadTwoD: "Télécharger le plan 2D",
      downloadThreeD: "Télécharger la vue 3D",
      interactionHelp:
        "Glisser pour tourner · Molette ou pincement pour zoomer · Clic droit ou Ctrl + glisser pour déplacer",
      twoDAltStart: "Plan topo-bathymétrique 2D de",
      twoDAltMiddle: "nord en haut, avec",
      depthsShownTo: "profondeurs affichées jusqu’à",
      threeDAltStart: "Perspective 3D oblique de",
      threeDAltMiddle: "avec",
      threeDAltEnd: ", relief vertical exagéré environ quatre fois.",
    },
    plate: {
      previewAlt: "Aperçu de la planche imprimable de",
      printable: "Planche HD à imprimer",
      download: "Télécharger la planche HD",
    },
    sources: {
      title: "Données, méthode et licences",
      lead:
        "Ce projet est rendu possible par des données bathymétriques, topographiques et aériennes librement accessibles, mises à disposition par des organismes publics et scientifiques.",
      cards: [
        {
          title: "Bathymétrie",
          description:
            "Relief sous-marin issu du levé HYSCORES 2015, incluant les données Litto3D.",
          links: sourceLinks.bathymetry,
        },
        {
          title: "Topographie",
          description:
            "Modèle numérique de terrain RGE ALTI pour le relief de la partie terrestre.",
          links: sourceLinks.topography,
        },
        {
          title: "Imagerie aérienne",
          description:
            "Imagerie aérienne géoréférencée IGN BD ORTHO pour le fond haute résolution.",
          links: sourceLinks.imagery,
        },
        {
          title: "Relief régional",
          description:
            "Grille bathymétrique GEBCO 2024 pour la carte de sélection de la côte ouest.",
          links: sourceLinks.regional,
        },
      ],
      methodLabel: "Traitement cartographique",
      methodTitle: "Méthode de production",
      methodSteps: [
        {
          title: "Sources et contrôle du cache",
          description:
            "Les MNT HYSCORES pour les fonds marins, le RGE ALTI pour la terre et l’orthophoto IGN à 20 cm sont découpés aux emprises de chaque site et alignés sur une grille commune WGS 84 / UTM 40S (EPSG:32740). Avant tout rendu, le pipeline contrôle leur source, leur emprise, leur résolution, leurs bandes, leur contenu et leur empreinte SHA-256.",
        },
        {
          title: "Fusion terre-mer",
          description:
            "Les altitudes marines sont converties en profondeurs positives, puis bathymétrie et topographie sont fusionnées autour d’un trait de côte interpolé à 0 m. Les lacunes restent absentes par défaut ; une limite marine profonde documentée peut être complétée localement par un plateau uniforme à la profondeur maximale, sans relief intermédiaire. Dans la variante orthophoto, l’image est recalée sur la grille bathymétrique, opaque jusqu’à −1,5 m puis fondue progressivement jusqu’à −2 m.",
        },
        {
          title: "Plans et perspectives",
          description:
            "Les cartes statiques utilisent des isobathes extraites et lissées tous les 5 m, jusqu’à −20, −30 ou −40 m selon le site. Dans le relief interactif, elles sont calculées dans des plans parfaitement horizontaux, reprennent à chaque niveau la couleur de la palette bathymétrique et sont accompagnées d’une légende fixe. Le plan 2D reste nord en haut sur l’emprise fine ; la perspective 3D utilise une emprise élargie, un azimut et un cadrage propres au site, une caméra placée depuis le large et une exagération verticale de ×4.",
        },
        {
          title: "Relief et formats de sortie",
          description:
            "L’éclairage des reliefs 3D est calculé à partir de normales métriques, avec une lumière hémisphérique froide, une lumière directionnelle chaude et une exposition linéaire de 1,55. La surface fusionnée est aussi exportée pour le Web avec son emprise et son centrage initial sous forme d’un champ d’altitude 16 bits, de masques compacts et de deux textures ; les planches HD assemblent ensuite la localisation insulaire, le plan 2D et la perspective 3D.",
        },
      ],
      creditsTitle: "Crédits et licence",
      mapsAndVisualisations: "Plans et visualisations",
      sourceCodeTitle: "Code source",
      sourceCodeText:
        "La chaîne de production et le code du site sont disponibles sur GitHub.",
      viewRepository: "Voir le dépôt GitHub",
      safetyTitle: "Sécurité",
      safetyText:
        "Ces plans ne sont pas destinés à la navigation et ne remplacent pas les informations locales, les conditions de mer, les consignes des autorités ou l’avis d’un professionnel.",
    },
    footer: {
      maps: "Plans",
      backToTop: "Haut de page",
    },
    dialogs: {
      largeMap: "Carte de",
      largeIslandMap: "Carte de La Réunion en grand",
      close: "Fermer",
      islandOverviewAlt:
        "Relief terrestre et sous-marin de La Réunion. Un rectangle situe la zone ouest couverte par la carte de sélection des sites.",
    },
    terrain: {
      interactiveTerrain: "Relief 3D interactif de",
      unavailable:
        "Le relief interactif n’est pas disponible sur cet appareil.",
      loading: "Chargement du relief…",
      orientation: "Orientation géographique de la vue",
      westCardinal: "O",
      isobathLegend: "Légende des isobathes, espacées de",
      hideIsobaths: "Masquer les isobathes espacées de 5 mètres",
      showIsobaths: "Afficher les isobathes espacées de 5 mètres",
      hideIsobathsShort: "Masquer les isobathes",
      showIsobathsShort: "Afficher les isobathes",
      resetView: "Réinitialiser la vue",
      exitFullscreen: "Quitter le plein écran",
      enterFullscreen: "Passer en plein écran",
    },
  },
  en: {
    header: {
      homeLabel: "DiveTopo, return to the main website",
      brand: "DiveTopo",
      navigationLabel: "Main navigation",
      explore: "Explore",
      methodSources: "Method and sources",
      githubNewWindow: "GitHub (new window)",
    },
    preferences: {
      languageGroup: "Language",
      french: "View the site in French",
      english: "View the site in English",
      themeGroup: "Theme",
      light: "Use light theme",
      dark: "Use dark theme",
      auto: "Use system theme",
    },
    atlasTitle: "Dive site maps of Réunion Island",
    metadataDescription:
      "Explore 2D topographic-bathymetric maps, 3D perspectives and interactive terrain for dive sites around Réunion Island.",
    islandName: "Réunion Island",
    surfaces: {
      orthophoto: {
        label: "Aerial imagery",
        description: "an aerial-imagery basemap",
      },
      topographic: {
        label: "Topography",
        description: "a topographic basemap",
      },
    },
    views: {
      group: "View type",
      twoD: "2D map",
      threeD: "3D view",
      interactive: "Interactive 3D",
    },
    surfaceGroup: "Map background",
    picker: {
      chooseDiveSite: "Choose a dive site",
      chooseSite: "Choose a site",
      sites: "Sites:",
      instruction: "Select a site on the map.",
      westCoastAlt:
        "Land and underwater terrain along Réunion Island’s west coast, from Cap La Houssaye to Saint-Leu.",
      north: "North",
      showSite: "Show",
      fiveKilometreScale: "Five-kilometre scale",
      openIslandMap: "Open the Réunion Island map",
      islandOverviewAlt:
        "Land and underwater terrain around Réunion Island. A rectangle marks the west-coast area shown in detail above.",
    },
    activeSite: {
      googleMaps: "View site on Google Maps",
    },
    map: {
      preparingTerrain: "Preparing terrain…",
      openLarge: "Open full size",
      openMap: "Open the map of",
      download: "Download",
      downloadTwoD: "Download the 2D map",
      downloadThreeD: "Download the 3D view",
      interactionHelp:
        "Drag to rotate · Scroll or pinch to zoom · Right-click or Ctrl + drag to pan",
      twoDAltStart: "2D topographic-bathymetric map of",
      twoDAltMiddle: "north up, with",
      depthsShownTo: "and depths shown to",
      threeDAltStart: "Oblique 3D perspective of",
      threeDAltMiddle: "with",
      threeDAltEnd: " and approximately fourfold vertical exaggeration.",
    },
    plate: {
      previewAlt: "Preview of the printable map sheet for",
      printable: "Printable high-resolution map sheet",
      download: "Download the high-resolution sheet",
    },
    sources: {
      title: "Data, method and licences",
      lead:
        "This project is made possible by freely available bathymetric, topographic and aerial data provided by public and scientific organisations.",
      cards: [
        {
          title: "Bathymetry",
          description:
            "Underwater terrain from the 2015 HYSCORES survey, including Litto3D data.",
          links: sourceLinks.bathymetry,
        },
        {
          title: "Topography",
          description:
            "The RGE ALTI digital terrain model used for the land surface.",
          links: sourceLinks.topography,
        },
        {
          title: "Aerial imagery",
          description:
            "Georeferenced IGN BD ORTHO aerial imagery used for the high-resolution background.",
          links: sourceLinks.imagery,
        },
        {
          title: "Regional terrain",
          description:
            "The GEBCO 2024 bathymetric grid used for the west-coast site-selection map.",
          links: sourceLinks.regional,
        },
      ],
      methodLabel: "Cartographic processing",
      methodTitle: "Production method",
      methodSteps: [
        {
          title: "Sources and cache validation",
          description:
            "HYSCORES digital terrain models for the seabed, RGE ALTI for land and 20 cm IGN orthophotography are cropped to each site extent and aligned on a common WGS 84 / UTM zone 40S grid (EPSG:32740). Before rendering, the pipeline validates their source, extent, resolution, bands, content and SHA-256 fingerprint.",
        },
        {
          title: "Land-sea fusion",
          description:
            "Marine elevations are converted to positive depths, then bathymetry and topography are merged around a shoreline interpolated at 0 m. Gaps remain empty by default; a documented deep-water boundary may be completed locally with a uniform plateau at the maximum depth, without inventing intermediate relief. In the aerial-imagery version, the image is aligned to the bathymetric grid, remains opaque to −1.5 m and then fades progressively to −2 m.",
        },
        {
          title: "Maps and perspectives",
          description:
            "Static maps use isobaths extracted and smoothed at 5 m intervals, down to −20, −30 or −40 m depending on the site. In the interactive terrain, they are calculated in perfectly horizontal planes, use the bathymetric palette colour for each level and are accompanied by a fixed legend. The detailed 2D map remains north-up; the 3D perspective uses a larger extent, a site-specific azimuth and framing, an offshore camera and ×4 vertical exaggeration.",
        },
        {
          title: "Terrain and output formats",
          description:
            "3D terrain lighting is calculated from metric normals, using a cool hemisphere light, a warm directional light and linear exposure of 1.55. The fused surface is also exported for the Web with its extent and initial framing as a 16-bit height field, compact masks and two textures; the high-resolution sheets then combine the island locator, 2D map and 3D perspective.",
        },
      ],
      creditsTitle: "Credits and licence",
      mapsAndVisualisations: "Maps and visualisations",
      sourceCodeTitle: "Source code",
      sourceCodeText:
        "The production pipeline and website source code are available on GitHub.",
      viewRepository: "View the GitHub repository",
      safetyTitle: "Safety",
      safetyText:
        "These maps are not intended for navigation and do not replace local information, sea conditions, guidance from authorities or professional advice.",
    },
    footer: {
      maps: "Maps",
      backToTop: "Back to top",
    },
    dialogs: {
      largeMap: "Full-size map of",
      largeIslandMap: "Full-size map of Réunion Island",
      close: "Close",
      islandOverviewAlt:
        "Land and underwater terrain around Réunion Island. A rectangle marks the west-coast area covered by the site-selection map.",
    },
    terrain: {
      interactiveTerrain: "Interactive 3D terrain of",
      unavailable:
        "Interactive terrain is not available on this device.",
      loading: "Loading terrain…",
      orientation: "Geographic orientation of the view",
      westCardinal: "W",
      isobathLegend: "Isobath legend at intervals of",
      hideIsobaths: "Hide isobaths at 5-metre intervals",
      showIsobaths: "Show isobaths at 5-metre intervals",
      hideIsobathsShort: "Hide isobaths",
      showIsobathsShort: "Show isobaths",
      resetView: "Reset view",
      exitFullscreen: "Exit full screen",
      enterFullscreen: "Enter full screen",
    },
  },
} as const;
