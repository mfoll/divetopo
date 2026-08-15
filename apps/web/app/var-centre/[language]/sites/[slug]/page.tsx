import type { Metadata } from "next";
import { permanentRedirect } from "next/navigation";
import {
  regionalSiteMetadata,
  regionalSiteStaticParams,
  renderRegionalSite,
} from "../../../../regional-pages";

const REGION = "var-centre" as const;
const MERGED_SLUG = "sec-du-langoustier";
const CANONICAL_SLUG = "sec-de-la-jeaune-garde";
type Props = { params: Promise<{ language: string; slug: string }> };

export function generateStaticParams() {
  const params = regionalSiteStaticParams(REGION);
  return [
    ...params,
    ...params
      .filter(({ slug }) => slug === CANONICAL_SLUG)
      .map(({ language }) => ({ language, slug: MERGED_SLUG })),
  ];
}
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { language, slug } = await params;
  return regionalSiteMetadata(
    language,
    slug === MERGED_SLUG ? CANONICAL_SLUG : slug,
    REGION,
  );
}

export default async function RegionSitePage({ params }: Props) {
  const { language, slug } = await params;
  if (slug === MERGED_SLUG) {
    permanentRedirect(`/${REGION}/${language}/sites/${CANONICAL_SLUG}`);
  }
  return renderRegionalSite(language, slug, REGION);
}
