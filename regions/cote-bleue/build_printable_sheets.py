"""Build Côte Bleue A4 sheets with the DiveTopo composer, ReportLab and pdftoppm."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from PIL import Image
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen.canvas import Canvas

ROOT = Path(__file__).resolve().parents[2]
REGION = ROOT / "regions/cote-bleue"
sys.path.insert(0, str(ROOT))
from cartography.plate import _plate_paths, compose

# Label origin and pointer target are normalized to the 2D panel, from the bottom left.
ANNOTATIONS = {
    "tombant-de-mejean": [
        ("Plateau des Écueils", (0.24, 0.46), (0.39, 0.33)),
        ("Tombant", (0.33, 0.16), (0.46, 0.21)),
    ],
    "tombant-de-l-erevine": [
        ("Îlot de l’Érevine", (0.12, 0.58), (0.35, 0.56)),
        ("Tombant côté large", (0.29, 0.12), (0.49, 0.2)),
    ],
    "yeux-de-chat": [
        ("Secteur du sec", (0.25, 0.44), (0.42, 0.38)),
        ("Falaise de Méjean", (0.66, 0.67), (0.65, 0.52)),
    ],
    "jardins-de-sausset": [
        ("Corniche de Sausset", (0.23, 0.91), (0.44, 0.91)),
        ("Rebord du plateau", (0.29, 0.34), (0.47, 0.22)),
    ],
    "les-jonquiers": [
        ("Calanque du Jonquier", (0.19, 0.81), (0.44, 0.765)),
        ("Tombant des Jonquiers", (0.6, 0.69), (0.53, 0.59)),
    ],
    "le-moulon": [
        ("Presqu’île du Moulon", (0.4, 0.87), (0.5, 0.77)),
        ("Tombant du Moulon", (0.75, 0.64), (0.64, 0.69)),
    ],
    "cap-frapaou": [
        ("Cap Frapaou", (0.19, 0.52), (0.32, 0.34)),
        ("Tombant", (0.31, 0.28), (0.34, 0.2)),
        ("Limite des mesures", (0.65, 0.075), (0.72, 0.13)),
    ],
}


def wrap_pdf(jpeg, pdf_path, config, style):
    slug = config["slug"]
    page_w, page_h = landscape(A4)
    with Image.open(jpeg) as image:
        width, height = image.size
    scale = (page_w - 24) / width
    art_x = 12
    art_y = (page_h - height * scale) / 2
    pdf = Canvas(str(pdf_path), pagesize=(page_w, page_h), invariant=True)
    pdf.setTitle(f"{config['plate_site_name']} | DiveTopo")
    pdf.setAuthor(config["plate_author"])
    pdf.drawImage(str(jpeg), art_x, art_y, width * scale, height * scale)

    # Match the panels rendered by cartography.plate.compose.
    plan, relief, _, _ = _plate_paths(config, style)
    panel_w = (width - 200) // 2
    with Image.open(plan) as image:
        plan_h = round(image.height * panel_w / image.width)
    with Image.open(relief) as image:
        relief_h = round(image.height * panel_w / image.width)
    panel_x = art_x + 80 * scale
    panel_y = art_y + (80 + max(plan_h, relief_h) - plan_h) * scale
    panel_width = panel_w * scale
    panel_height = plan_h * scale
    pdf.setLineCap(1)
    pdf.setFont("Helvetica-Bold", 6.8)
    for name, (left, bottom), (target_x, target_y) in ANNOTATIONS[slug]:
        label_width = pdf.stringWidth(name, "Helvetica-Bold", 6.8) + 9
        x = min(panel_x + left * panel_width, panel_x + panel_width - label_width - 6)
        y = panel_y + bottom * panel_height
        tx = panel_x + target_x * panel_width
        ty = panel_y + target_y * panel_height
        for color, weight in ((HexColor("#263a44"), 1.55), (white, 0.7)):
            pdf.setStrokeColor(color)
            pdf.setLineWidth(weight)
            pdf.line(x + label_width / 2, y + 5.8, tx, ty)
        pdf.setFillColor(white)
        pdf.circle(tx, ty, 1.45, fill=1, stroke=0)
        pdf.roundRect(x, y, label_width, 11.5, 2.5, fill=1, stroke=0)
        pdf.setFillColor(HexColor("#182329"))
        pdf.drawString(x + 4.5, y + 3.2, name)

    pdf.setFillColor(HexColor("#4d5b61"))
    pdf.setFont("Helvetica", 7.3)
    y = art_y + 80 * scale - 10
    caution = "Repères indicatifs · Profondeurs rapportées au zéro IGN69"
    if slug == "cap-frapaou":
        caution = "Repères indicatifs · Gris : fond non mesuré · Levé jusqu’à 47 m (IGN69)"
    elif slug == "le-moulon":
        caution = "Repères indicatifs · Les isobathes s’arrêtent en bordure des mesures · IGN69"
    elif slug in {"tombant-de-mejean", "tombant-de-l-erevine", "yeux-de-chat"}:
        caution = "Repères indicatifs · Gris : données absentes · Profondeurs rapportées au zéro IGN69"
    pdf.drawString(panel_x, y, caution)
    pdf.drawRightString(page_w - panel_x, y, "Hors navigation")
    if slug == "yeux-de-chat":
        pdf.drawString(panel_x, y - 10, "Le tracé de la faille reste à confirmer. L’intérieur de la grotte est hors levé.")
    if slug == "le-moulon":
        atlas = "Parc marin, atlas Côte Bleue Marine, carte 60"
        pdf.drawString(panel_x, y - 10, atlas)
        pdf.linkURL(
            "https://cotebleuemarine.n2000.fr/concretement-pour-vous/le-document-d-objectif-docob",
            (panel_x, y - 12, panel_x + pdf.stringWidth(atlas, "Helvetica", 7.3), y - 2),
            relative=0,
        )
        pdf.drawRightString(page_w - panel_x, y - 10, "Modèle de surface autour de l’arche.")
    pdf.showPage()
    pdf.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sites", nargs="*", metavar="SITE")
    args = parser.parse_args()
    unknown = set(args.sites) - ANNOTATIONS.keys()
    if unknown:
        parser.error("Unknown site: " + ", ".join(sorted(unknown)))
    outputs = REGION / "outputs"
    with tempfile.TemporaryDirectory() as temp:
        for slug in args.sites or ANNOTATIONS:
            config = json.loads((REGION / "sites" / f"{slug}.json").read_text())
            config["locator_marker_utm40s"] = config["site_location_utm40s"]
            # Use the saved classic 3D captures, independent of the interactive toggle.
            config["plate_relief_source"] = "interactive"
            config["paths"] = {
                **config.get("paths", {}),
                "output_plate": str(Path(temp) / "orthophoto.jpg"),
                "output_plate_topography": str(Path(temp) / "topographic.jpg"),
            }
            for style in ("topographic", "orthophoto"):
                basename = f"{slug}-orthophoto-a4" if style == "orthophoto" else f"{slug}-a4"
                jpeg = compose(config, style)
                pdf_path = outputs / f"{basename}.pdf"
                wrap_pdf(jpeg, pdf_path, config, style)
                render = Path(temp) / "preview"
                subprocess.run(
                    ["pdftoppm", "-singlefile", "-scale-to", "1500", "-png", str(pdf_path), str(render)],
                    check=True,
                )
                with Image.open(render.with_suffix(".png")) as image:
                    image.save(outputs / f"{basename}-preview.webp", quality=88)


if __name__ == "__main__":
    main()
