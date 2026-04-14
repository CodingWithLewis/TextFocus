---
name: textfocus
description: Align and center a specific word across multiple images using OCR (Tesseract) to produce documentary-style "word focus" cuts. Use when the user wants to center/lock a keyword across screenshots or video frames, create news-ticker style alignment, produce same-word cuts for After Effects / Premiere, or batch-crop frames so a chosen word stays perfectly centered and same-size. Wraps the `quick_cuts.py` CLI in this repo.
---

# TextFocus (Quick Cuts) Skill

A Python-based OCR alignment tool that finds a target word in each input image and produces an output image where that word is centered and scaled to a consistent size. Designed for creating documentary / news-style video cuts where the same word stays locked in place across different footage.

## When to use this skill

Activate when the user asks to:
- "Center the word X across these images/frames"
- "Align all these screenshots on the word Y"
- "Make a Warp-style / documentary cut where a word stays fixed"
- Batch-process video frames so a keyword is locked to the center
- Normalize word size and position across many images

If the user only wants generic image cropping (no OCR / no target word), this skill is not the right fit.

## Prerequisites

Before running anything, verify the environment:

1. **Tesseract OCR must be installed on the system** (not just the Python package):
   - macOS: `brew install tesseract`
   - Linux: `sudo apt-get install tesseract-ocr`
   - Windows: installer from https://github.com/UB-Mannheim/tesseract/wiki
   - Check with: `tesseract --version`
2. **Python 3.8+**
3. **Python dependencies** (from `requirements.txt`):
   ```bash
   pip install -r requirements.txt
   # or
   uv pip install -r requirements.txt
   ```

If Tesseract is missing, tell the user to install it — do not try to work around it.

## Primary tool: `quick_cuts.py`

```bash
python quick_cuts.py <images> -w "<target_word>" [options]
```

`<images>` can be a glob (`images/*.png`), a directory (`images/`), or individual files.

### Common options

| Flag | Purpose | Default |
|---|---|---|
| `-w, --word` | Target word to center (required) | — |
| `-o, --output` | Output directory | `./aligned_<word>` |
| `-s, --size` | Output canvas `WxH` | `1920x1080` |
| `--word-height` | Target word height in px | `100` |
| `--background` | `white` \| `black` \| `transparent` \| `dominant` | `dominant` |
| `--partial` | Match words starting with the target (e.g. `warp` → `warpdotdev`) | off |
| `--workers` | Parallel worker count | CPU count |

### Typical invocations

```bash
# Basic — center "breaking" across PNGs
python quick_cuts.py images/*.png -w "breaking"

# Partial match — useful when the target is a prefix of a longer word
python quick_cuts.py images/ -w "warp" --partial

# 4K output with larger word
python quick_cuts.py images/ -w "alert" -s 3840x2160 --word-height 200

# Vertical / social-media format, transparent background
python quick_cuts.py frames/ -w "viral" -s 1080x1920 --background transparent
```

Transparent background forces `.png` output regardless of input format.

## Working guidance for Claude

When the user asks for a word-alignment task:

1. **Confirm the target word and the input path** before running — mistakes here waste a batch.
2. **Check image formats** — supported: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`.
3. **Run once on a small sample first** (1–3 images) to verify OCR actually finds the word, before processing a full folder.
4. **If OCR misses**, suggest in order: `--partial`, higher-resolution source images, better contrast. Do not silently change the target word.
5. **Output files** are named `aligned_<original>` in the output dir. Tell the user where they landed (`output_dir.absolute()` is logged).
6. **Progress / failures** are printed to stdout. Surface the "Failed to find word in:" list back to the user so they know which frames need manual attention.

## Secondary capability: content scraping

`backend_service.py` exposes a `scrape_content` JSON-IPC command (Google News RSS, Bing News RSS, Hacker News) for pulling articles related to a keyword. This is auxiliary — only use it if the user explicitly asks to fetch related articles, not as part of the image pipeline. See `README.md` for the JSON protocol.

## Files in this skill

- `quick_cuts.py` — main CLI (use this)
- `requirements.txt` — Python deps
- `README.md` — full user-facing docs
- `examples.md` — worked examples
- `backend_service.py`, `quick_cuts_backend.py` — Electron-app IPC backend (not for CLI use)
- `docs/example.gif`, `docs/example.mp4` — visual reference of the effect
