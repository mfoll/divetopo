import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import {
  findRegionalSite,
  isLanguage,
  publishedSitesForRegion,
  SUPPORTED_LANGUAGES,
} from "../content/routing";
import type { AutonomousMediterraneanRegionSlug } from "../content/regional";
import EmptyRegionExperience from "./EmptyRegionExperience";
import { getPreferences } from "./preferences";
import RegionalExperience from "./RegionalExperience";
import {
  RegionalStructuredData,
  regionalMetadata,
  SiteStructuredData,
  siteMetadata,
} from "./seo";

export function regionalStaticParams() {
  return SUPPORTED_LANGUAGES.map((language) => ({ language }));
}

export async function regionalPageMetadata(
  language: string,
  region: AutonomousMediterraneanRegionSlug,
): Promise<Metadata> {
  return isLanguage(language) ? regionalMetadata(language, region) : {};
}

export async function renderRegionalPage(
  language: string,
  region: AutonomousMediterraneanRegionSlug,
) {
  if (!isLanguage(language)) notFound();
  const { theme } = await getPreferences();
  const sites = publishedSitesForRegion(region);
  return (
    <>
      <RegionalStructuredData language={language} region={region} />
      {sites.length > 0 ? (
        <RegionalExperience
          region={region}
          language={language}
          theme={theme}
        />
      ) : (
        <EmptyRegionExperience
          region={region}
          language={language}
          theme={theme}
        />
      )}
    </>
  );
}

export function regionalSiteStaticParams(
  region: AutonomousMediterraneanRegionSlug,
) {
  return SUPPORTED_LANGUAGES.flatMap((language) =>
    publishedSitesForRegion(region).map((site) => ({
      language,
      slug: site.slug,
    })),
  );
}

export async function regionalSiteMetadata(
  language: string,
  slug: string,
  region: AutonomousMediterraneanRegionSlug,
): Promise<Metadata> {
  const site = findRegionalSite(region, slug);
  return isLanguage(language) && site
    ? siteMetadata(language, site, region)
    : {};
}

export async function renderRegionalSite(
  language: string,
  slug: string,
  region: AutonomousMediterraneanRegionSlug,
) {
  const site = findRegionalSite(region, slug);
  if (!isLanguage(language) || !site) notFound();
  const { theme } = await getPreferences();
  return (
    <>
      <SiteStructuredData language={language} site={site} region={region} />
      <RegionalExperience
        region={region}
        initialSlug={site.slug}
        language={language}
        theme={theme}
      />
    </>
  );
}

export async function redirectToRegionalSite(
  slug: string,
  region: AutonomousMediterraneanRegionSlug,
) {
  if (!findRegionalSite(region, slug)) notFound();
  const { language } = await getPreferences();
  redirect(`/${region}/${language}/sites/${slug}`);
}
