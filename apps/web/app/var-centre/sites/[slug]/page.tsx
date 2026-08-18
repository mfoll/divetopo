import { redirectToRegionalSite } from "../../../regional-pages";

type Props = { params: Promise<{ slug: string }> };

export default async function DefaultRegionSitePage({ params }: Props) {
  const { slug } = await params;
  return redirectToRegionalSite(slug, "var-centre");
}
