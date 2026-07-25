import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import { getPreferences } from "./preferences";
import "./globals.css";

const metadataCopy = {
  fr: {
    title: "Plans des sites de plongée à La Réunion",
    description:
      "Plans topo-bathymétriques 2D, perspectives 3D et reliefs interactifs de sites de plongée à La Réunion.",
    socialAlt: "Plans des sites de plongée à La Réunion",
    locale: "fr_FR",
  },
  en: {
    title: "Dive site maps of Réunion Island",
    description:
      "Explore 2D topographic-bathymetric maps, 3D perspectives and interactive terrain for dive sites around Réunion Island.",
    socialAlt: "Dive site maps of Réunion Island",
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
      title: text.title,
      description: text.description,
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
      title: text.title,
      description: text.description,
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
