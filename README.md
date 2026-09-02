# PDF Text Editor

A small PyQt6 desktop app for reviewing and correcting OCR'd PDFs. It renders each page, overlays a bounding box per recognized word (from the PDF's existing text layer), and lets you review, delete, and eventually add/edit words directly in the PDF.

## Install

Requires Python 3.13+ and [Poetry](https://python-poetry.org/). Dependencies (PyQt6, PyMuPDF) are already declared in `pyproject.toml`.

```bash
poetry install
```

### OCR Support

When drawing text boxes, *PDF Text Editor* can run OCR (_Optical Character Recognition_) to automatically guess the text inside the box. 
For this to work, Tesseract OCR is required. If not installed, the OCR will silently fail.
Install instructions below:

#### Linux

```bash
sudo apt install tesseract-ocr
```

#### Windows

1. Go to the UB-Mannheim Tesseract builds page (this is the de facto standard Windows installer, maintained separately from the main Tesseract repo since Tesseract itself doesn't publish official Windows binaries): https://github.com/UB-Mannheim/tesseract/wiki
2. Download the latest tesseract-ocr-w64-setup-*.exe
3. Run it. Note the install path — default is usually `C:\Program Files\Tesseract-OCR`
   1. Make sure you check "Add to PATH"
   2. During install, there's a component list — make sure "Additional language data" is checked if you need anything beyond English (you're doing language="eng" currently, so default English is fine as-is)
4. Test that Tesseract was successfully added to PATH by running `tesseract --version` in a terminal.


## Run

```bash
poetry run python main.py
```

## TODO

1. [ ] Add info spinner when loading pdf 
2. [ ] Fix sync of current page for status bar