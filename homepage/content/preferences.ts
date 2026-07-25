export type Language = "fr" | "en";
export type Theme = "light" | "dark" | "auto";

export const LANGUAGES = ["fr", "en"] as const;
export const LANGUAGE_COOKIE = "divetopo-language";
export const THEME_COOKIE = "divetopo-theme";

export function isLanguage(value: string): value is Language {
  return LANGUAGES.some((language) => language === value);
}
