"use client";

import { useState } from "react";
import { homepageCopy } from "../content/copy";
import {
  LANGUAGE_COOKIE,
  THEME_COOKIE,
  type Language,
  type Theme,
} from "../content/preferences";

const COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

const languageOptions = [
  { value: "fr", shortLabel: "FR" },
  { value: "en", shortLabel: "EN" },
] as const;

const themeOptions = [
  { value: "light", labelKey: "lightShort" },
  { value: "dark", labelKey: "darkShort" },
  { value: "auto", labelKey: "autoShort" },
] as const;

function writePreference(name: string, value: string) {
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${name}=${encodeURIComponent(value)}; Path=/; Max-Age=${COOKIE_MAX_AGE_SECONDS}; SameSite=Lax${secure}`;
}

export default function PreferenceControls({
  language,
  theme,
}: {
  language: Language;
  theme: Theme;
}) {
  const [selectedTheme, setSelectedTheme] = useState(theme);
  const labels = homepageCopy[language].preferences;

  function chooseLanguage(nextLanguage: Language) {
    if (nextLanguage === language) {
      return;
    }

    writePreference(LANGUAGE_COOKIE, nextLanguage);
    window.location.reload();
  }

  function chooseTheme(nextTheme: Theme) {
    writePreference(THEME_COOKIE, nextTheme);
    document.documentElement.setAttribute("data-theme", nextTheme);
    setSelectedTheme(nextTheme);
  }

  return (
    <div className="preference-controls">
      <fieldset className="segmented-control language-control">
        <legend className="sr-only">{labels.languageGroup}</legend>
        {languageOptions.map((option) => (
          <span className="segment" key={option.value}>
            <input
              aria-label={
                option.value === "fr" ? labels.french : labels.english
              }
              checked={language === option.value}
              className="segment-input"
              data-testid={`language-${option.value}`}
              id={`language-${option.value}`}
              name="language"
              onChange={() => chooseLanguage(option.value)}
              type="radio"
              value={option.value}
            />
            <label htmlFor={`language-${option.value}`}>
              {option.shortLabel}
            </label>
          </span>
        ))}
      </fieldset>

      <fieldset className="segmented-control theme-control">
        <legend className="sr-only">{labels.themeGroup}</legend>
        {themeOptions.map((option) => (
          <span className="segment" key={option.value}>
            <input
              aria-label={labels[option.value]}
              checked={selectedTheme === option.value}
              className="segment-input"
              data-testid={`theme-${option.value}`}
              id={`theme-${option.value}`}
              name="theme"
              onChange={() => chooseTheme(option.value)}
              type="radio"
              value={option.value}
            />
            <label htmlFor={`theme-${option.value}`}>
              {labels[option.labelKey]}
            </label>
          </span>
        ))}
      </fieldset>
    </div>
  );
}
