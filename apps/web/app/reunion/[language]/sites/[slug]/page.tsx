import type { Metadata } from "next";
import { notFound } from "next/navigation";
import {
  findPublishedSite,
  isLanguage,
  publishedSites,
  SUPPORTED_LANGUAGES,
} from "../../../../../content/routing";
import { getPreferences } from "../../../../preferences";
import {
  SiteStructuredData,
  siteMetadata,
} from "../../../../seo";
import { TopoReunionExperience } from "../../../../TopoReunionExperience";

type SitePageProps = {
  params: Promise<{ language: string; slug: string }>;
};

export function generateStaticParams() {
  return SUPPORTED_LANGUAGES.flatMap((language) =>
    publishedSites.map((site) => ({ language, slug: site.slug })),
  );
}

export async function generateMetadata({
  params,
}: SitePageProps): Promise<Metadata> {
  const { language, slug } = await params;
  const site = findPublishedSite(slug);
  if (!isLanguage(language) || !site) {
    return {};
  }
  return siteMetadata(language, site);
}

export default async function SitePage({ params }: SitePageProps) {
  const { language, slug } = await params;
  const site = findPublishedSite(slug);
  if (!isLanguage(language) || !site) {
    notFound();
  }

  const { theme } = await getPreferences();

  return (
    <>
      <SiteStructuredData language={language} site={site} />
      <TopoReunionExperience
        initialSlug={site.slug}
        language={language}
        theme={theme}
      />
    </>
  );
}
