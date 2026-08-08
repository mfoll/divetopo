import { notFound, permanentRedirect } from "next/navigation";
import { legacyPacaSiteRegions } from "../../../../content/legacy-paca";

type Props = { params: Promise<{ slug: string }> };

export default async function LegacyPacaSitePage({ params }: Props) {
  const { slug } = await params;
  const region = legacyPacaSiteRegions[slug];
  if (!region) notFound();
  permanentRedirect(`/${region}/fr/sites/${slug}`);
}
