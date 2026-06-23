# Textbook Quick Outline

`textbook-quick-outline` 是一个 Codex Skill，用于把教材 PDF、课程 PDF 或扫描版教材整理成适合打印的“开卷考试快查手册”。

它的目标不是简单 OCR 或全文摘录，而是帮助 Codex 稳定复现一套教材整理流程：

- 判断 PDF 是否需要 OCR；
- 生成可复现的 PDF 源材料包；
- 按教材实际印刷页码建立索引，而不是直接使用 PDF 页码；
- 抽取章节目录树、重点名词、流程步骤、分类对比、公式、协议过程和课后题；
- 将最终 Markdown 快查手册导出为窄页边距 DOCX，方便打印和开卷考试翻查。

## 文件结构

```text
textbook-quick-outline/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── examples/
│   └── 网络安全教材开卷快查手册.pdf
└── scripts/
    ├── prepare_textbook_sources.py
    └── markdown_to_narrow_docx.py
```

## 效果展示

- [网络安全教材开卷快查手册.pdf](examples/%E7%BD%91%E7%BB%9C%E5%AE%89%E5%85%A8%E6%95%99%E6%9D%90%E5%BC%80%E5%8D%B7%E5%BF%AB%E6%9F%A5%E6%89%8B%E5%86%8C.pdf)：一份面向开卷考试的教材快查手册示例。

## 安全约束

这个 Skill 默认避免隐藏下载和污染全局环境：

- 不会静默下载 OCR 模型权重。
- OCR 前必须询问用户是否下载 PaddleOCR、MinerU、ModelScope、Hugging Face 或其他模型文件。
- Python 依赖只能安装到临时环境或项目局部虚拟环境。
- 不要把依赖安装到全局/system Python。
- 不要使用 `pip install --user`。

`scripts/prepare_textbook_sources.py` 本身不执行 OCR，也不会下载模型权重。它只负责准备后续 OCR 或非 OCR 处理所需的稳定输入。

## 准备教材源材料

从教材 PDF 生成可复现的源材料包：

```bash
python scripts/prepare_textbook_sources.py textbook.pdf workdir \
  --first-printed-pdf-page 16 \
  --first-printed-page-number 1 \
  --mode auto \
  --render-samples auto
```

扫描版教材或准备 OCR 时：

```bash
python scripts/prepare_textbook_sources.py textbook.pdf workdir \
  --first-printed-pdf-page 16 \
  --first-printed-page-number 1 \
  --mode ocr-prep \
  --render-all
```

如果一个 PDF 页面包含左右两页教材：

```bash
python scripts/prepare_textbook_sources.py textbook.pdf workdir \
  --first-printed-pdf-page 16 \
  --first-printed-page-number 1 \
  --spread-pages \
  --mode ocr-prep \
  --render-all
```

脚本会生成：

- `manifest.json`：运行元数据、页数、抽取统计、渲染页、工具路径等；
- `page_map.csv`：PDF 页面/source ID 与教材印刷页码的映射；
- `RUN_COMMAND.txt`：本次运行命令，便于复现；
- `page_texts_raw/`：逐页抽取文本；
- `page_images_sample/` 或 `page_images_all/`：用于检查或 OCR 的页面图片。

## 导出 DOCX

将最终 Markdown 快查手册导出为可打印 DOCX：

```bash
python scripts/markdown_to_narrow_docx.py quick-outline.md quick-outline.docx
```

DOCX 导出脚本使用窄页边距，并按操作系统选择中文字体默认值：

- Windows：`SimSun`
- macOS：`Songti SC`
- Linux：`Noto Serif CJK SC`

如果默认字体不可用，可以手动指定：

```bash
python scripts/markdown_to_narrow_docx.py quick-outline.md quick-outline.docx --font "Noto Serif CJK SC"
```

## 依赖

PDF 源材料准备：

- Python 3.10+
- 推荐安装 Poppler 工具：`pdfinfo`、`pdftotext`、`pdftoppm`
- 可选页数兜底：`pypdf` 或 `PyPDF2`
- 可选双页图片切分：`Pillow`

DOCX 导出：

- Python 3.10+
- `python-docx`

请把依赖安装在临时环境或项目局部虚拟环境中，不要安装到全局 Python。

## 作为 Codex Skill 使用

将本目录复制或软链接到 Codex skills 目录：

```bash
mkdir -p ~/.codex/skills
cp -R textbook-quick-outline ~/.codex/skills/
```

之后可以让 Codex 使用 `$textbook-quick-outline`，针对某本教材 PDF 生成开卷考试快查手册。
