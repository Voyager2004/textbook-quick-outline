---
name: textbook-quick-outline
description: Generate printable quick-reference manuals, outline trees, page-grounded study guides, or exam lookup handbooks from textbook PDFs or course PDFs. Use when Codex needs to decide whether OCR is needed, parse scanned or text PDFs, preserve printed page numbers, extract chapter structure/key terms/exercises, and produce Markdown or DOCX quick-reference artifacts for open-book study.
---

# Textbook Quick Outline

## Core Rule

Always make the handbook page-grounded. The page numbers in the quick reference must point to the textbook's printed pages, not blindly to PDF page indexes or OCR file numbers.

Before running OCR, ask the user whether to download OCR model weights such as PaddleOCR, MinerU, ModelScope, Hugging Face, or other model files. Name the intended model, expected cache/download location, approximate size if known, and whether a local cached copy already exists. Do not download weights silently.

Use isolated temporary or project-local environments for all dependencies. Do not install Python packages into the global/system interpreter, do not use `pip install --user`, and do not modify global package state. Prefer an existing project venv, a temporary venv under the task work directory, or a `/tmp` venv. If an OCR tool would write model caches to a default home directory, redirect the cache to a task-local directory when supported; otherwise ask the user before proceeding.

## Workflow

1. Confirm inputs and output.
   - Identify the textbook PDF, optional PPT/courseware folders, reference style DOCX, and desired output format.
   - If the user did not specify OCR, choose the path after inspecting the PDF. Ask only if the tradeoff matters, such as slower OCR vs faster text extraction.
   - Before any OCR run that may fetch weights, get explicit user approval for the model download and cache location.
   - Before installing packages, create or reuse an isolated venv; never install into global Python.
   - If output is DOCX, use the `documents` skill and render the final DOCX before delivery.

2. Inspect the PDF before parsing.
   - Prefer running `scripts/prepare_textbook_sources.py` first to create a reproducible source package with `manifest.json`, `page_map.csv`, and extracted text or OCR-ready page images.
   - Check whether text extraction works with `pdftotext -layout`, `pdfplumber`, or another structured extractor.
   - Render several representative pages to images, including front matter, a chapter start, a dense text page, and a chapter end.
   - Determine whether each PDF page contains one printed page or a combined spread/two pages. If spreads are present, split/crop before OCR or maintain an explicit mapping.
   - Establish page mapping, for example: `page-016 => printed P1`. Record the rule in generated notes.

3. Decide OCR vs no OCR.
   - Skip OCR when extracted text is complete enough, has stable headings, and Chinese text quality is good.
   - Use OCR when the PDF is scanned, photographed, has garbled text, missing Chinese characters, or unreliable layout.
   - For Chinese scanned textbooks, prefer a high-accuracy OCR path such as PaddleOCR PP-OCRv5 server models; use MinerU when layout recovery, formulas, or structured Markdown are more important.
   - If OCR requires PaddleOCR, MinerU, ModelScope, Hugging Face, or other weights not already present, pause and ask the user whether to download them. Include the planned model/cache path in the question.
   - For a long book, run a small sample first. Compare OCR output against rendered page images before committing to the full run.

4. Build durable page text.
   - Store one text file per printed page or per calibrated OCR page.
   - Preserve both IDs when useful: source image/page ID and printed page number.
   - Keep a corrected text layer if manual fixes are made; never overwrite raw OCR without keeping provenance.
   - Mark uncertain OCR regions for later review instead of silently inventing text.

5. Extract the handbook content.
   - Build the chapter tree from the table of contents and actual chapter headings.
   - For every section, include compact exam-useful summaries, key terms, formulas, classifications, workflows, comparisons, and tool names.
   - Include chapter-end exercises if the textbook has them. Check the end of every chapter for headings such as `习题`, `课后题`, `思考题`, `复习题`, or `练习题`.
   - If PPT/courseware is provided, separately check whether it contains exercises or only summaries/THANK YOU slides.

