#!/usr/bin/env python3
"""Prepare reproducible source files for textbook quick-reference work.

The script is intentionally dependency-light. It prefers Poppler commands when
available and falls back to optional Python PDF libraries only for page count.
OCR engines are not invoked here; this script prepares stable inputs and
records enough metadata for later OCR or no-OCR processing.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(cmd: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def which(name: str) -> str | None:
    return shutil.which(name)


def page_count_from_pdfinfo(pdf: Path) -> int | None:
    if not which("pdfinfo"):
        return None
    proc = run(["pdfinfo", str(pdf)])
    if proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        if line.startswith("Pages:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None


def page_count_from_python(pdf: Path) -> int | None:
    for module_name in ("pypdf", "PyPDF2"):
        try:
            if module_name == "pypdf":
                from pypdf import PdfReader  # type: ignore
            else:
                from PyPDF2 import PdfReader  # type: ignore
            return len(PdfReader(str(pdf)).pages)
        except Exception:
            continue
    return None


def get_page_count(pdf: Path) -> int:
    count = page_count_from_pdfinfo(pdf) or page_count_from_python(pdf)
    if not count:
        raise SystemExit("Could not determine PDF page count. Install poppler pdfinfo or pypdf.")
    return count


def extract_page_text(pdf: Path, page: int) -> tuple[str, str]:
    if which("pdftotext"):
        proc = run(["pdftotext", "-layout", "-enc", "UTF-8", "-f", str(page), "-l", str(page), str(pdf), "-"])
        if proc.returncode == 0:
            return proc.stdout, "pdftotext"
        return "", f"pdftotext-error: {proc.stderr.strip()[:200]}"
    return "", "missing-pdftotext"


def render_page(pdf: Path, page: int, out_png: Path, dpi: int) -> str:
    if not which("pdftoppm"):
        return "missing-pdftoppm"
    prefix = out_png.with_suffix("")
    proc = run(["pdftoppm", "-r", str(dpi), "-png", "-f", str(page), "-singlefile", str(pdf), str(prefix)])
    if proc.returncode != 0:
        return f"pdftoppm-error: {proc.stderr.strip()[:200]}"
    rendered = prefix.with_suffix(".png")
    if rendered != out_png and rendered.exists():
        rendered.replace(out_png)
    return "ok" if out_png.exists() else "render-missing"


def split_spread_image(image_path: Path, out_dir: Path) -> list[str]:
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return ["missing-pillow"]
    with Image.open(image_path) as im:
        w, h = im.size
        left = im.crop((0, 0, w // 2, h))
        right = im.crop((w // 2, 0, w, h))
        left_path = out_dir / f"{image_path.stem}-left.png"
        right_path = out_dir / f"{image_path.stem}-right.png"
        left.save(left_path)
        right.save(right_path)
    return [str(left_path), str(right_path)]


def sample_pages(page_count: int, first_printed_pdf_page: int | None, spec: str) -> list[int]:
    if spec == "none":
        return []
    if spec and spec != "auto":
        pages = []
        for part in spec.split(","):
            part = part.strip()
            if not part:
                continue
            pages.append(int(part))
        return sorted({p for p in pages if 1 <= p <= page_count})
    candidates = {1, 2, page_count}
    if first_printed_pdf_page:
        candidates.update({first_printed_pdf_page, first_printed_pdf_page + 1})
    candidates.add(max(1, page_count // 2))
    return sorted({p for p in candidates if 1 <= p <= page_count})


def printed_label(
    pdf_page: int,
    first_printed_pdf_page: int | None,
    first_printed_page_number: int,
    prefix: str,
    spread_pages: bool,
    side_index: int = 0,
) -> str:
    if not first_printed_pdf_page or pdf_page < first_printed_pdf_page:
        return ""
    offset = pdf_page - first_printed_pdf_page
    printed_number = first_printed_page_number + offset * (2 if spread_pages else 1) + side_index
    return f"{prefix}{printed_number}"


def text_stats(text: str) -> dict[str, int | float]:
    non_ws = sum(1 for ch in text if not ch.isspace())
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    replacement = text.count("\ufffd")
    return {
        "chars_non_ws": non_ws,
        "cjk_chars": cjk,
        "replacement_chars": replacement,
        "cjk_ratio": round(cjk / non_ws, 4) if non_ws else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare reproducible textbook PDF source files.")
    parser.add_argument("pdf", type=Path, help="Input textbook PDF")
    parser.add_argument("outdir", type=Path, help="Output source package directory")
    parser.add_argument("--mode", choices=("auto", "text", "ocr-prep"), default="auto")
    parser.add_argument("--first-printed-pdf-page", type=int, default=None, help="1-based PDF page that maps to the first printed textbook page")
    parser.add_argument("--first-printed-page-number", type=int, default=1)
    parser.add_argument("--printed-prefix", default="P")
    parser.add_argument("--spread-pages", action="store_true", help="Treat each PDF page as a left/right two-page spread for page_map.csv")
    parser.add_argument("--render-samples", default="auto", help="'auto', 'none', or comma-separated 1-based PDF pages")
    parser.add_argument("--render-all", action="store_true", help="Render every PDF page to PNG for OCR")
    parser.add_argument("--split-spreads", action="store_true", help="Split rendered spread images into left/right halves when Pillow is installed")
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()

    pdf = args.pdf.expanduser().resolve()
    if not pdf.exists():
        raise SystemExit(f"PDF does not exist: {pdf}")
    outdir = args.outdir.expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    text_dir = outdir / "page_texts_raw"
    image_dir = outdir / ("page_images_all" if args.render_all else "page_images_sample")
    split_dir = outdir / "page_images_split"
    text_dir.mkdir(exist_ok=True)
    if args.render_all or args.render_samples != "none":
        image_dir.mkdir(exist_ok=True)
    if args.split_spreads:
        split_dir.mkdir(exist_ok=True)

    page_count = get_page_count(pdf)
    pages_for_text = range(1, page_count + 1) if args.mode in ("auto", "text") else []
    page_text_stats: list[dict[str, object]] = []
    extraction_methods: set[str] = set()

    for page in pages_for_text:
        text, method = extract_page_text(pdf, page)
        extraction_methods.add(method)
        (text_dir / f"pdf-page-{page:03d}.txt").write_text(text, encoding="utf-8")
        stats = text_stats(text)
        page_text_stats.append({"pdf_page": page, "method": method, **stats})

    pages_to_render = list(range(1, page_count + 1)) if args.render_all else sample_pages(page_count, args.first_printed_pdf_page, args.render_samples)
    render_results: list[dict[str, object]] = []
    for page in pages_to_render:
        out_png = image_dir / f"pdf-page-{page:03d}.png"
        status = render_page(pdf, page, out_png, args.dpi)
        row: dict[str, object] = {"pdf_page": page, "status": status, "path": str(out_png) if out_png.exists() else ""}
        if args.split_spreads and out_png.exists():
            row["split_outputs"] = split_spread_image(out_png, split_dir)
        render_results.append(row)

    page_map_path = outdir / "page_map.csv"
    with page_map_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["pdf_page", "source_id", "side", "printed_page", "notes"])
        writer.writeheader()
        for pdf_page in range(1, page_count + 1):
            if args.spread_pages:
                writer.writerow({
                    "pdf_page": pdf_page,
                    "source_id": f"pdf-page-{pdf_page:03d}-left",
                    "side": "left",
                    "printed_page": printed_label(pdf_page, args.first_printed_pdf_page, args.first_printed_page_number, args.printed_prefix, True, 0),
                    "notes": "",
                })
                writer.writerow({
                    "pdf_page": pdf_page,
                    "source_id": f"pdf-page-{pdf_page:03d}-right",
                    "side": "right",
                    "printed_page": printed_label(pdf_page, args.first_printed_pdf_page, args.first_printed_page_number, args.printed_prefix, True, 1),
                    "notes": "",
                })
            else:
                writer.writerow({
                    "pdf_page": pdf_page,
                    "source_id": f"pdf-page-{pdf_page:03d}",
                    "side": "",
                    "printed_page": printed_label(pdf_page, args.first_printed_pdf_page, args.first_printed_page_number, args.printed_prefix, False),
                    "notes": "",
                })

    avg_chars = 0.0
    avg_cjk_ratio = 0.0
    if page_text_stats:
        avg_chars = sum(int(row["chars_non_ws"]) for row in page_text_stats) / len(page_text_stats)
        avg_cjk_ratio = sum(float(row["cjk_ratio"]) for row in page_text_stats) / len(page_text_stats)
    ocr_recommended = args.mode == "ocr-prep" or (args.mode == "auto" and (avg_chars < 120 or avg_cjk_ratio < 0.2))

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "command": [sys.executable, *sys.argv],
        "pdf": str(pdf),
        "outdir": str(outdir),
        "page_count": page_count,
        "mode": args.mode,
        "page_mapping": {
            "first_printed_pdf_page": args.first_printed_pdf_page,
            "first_printed_page_number": args.first_printed_page_number,
            "printed_prefix": args.printed_prefix,
            "spread_pages": args.spread_pages,
            "page_map_csv": str(page_map_path),
        },
        "tools": {
            "pdfinfo": which("pdfinfo"),
            "pdftotext": which("pdftotext"),
            "pdftoppm": which("pdftoppm"),
        },
        "text_extraction": {
            "methods": sorted(extraction_methods),
            "raw_text_dir": str(text_dir),
            "pages_extracted": len(page_text_stats),
            "average_non_ws_chars": round(avg_chars, 2),
            "average_cjk_ratio": round(avg_cjk_ratio, 4),
            "ocr_recommended": ocr_recommended,
            "page_stats": page_text_stats,
        },
        "rendering": {
            "dpi": args.dpi,
            "render_all": args.render_all,
            "image_dir": str(image_dir) if image_dir.exists() else "",
            "pages_rendered": pages_to_render,
            "results": render_results,
        },
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir / "RUN_COMMAND.txt").write_text(" ".join(json.dumps(part, ensure_ascii=False) for part in manifest["command"]) + "\n", encoding="utf-8")

    print(json.dumps({
        "manifest": str(outdir / "manifest.json"),
        "page_map": str(page_map_path),
        "page_count": page_count,
        "ocr_recommended": ocr_recommended,
        "rendered_pages": pages_to_render,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
