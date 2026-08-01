"use client";

import type { Language, Theme } from "../content/preferences";
import {
  PACA_EXPERIENCE_CONFIG,
  TopoRegionExperience,
} from "./TopoReunionExperience";

export default function PacaExperience({
  language,
  theme,
  initialSlug,
}: {
  language: Language;
  theme: Theme;
  initialSlug?: string;
}) {
  return (
    <TopoRegionExperience
      config={PACA_EXPERIENCE_CONFIG}
      language={language}
      theme={theme}
      initialSlug={initialSlug}
    />
  );
}
