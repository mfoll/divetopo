import type { Metadata } from "next";
import PyramidesTestExperience from "./PyramidesTestExperience";

export const metadata: Metadata = {
  title: "Test local Les Pyramides | DiveTopo",
  robots: {
    index: false,
    follow: false,
  },
};

export default function PyramidesTestPage() {
  return <PyramidesTestExperience />;
}
