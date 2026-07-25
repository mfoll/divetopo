import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import { getPreferences } from "./preferences";
import "./globals.css";

const metadataCopy = {
  fr: {
    title: "DiveTopo · Cartes de sites de plongée",
    description:
      "Explorez des cartes topo-bathymétriques de sites de plongée, région par région.",
    socialTitle: "DiveTopo · Le relief sous-marin, région par région",
    socialDescription:
      "Des plans 2D, perspectives 3D et reliefs interactifs de sites de plongée.",
    socialAlt: "DiveTopo, cartographies de sites de plongée",
    locale: "fr_FR",
  },
  en: {
    title: "DiveTopo · Dive site maps",
    description:
      "Explore topographic and bathymetric maps of dive sites, region by region.",
    socialTitle: "DiveTopo · Underwater terrain, region by region",
    socialDescription:
      "2D maps, 3D views and interactive terrain for selected dive sites.",
    socialAlt: "DiveTopo, dive site maps",
    locale: "en_GB",
  },
} as const;

export const viewport: Viewport = {
  initialScale: 1,
  width: "device-width",
};

export async function generateMetadata(): Promise<Metadata> {
  const [{ language }, requestHeaders] = await Promise.all([
    getPreferences(),
    headers(),
  ]);
  const text = metadataCopy[language];
  const host =
    requestHeaders.get("x-forwarded-host") ??
    requestHeaders.get("host") ??
    "localhost:3000";
  const protocol =
    requestHeaders.get("x-forwarded-proto") ??
    (host.startsWith("localhost") ? "http" : "https");
  const origin = `${protocol}://${host}`;
  const socialImage = new URL("/og.png", origin).toString();

  return {
    title: text.title,
    description: text.description,
    icons: {
      icon: "/favicon.svg",
      shortcut: "/favicon.svg",
    },
    openGraph: {
      title: text.socialTitle,
      description: text.socialDescription,
      locale: text.locale,
      type: "website",
      images: [
        {
          url: socialImage,
          width: 1200,
          height: 630,
          alt: text.socialAlt,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: text.socialTitle,
      description: text.socialDescription,
      images: [{ url: socialImage, alt: text.socialAlt }],
    },
  };
}

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
