import type { Metadata, Viewport } from "next";
import { getPreferences } from "./preferences";
import { DIVETOPO_ORIGIN } from "../content/routing";
import "./globals.css";

export const viewport: Viewport = {
  initialScale: 1,
  // Vinext 0.0.50 does not yet serialize Viewport.viewportFit. Keeping the
  // directive in the width string produces one valid viewport meta tag.
  width: "device-width, viewport-fit=cover",
};

export const metadata: Metadata = {
  metadataBase: new URL(DIVETOPO_ORIGIN),
  applicationName: "DiveTopo",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    title: "DiveTopo",
    statusBarStyle: "black-translucent",
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

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const { language, theme } = await getPreferences();

  return (
    <html lang={language} data-theme={theme}>
      <body>{children}</body>
    </html>
  );
}
