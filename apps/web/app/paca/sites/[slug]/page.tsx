import { notFound, redirect } from "next/navigation";
import { findPacaSite } from "../../../../content/routing";
import { getPreferences } from "../../../preferences";

export default async function DefaultPacaSitePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  if (!findPacaSite(slug)) {
    notFound();
  }

  const { language } = await getPreferences();
  redirect(`/paca/${language}/sites/${slug}`);
}
