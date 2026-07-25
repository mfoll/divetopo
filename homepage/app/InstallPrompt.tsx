"use client";

import { useEffect, useId, useRef, useState } from "react";

type InstallPromptCopy = {
  iosTitle: string;
  iosInstructions: string;
  androidTitle: string;
  androidInstructions: string;
  installAction: string;
  dismiss: string;
};

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{
    outcome: "accepted" | "dismissed";
    platform: string;
  }>;
};

type InstallPlatform = "ios" | "android";

const DISMISSAL_STORAGE_KEY = "divetopo.install-prompt.dismissed-at.v1";
const DISMISSAL_DURATION_MS = 30 * 24 * 60 * 60 * 1000;
const DISPLAY_DELAY_MS = 3_000;

function isRecentlyDismissed() {
  try {
    const dismissedAt = Number(
      window.localStorage.getItem(DISMISSAL_STORAGE_KEY),
    );
    return (
      Number.isFinite(dismissedAt) &&
      dismissedAt > 0 &&
      Date.now() - dismissedAt < DISMISSAL_DURATION_MS
    );
  } catch {
    return false;
  }
}

function rememberDismissal() {
  try {
    window.localStorage.setItem(DISMISSAL_STORAGE_KEY, String(Date.now()));
  } catch {
    // The prompt can still be dismissed for this page view when storage is unavailable.
  }
}

function isStandalone(displayMode: MediaQueryList) {
  const navigatorWithStandalone = navigator as Navigator & {
    standalone?: boolean;
  };
  return displayMode.matches || navigatorWithStandalone.standalone === true;
}

function detectedPlatform(): InstallPlatform | null {
  const userAgent = navigator.userAgent;
  const isIPadOS =
    /Macintosh/i.test(userAgent) && navigator.maxTouchPoints > 1;

  if (/iPad|iPhone|iPod/i.test(userAgent) || isIPadOS) {
    return "ios";
  }
  if (/Android/i.test(userAgent)) {
    return "android";
  }
  return null;
}

export default function InstallPrompt({
  copy,
}: {
  copy: InstallPromptCopy;
}) {
  const titleId = useId();
  const [platform, setPlatform] = useState<InstallPlatform | null>(null);
  const deferredPrompt = useRef<BeforeInstallPromptEvent | null>(null);
  const delayElapsed = useRef(false);

  useEffect(() => {
    const displayMode = window.matchMedia("(display-mode: standalone)");
    const devicePlatform = detectedPlatform();

    if (
      devicePlatform === null ||
      isStandalone(displayMode) ||
      isRecentlyDismissed()
    ) {
      return;
    }

    function showWhenReady() {
      delayElapsed.current = true;
      if (
        devicePlatform === "ios" ||
        (devicePlatform === "android" && deferredPrompt.current)
      ) {
        setPlatform(devicePlatform);
      }
    }

    function handleBeforeInstallPrompt(event: Event) {
      if (devicePlatform !== "android") {
        return;
      }
      event.preventDefault();
      deferredPrompt.current = event as BeforeInstallPromptEvent;
      if (delayElapsed.current) {
        setPlatform("android");
      }
    }

    function hidePrompt() {
      deferredPrompt.current = null;
      setPlatform(null);
    }

    function handleDisplayModeChange() {
      if (isStandalone(displayMode)) {
        hidePrompt();
      }
    }

    const timer = window.setTimeout(showWhenReady, DISPLAY_DELAY_MS);
    window.addEventListener(
      "beforeinstallprompt",
      handleBeforeInstallPrompt,
    );
    window.addEventListener("appinstalled", hidePrompt);
    displayMode.addEventListener("change", handleDisplayModeChange);

    return () => {
      window.clearTimeout(timer);
      window.removeEventListener(
        "beforeinstallprompt",
        handleBeforeInstallPrompt,
      );
      window.removeEventListener("appinstalled", hidePrompt);
      displayMode.removeEventListener("change", handleDisplayModeChange);
    };
  }, []);

  function dismiss() {
    rememberDismissal();
    deferredPrompt.current = null;
    setPlatform(null);
  }

  async function install() {
    const promptEvent = deferredPrompt.current;
    if (!promptEvent) {
      return;
    }

    try {
      await promptEvent.prompt();
      await promptEvent.userChoice;
      dismiss();
    } catch {
      deferredPrompt.current = null;
      setPlatform(null);
    }
  }

  if (platform === null) {
    return null;
  }

  const title = platform === "ios" ? copy.iosTitle : copy.androidTitle;
  const instructions =
    platform === "ios"
      ? copy.iosInstructions
      : copy.androidInstructions;

  return (
    <aside
      className="install-prompt"
      aria-labelledby={titleId}
      aria-live="polite"
    >
      <div className="install-prompt-inner">
        <div className="install-prompt-copy">
          <strong id={titleId}>{title}</strong>
          <p>{instructions}</p>
        </div>
        <div className="install-prompt-actions">
          {platform === "android" ? (
            <button
              className="install-prompt-action"
              onClick={install}
              type="button"
            >
              {copy.installAction}
            </button>
          ) : null}
          <button
            aria-label={copy.dismiss}
            className="install-prompt-close"
            onClick={dismiss}
            type="button"
          >
            <svg
              aria-hidden="true"
              fill="none"
              focusable="false"
              stroke="currentColor"
              strokeLinecap="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
            >
              <path d="m6 6 12 12M18 6 6 18" />
            </svg>
          </button>
        </div>
      </div>
    </aside>
  );
}
