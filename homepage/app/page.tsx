import HomepageExperience from "./HomepageExperience";
import { getPreferences } from "./preferences";

export default async function Home() {
  const preferences = await getPreferences();
  return <HomepageExperience {...preferences} />;
}
