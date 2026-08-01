import type { Metadata } from "next";
import DeuxFreresTestExperience from "./DeuxFreresTestExperience";

export const metadata: Metadata = {
  title: "Test local Les Deux Frères | DiveTopo",
  robots: {
    index: false,
    follow: false,
  },
};

export default function DeuxFreresTestPage() {
  return <DeuxFreresTestExperience />;
}
