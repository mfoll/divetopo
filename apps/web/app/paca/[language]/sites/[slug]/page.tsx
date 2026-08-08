import { notFound, permanentRedirect } from "next/navigation";
import { legacyPacaSiteRegions } from "../../../../../content/legacy-paca";
import { isLanguage } from "../../../../../content/routing";

type Props = { params: Promise<{ language: string; slug: string }> };

export default async function LegacyPacaSitePage({ params }: Props) {
  const { language, slug } = await params;
  const region = legacyPacaSiteRegions[slug];
  if (!isLanguage(language) || !region) notFound();
  permanentRedirect(`/${region}/${language}/sites/${slug}`);
}
