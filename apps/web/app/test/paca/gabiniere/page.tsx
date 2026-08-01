import type { Metadata } from "next";
import GabiniereTestExperience from "./GabiniereTestExperience";

export const metadata: Metadata = {
  title: "Test local La Gabinière | DiveTopo",
  robots: {
    index: false,
    follow: false,
  },
};

export default function GabiniereTestPage() {
  return <GabiniereTestExperience />;
}
