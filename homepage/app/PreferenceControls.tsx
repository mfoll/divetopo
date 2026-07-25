"use client";

import { useEffect, useState } from "react";
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

const themeOptions = ["light", "auto", "dark"] as const;

function ThemeIcon({ theme }: { theme: Theme }) {
  if (theme === "light") {
    return (
      <svg
        aria-hidden="true"
        className="theme-choice-icon"
        fill="none"
        focusable="false"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.8"
        viewBox="0 0 24 24"
      >
        <circle cx="12" cy="12" r="3.75" />
        <path d="M12 2.25v2M12 19.75v2M4.25 12h-2M21.75 12h-2M5.1 5.1l1.42 1.42M17.48 17.48l1.42 1.42M18.9 5.1l-1.42 1.42M6.52 17.48 5.1 18.9" />
      </svg>
    );
  }

  if (theme === "auto") {
    return (
      <svg
        aria-hidden="true"
        className="theme-choice-icon"
        fill="none"
        focusable="false"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.8"
        viewBox="0 0 24 24"
      >
        <rect height="13" rx="2" width="18" x="3" y="4" />
        <path d="M8.5 21h7M12 17v4" />
      </svg>
    );
  }

  return (
    <svg
      aria-hidden="true"
      className="theme-choice-icon"
      fill="none"
      focusable="false"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.8"
      viewBox="0 0 24 24"
    >
      <path d="M20.75 14.25A8.75 8.75 0 1 1 9.75 3.3a7 7 0 0 0 11 10.95Z" />
    </svg>
  );
}

function sharedCookieDomain() {
  const hostname = window.location.hostname.toLowerCase();
  return hostname === "divetopo.com" || hostname.endsWith(".divetopo.com")
    ? "; Domain=.divetopo.com"
    : "";
}

function writePreference(name: string, value: string) {
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  const domain = sharedCookieDomain();

  if (domain) {
    document.cookie = `${name}=; Path=/; Max-Age=0; SameSite=Lax${secure}`;
  }

  document.cookie = `${name}=${encodeURIComponent(value)}; Path=/; Max-Age=${COOKIE_MAX_AGE_SECONDS}; SameSite=Lax${domain}${secure}`;
}

function hasPreference(name: string) {
  return document.cookie
    .split(";")
    .some((entry) => entry.trim().startsWith(`${name}=`));
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

  useEffect(() => {
    if (!sharedCookieDomain()) {
      return;
    }

    if (hasPreference(LANGUAGE_COOKIE)) {
      writePreference(LANGUAGE_COOKIE, language);
    }
    if (hasPreference(THEME_COOKIE)) {
      writePreference(THEME_COOKIE, selectedTheme);
    }
  }, [language, selectedTheme]);

  function chooseLanguage(nextLanguage: Language) {
    if (nextLanguage === language) {
      return;
    }

    writePreference(LANGUAGE_COOKIE, nextLanguage);
    window.location.assign(`/${nextLanguage}${window.location.search}`);
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
          <button
            aria-label={
              option.value === "fr" ? labels.french : labels.english
            }
            aria-pressed={language === option.value}
            className="language-choice"
            data-testid={`language-${option.value}`}
            key={option.value}
            onClick={() => chooseLanguage(option.value)}
            onMouseDown={(event) => event.preventDefault()}
            type="button"
          >
            {option.shortLabel}
          </button>
        ))}
      </fieldset>

      <fieldset className="segmented-control theme-control">
        <legend className="sr-only">{labels.themeGroup}</legend>
        {themeOptions.map((option) => (
          <span className="segment" key={option}>
            <input
              aria-label={labels[option]}
              checked={selectedTheme === option}
              className="segment-input"
              data-testid={`theme-${option}`}
              id={`theme-${option}`}
              name="theme"
              onChange={() => chooseTheme(option)}
              type="radio"
              value={option}
            />
            <label htmlFor={`theme-${option}`} title={labels[option]}>
              <ThemeIcon theme={option} />
            </label>
          </span>
        ))}
      </fieldset>
    </div>
  );
}
