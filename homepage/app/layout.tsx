import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import { getPreferences, languageFromPathname } from "./preferences";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://divetopo.com"),
  applicationName: "DiveTopo",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    title: "DiveTopo",
    statusBarStyle: "default",
  },
  other: {
    "apple-mobile-web-app-capable": "yes",
  },
  icons: {
    icon: [{ url: "/favicon.svg", type: "image/svg+xml" }],
    shortcut: "/favicon.svg",
    apple: [
      {
        url: "/apple-touch-icon.png",
        sizes: "180x180",
        type: "image/png",
      },
    ],
  },
};

export const viewport: Viewport = {
  initialScale: 1,
  width: "device-width",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [preferences, requestHeaders] = await Promise.all([
    getPreferences(),
    headers(),
  ]);
  const language =
    languageFromPathname(requestHeaders.get("x-divetopo-pathname")) ??
    preferences.language;

  return (
    <html lang={language} data-theme={preferences.theme}>
      <body>{children}</body>
    </html>
  );
}
