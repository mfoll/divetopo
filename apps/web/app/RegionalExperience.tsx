"use client";

import type { Language, Theme } from "../content/preferences";
import type { RegionSlug } from "../content/regional";
import {
  regionalExperienceConfig,
  TopoRegionExperience,
} from "./TopoReunionExperience";

export default function RegionalExperience({
  region,
  language,
  theme,
  initialSlug,
}: {
  region: RegionSlug;
  language: Language;
  theme: Theme;
  initialSlug?: string;
}) {
  return (
    <TopoRegionExperience
      config={regionalExperienceConfig(region)}
      language={language}
      theme={theme}
      initialSlug={initialSlug}
    />
  );
}
