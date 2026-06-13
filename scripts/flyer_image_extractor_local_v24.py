from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


def render_pdf(pdf_path: Path, output_dir: Path, scale: float) -> list[Path]:
    try:
        import fitz
    except Exception as exc:
        raise SystemExit("PyMuPDF mancante. Installa con: pip install PyMuPDF") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    pages = []

    for index, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        out = output_dir / f"page_{index:03d}.jpg"
        pix.save(out)
        pages.append(out)

    doc.close()
    return pages


def zip_pages(pages: list[Path], zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for page in pages:
            z.write(page, page.name)


def main() -> None:
    parser = argparse.ArgumentParser(description="No-OCR PDF flyer image extractor")
    parser.add_argument("pdf", help="PDF volantino")
    parser.add_argument("--out", default="flyer_pages_out", help="Cartella output")
    parser.add_argument("--scale", type=float, default=2.0, help="Qualità render")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    output_dir = Path(args.out)

    if not pdf_path.exists():
        raise SystemExit(f"PDF non trovato: {pdf_path}")

    pages = render_pdf(pdf_path, output_dir, args.scale)
    zip_path = output_dir / f"{pdf_path.stem}_pages.zip"
    zip_pages(pages, zip_path)

    print(f"OK: {len(pages)} pagine estratte")
    print(f"Cartella: {output_dir}")
    print(f"ZIP: {zip_path}")


if __name__ == "__main__":
    main()
