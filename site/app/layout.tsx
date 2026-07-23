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
    title: {
      default: "Reliefs de l’Ouest",
      template: "%s · Reliefs de l’Ouest",
    },
    description:
      "Plans 2D, perspectives et reliefs 3D interactifs de la côte ouest de La Réunion.",
    icons: {
      icon: "/favicon.png",
      shortcut: "/favicon.png",
    },
    openGraph: {
      title: "Reliefs de l’Ouest",
      description:
        "Lire la côte sous la surface, du plan 2D au relief 3D interactif.",
      locale: "fr_FR",
      type: "website",
      images: [
        {
          url: socialImage,
          width: 1200,
          height: 630,
          alt: "Reliefs de l’Ouest — Lire la côte sous la surface",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: "Reliefs de l’Ouest",
      description:
        "Lire la côte sous la surface, du plan 2D au relief 3D interactif.",
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
