import type { Metadata } from "next";
import { notFound } from "next/navigation";
import {
  findPacaSite,
  isLanguage,
  pacaPublishedSites,
  SUPPORTED_LANGUAGES,
} from "../../../../../content/routing";
import { getPreferences } from "../../../../preferences";
import {
  SiteStructuredData,
  siteMetadata,
} from "../../../../seo";
import PacaExperience from "../../../../PacaExperience";

type SitePageProps = {
  params: Promise<{ language: string; slug: string }>;
};

export function generateStaticParams() {
  return SUPPORTED_LANGUAGES.flatMap((language) =>
    pacaPublishedSites.map((site) => ({ language, slug: site.slug })),
  );
}

export async function generateMetadata({
  params,
}: SitePageProps): Promise<Metadata> {
  const { language, slug } = await params;
  const site = findPacaSite(slug);
  if (!isLanguage(language) || !site) {
    return {};
  }
  return siteMetadata(language, site, "paca");
}

export default async function PacaSitePage({ params }: SitePageProps) {
  const { language, slug } = await params;
  const site = findPacaSite(slug);
  if (!isLanguage(language) || !site) {
    notFound();
  }

  const { theme } = await getPreferences();

  return (
    <>
      <SiteStructuredData language={language} site={site} region="paca" />
      <PacaExperience
        initialSlug={site.slug}
        language={language}
        theme={theme}
      />
    </>
  );
}
