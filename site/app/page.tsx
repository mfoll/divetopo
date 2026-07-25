import { AtlasExperience } from "./AtlasExperience";
import { getPreferences } from "./preferences";

export default async function Home() {
  const preferences = await getPreferences();
  return <AtlasExperience {...preferences} />;
}
