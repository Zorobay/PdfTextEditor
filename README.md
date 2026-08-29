# PDF Text Editor

A small PyQt6 desktop app for reviewing and correcting OCR'd PDFs. It renders each page, overlays a bounding box per recognized word (from the PDF's existing text layer), and lets you review, delete, and eventually add/edit words directly in the PDF.

## Install

Requires Python 3.13+ and [Poetry](https://python-poetry.org/). Dependencies (PyQt6, PyMuPDF) are already declared in `pyproject.toml`.

```bash
poetry install
```

## Run

```bash
poetry run python main.py
```

## TODO

1. [ ] Add info spinner when loading pdf 