6. Generate the quick-reference structure.
   - Default to one dense tree-style section rather than multiple prose sections.
   - Integrate high-frequency Q&A and key-term indexes into each chapter tree.
   - Bold key terms when output supports it.
   - Avoid tables unless the user specifically asks; tables are usually less printable for this use case.
   - Use concise wording, but do not omit process/classification/step lists that are likely exam answers.

7. Validate content against sources.
   - Verify every chapter in the table of contents appears in the handbook.
   - Spot-check page anchors against rendered page images, not just OCR text.
   - Check high-risk items: workflows, classification lists, formula pages, protocol steps, and terms with similar names.
   - Search the final Markdown/DOCX text for newly added key terms to confirm they landed.
   - If the user supplies an audit list, verify each issue against current source files before applying it.

8. Produce DOCX when requested.
   - If no project-specific generator exists, use `scripts/markdown_to_narrow_docx.py` to convert the final Markdown handbook into a narrow-margin DOCX.
   - Use narrow margins for print-heavy open-book references.
   - Use a Chinese print font suited to the current OS: Windows `SimSun`, macOS `Songti SC`, Linux `Noto Serif CJK SC`. Override with `--font` if the default font is unavailable.
   - Keep fonts readable even when dense; prefer a stable monospace/tree style for the outline.
   - Include a short page-number note near the title.
   - Render the DOCX to PNG pages and inspect every page for clipping, overlap, missing glyphs, and bad page breaks before final delivery.

## Bundled Scripts

- `scripts/prepare_textbook_sources.py`: build a reproducible source package from a PDF. It records the command, probes page count/text quality, creates `page_map.csv`, extracts per-page text when possible, and can render sample/all pages for OCR. Use `--spread-pages` when one PDF page contains two printed pages.
- `scripts/markdown_to_narrow_docx.py`: convert a final Markdown quick-reference handbook to a printable DOCX with narrow margins, OS-aware Chinese font defaults, headings, bullets, and `**bold key terms**`.

Example source preparation:

```bash
python /path/to/textbook-quick-outline/scripts/prepare_textbook_sources.py textbook.pdf workdir \
  --first-printed-pdf-page 16 --first-printed-page-number 1 --mode auto --render-samples auto
```

Example for scanned two-page spreads:

```bash
python /path/to/textbook-quick-outline/scripts/prepare_textbook_sources.py textbook.pdf workdir \
  --first-printed-pdf-page 16 --first-printed-page-number 1 --spread-pages --mode ocr-prep --render-all
```

Example DOCX export:

```bash
python /path/to/textbook-quick-outline/scripts/markdown_to_narrow_docx.py quick-outline.md quick-outline.docx
```

## OCR Decision Checklist

Use no-OCR extraction when:
- `pdftotext -layout` or `pdfplumber` returns clean Chinese text.
- Headings and page numbers are stable.
- Page images are born-digital or already searchable.

Use OCR when:
- The PDF is photographed/scanned.
- Chinese characters are wrong, missing, or mojibake.
- The PDF has two printed pages combined in one image.
- Layout or formulas are visible only in images.

For OCR:
- Render at sufficient DPI, usually 300-400 for text-heavy Chinese scans.
- Split spreads before OCR when a PDF page contains two book pages.
- Run a sample and compare against page images.
- Use a temporary or project-local venv for OCR packages. Never install OCR packages globally.
- Keep model weights in a task-local cache when the OCR tool allows it, such as a cache directory inside the source package or work directory.
- Prefer deterministic file names such as `page_texts_raw/page-016.txt` and `page_texts_corrected/page-016.txt`.

## Quality Gates

Before final delivery, report:
- The reproducibility source directory and manifest path.
- The page mapping rule.
- Whether OCR was used and why.
- The number of chapters/TOC entries covered.
- Whether chapter-end exercises were present.
- The output files created.
- For DOCX, whether render QA passed.

Do not present a handbook as final if page numbers are unverified or if OCR accuracy is known to be weak.
