import type { Metadata } from "next";
import CapDesMedesTestExperience from "./CapDesMedesTestExperience";

export const metadata: Metadata = {
  title: "Test local Cap des Mèdes | DiveTopo",
  robots: {
    index: false,
    follow: false,
  },
};

export default function CapDesMedesTestPage() {
  return <CapDesMedesTestExperience />;
}
