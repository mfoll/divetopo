import { redirect } from "next/navigation";
import { getPreferences } from "./preferences";

export default async function Home() {
  const { language } = await getPreferences();
  redirect(`/${language}`);
}
