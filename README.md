# Textbook Quick Outline

`textbook-quick-outline` is a Codex skill for turning textbook PDFs and course PDFs into printable, page-grounded quick-reference manuals for open-book study.

It helps an agent:

- decide whether OCR is needed;
- prepare reproducible PDF source packages;
- preserve printed textbook page numbers instead of relying on PDF indexes;
- extract chapter trees, key terms, workflows, formulas, comparisons, and exercises;
- export dense Markdown handbooks to narrow-margin DOCX files.

## Contents

```text
textbook-quick-outline/
├── SKILL.md
├── agents/
│   └── openai.yaml
└── scripts/
    ├── prepare_textbook_sources.py
    └── markdown_to_narrow_docx.py
```

## Safety Defaults

The skill is designed to avoid hidden environment changes:

- OCR model weights are not downloaded silently.
- Before OCR, the agent must ask whether to download PaddleOCR, MinerU, ModelScope, Hugging Face, or other model files.
- Python packages should be installed only in temporary or project-local virtual environments.
- Do not install packages into the global/system interpreter.
- Do not use `pip install --user`.

`scripts/prepare_textbook_sources.py` does not run OCR and does not download model weights. It only prepares source files for later OCR or no-OCR processing.

## Source Preparation

Prepare a reproducible source package from a PDF:

```bash
python scripts/prepare_textbook_sources.py textbook.pdf workdir \
  --first-printed-pdf-page 16 \
  --first-printed-page-number 1 \
  --mode auto \
  --render-samples auto
```

For scanned PDFs or OCR preparation:

```bash
python scripts/prepare_textbook_sources.py textbook.pdf workdir \
  --first-printed-pdf-page 16 \
  --first-printed-page-number 1 \
  --mode ocr-prep \
  --render-all
```

For PDFs where each PDF page contains a left/right textbook spread:

```bash
python scripts/prepare_textbook_sources.py textbook.pdf workdir \
  --first-printed-pdf-page 16 \
  --first-printed-page-number 1 \
  --spread-pages \
  --mode ocr-prep \
  --render-all
```

The script writes:

- `manifest.json`: run metadata, page count, extraction stats, rendered pages, and tool paths;
- `page_map.csv`: PDF page/source ID to printed page mapping;
- `RUN_COMMAND.txt`: the command used for reproducibility;
- `page_texts_raw/`: per-page extracted text when text extraction is enabled;
- `page_images_sample/` or `page_images_all/`: rendered PNG pages for inspection or OCR.

## DOCX Export

Convert a final Markdown handbook to a printable DOCX:

```bash
python scripts/markdown_to_narrow_docx.py quick-outline.md quick-outline.docx
```

The DOCX exporter uses narrow margins and OS-aware Chinese font defaults:

- Windows: `SimSun`
- macOS: `Songti SC`
- Linux: `Noto Serif CJK SC`

Override the font when needed:

```bash
python scripts/markdown_to_narrow_docx.py quick-outline.md quick-outline.docx --font "Noto Serif CJK SC"
```

## Dependencies

For PDF source preparation:

- Python 3.10+
- Poppler tools recommended: `pdfinfo`, `pdftotext`, `pdftoppm`
- Optional fallback for page counting: `pypdf` or `PyPDF2`
- Optional spread image splitting: `Pillow`

For DOCX export:

- Python 3.10+
- `python-docx`

Install dependencies in a temporary or project-local virtual environment, not globally.

## Using As A Codex Skill

Copy or symlink this directory into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R textbook-quick-outline ~/.codex/skills/
```

Then ask Codex to use `$textbook-quick-outline` for a textbook PDF quick-reference workflow.
