import { notFound, redirect } from "next/navigation";
import { findPublishedSite } from "../../../content/routing";
import { getPreferences } from "../../preferences";

export default async function DefaultSitePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  if (!findPublishedSite(slug)) {
    notFound();
  }

  const { language } = await getPreferences();
  redirect(`/${language}/sites/${slug}`);
}
