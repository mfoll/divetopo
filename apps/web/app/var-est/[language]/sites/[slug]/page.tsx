import type { Metadata } from "next";
import {
  regionalSiteMetadata,
  regionalSiteStaticParams,
  renderRegionalSite,
} from "../../../../regional-pages";

const REGION = "var-est" as const;
type Props = { params: Promise<{ language: string; slug: string }> };

export function generateStaticParams() {
  return regionalSiteStaticParams(REGION);
}
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { language, slug } = await params;
  return regionalSiteMetadata(language, slug, REGION);
}

export default async function RegionSitePage({ params }: Props) {
  const { language, slug } = await params;
  return renderRegionalSite(language, slug, REGION);
}
