import { TopoReunionExperience } from "./TopoReunionExperience";
import { getPreferences } from "./preferences";

export default async function Home() {
  const preferences = await getPreferences();
  return <TopoReunionExperience {...preferences} />;
}
