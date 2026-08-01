import type { Metadata } from "next";
import { notFound } from "next/navigation";
import {
  isLanguage,
  SUPPORTED_LANGUAGES,
} from "../../../content/routing";
import { getPreferences } from "../../preferences";
import {
  RegionalStructuredData,
  regionalMetadata,
} from "../../seo";
import PacaExperience from "../../PacaExperience";

type LanguagePageProps = {
  params: Promise<{ language: string }>;
};

export function generateStaticParams() {
  return SUPPORTED_LANGUAGES.map((language) => ({ language }));
}

export async function generateMetadata({
  params,
}: LanguagePageProps): Promise<Metadata> {
  const { language } = await params;
  if (!isLanguage(language)) {
    return {};
  }
  return regionalMetadata(language, "paca");
}

export default async function PacaLanguagePage({
  params,
}: LanguagePageProps) {
  const { language } = await params;
  if (!isLanguage(language)) {
    notFound();
  }

  const { theme } = await getPreferences();

  return (
    <>
      <RegionalStructuredData language={language} region="paca" />
      <PacaExperience language={language} theme={theme} />
    </>
  );
}
