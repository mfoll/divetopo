import { redirect } from "next/navigation";
import { getPreferences } from "../preferences";

export default async function PacaHome() {
  const { language } = await getPreferences();
  redirect(`/paca/${language}`);
}
