import type { Metadata } from "next";
import PortissolTestExperience from "./PortissolTestExperience";

export const metadata: Metadata = {
  title: "Test local Pointe de Portissol | DiveTopo",
  robots: {
    index: false,
    follow: false,
  },
};

export default function PortissolTestPage() {
  return <PortissolTestExperience />;
}
