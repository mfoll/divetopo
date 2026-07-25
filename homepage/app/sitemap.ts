import type { MetadataRoute } from "next";
import { LANGUAGES } from "../content/preferences";

const origin = "https://divetopo.com";
const languageAlternates = {
  fr: `${origin}/fr`,
  en: `${origin}/en`,
  "x-default": `${origin}/`,
};

export default function sitemap(): MetadataRoute.Sitemap {
  return LANGUAGES.map((language) => ({
    url: `${origin}/${language}`,
    alternates: {
      languages: languageAlternates,
    },
  }));
}
