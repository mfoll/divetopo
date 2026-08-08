import { permanentRedirect } from "next/navigation";
import { isLanguage } from "../../../content/routing";

type Props = { params: Promise<{ language: string }> };

export default async function LegacyPacaLanguagePage({ params }: Props) {
  const { language } = await params;
  permanentRedirect(isLanguage(language) ? `/${language}#regions` : "/fr#regions");
}
