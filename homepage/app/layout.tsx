import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
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
    title: "DiveTopo · Cartes de sites de plongée",
    description:
      "Explorez des cartes topo-bathymétriques de sites de plongée, région par région.",
    icons: {
      icon: "/favicon.svg",
      shortcut: "/favicon.svg",
    },
    openGraph: {
      title: "DiveTopo · Le relief sous-marin, région par région",
      description:
        "Des plans 2D, perspectives 3D et reliefs interactifs de sites de plongée.",
      locale: "fr_FR",
      type: "website",
      images: [
        {
          url: socialImage,
          width: 1200,
          height: 630,
          alt: "DiveTopo, cartographies de sites de plongée",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: "DiveTopo · Le relief sous-marin, région par région",
      description:
        "Des plans 2D, perspectives 3D et reliefs interactifs de sites de plongée.",
      images: [socialImage],
    },
  };
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
