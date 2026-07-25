import { redirect } from "next/navigation";
import { getPreferences } from "../preferences";

export default async function ReunionHome() {
  const { language } = await getPreferences();
  redirect(`/reunion/${language}`);
}
