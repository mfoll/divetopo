import { permanentRedirect } from "next/navigation";

export default function LegacyPacaPage() {
  permanentRedirect("/fr#regions");
}
