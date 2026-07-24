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
      default: "Cartes de plongée à La Réunion",
      template: "%s · Plongée à La Réunion",
    },
    description:
      "Plans 2D, vues 3D et reliefs interactifs des sites de plongée à La Réunion.",
    icons: {
      icon: "/favicon.png",
      shortcut: "/favicon.png",
    },
    openGraph: {
      title: "Cartes de plongée à La Réunion",
      description:
        "Plans 2D, vues 3D et reliefs interactifs des sites de plongée à La Réunion.",
      locale: "fr_FR",
      type: "website",
      images: [
        {
          url: socialImage,
          width: 1200,
          height: 630,
          alt: "Cartes de plongée à La Réunion",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: "Cartes de plongée à La Réunion",
      description:
        "Plans 2D, vues 3D et reliefs interactifs des sites de plongée à La Réunion.",
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
