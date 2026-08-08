import { notFound, permanentRedirect, redirect } from "next/navigation";
import {
  canonicalReunionSiteSlug,
  findPublishedSite,
} from "../../../../content/routing";
import { getPreferences } from "../../../preferences";

export default async function DefaultSitePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const canonicalSlug = canonicalReunionSiteSlug(slug);
  if (canonicalSlug !== slug) {
    permanentRedirect(`/reunion/sites/${canonicalSlug}`);
  }

  if (!findPublishedSite(slug)) {
    notFound();
  }

  const { language } = await getPreferences();
  redirect(`/reunion/${language}/sites/${slug}`);
}
