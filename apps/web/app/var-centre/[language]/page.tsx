import type { Metadata } from "next";
import {
  regionalPageMetadata,
  regionalStaticParams,
  renderRegionalPage,
} from "../../regional-pages";

const REGION = "var-centre" as const;
type Props = { params: Promise<{ language: string }> };

export const generateStaticParams = regionalStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { language } = await params;
  return regionalPageMetadata(language, REGION);
}
export default async function RegionLanguagePage({ params }: Props) {
  const { language } = await params;
  return renderRegionalPage(language, REGION);
}
