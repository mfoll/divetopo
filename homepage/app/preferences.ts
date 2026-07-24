import { cookies, headers } from "next/headers";
import {
  LANGUAGE_COOKIE,
  THEME_COOKIE,
  type Language,
  type Theme,
} from "../content/preferences";

function languageFromAcceptHeader(acceptLanguage: string | null): Language {
  if (!acceptLanguage) {
    return "fr";
  }

  const preferences = acceptLanguage
    .split(",")
    .map((entry, index) => {
      const [rawLanguage, ...rawParameters] = entry.trim().split(";");
      let quality = 1;

      for (const parameter of rawParameters) {
        const [name, value] = parameter.trim().split("=");

        if (name.toLowerCase() === "q") {
          const parsedQuality = Number(value);
          quality = Number.isFinite(parsedQuality)
            ? Math.min(1, Math.max(0, parsedQuality))
            : 0;
        }
      }

      return {
        index,
        language: rawLanguage.toLowerCase(),
        quality,
      };
    })
    .filter(({ language, quality }) => language && quality > 0)
    .sort(
      (first, second) =>
        second.quality - first.quality || first.index - second.index,
    );

  for (const preference of preferences) {
    if (
      preference.language === "fr" ||
      preference.language.startsWith("fr-")
    ) {
      return "fr";
    }

    if (
      preference.language === "en" ||
      preference.language.startsWith("en-")
    ) {
      return "en";
    }
  }

  return "fr";
}

export async function getPreferences(): Promise<{
  language: Language;
  theme: Theme;
}> {
  const [cookieStore, requestHeaders] = await Promise.all([
    cookies(),
    headers(),
  ]);
  const languageCookie = cookieStore.get(LANGUAGE_COOKIE)?.value;
  const themeCookie = cookieStore.get(THEME_COOKIE)?.value;

  const language =
    languageCookie === "fr" || languageCookie === "en"
      ? languageCookie
      : languageFromAcceptHeader(requestHeaders.get("accept-language"));

  const theme =
    themeCookie === "light" ||
    themeCookie === "dark" ||
    themeCookie === "auto"
      ? themeCookie
      : "auto";

  return { language, theme };
}
