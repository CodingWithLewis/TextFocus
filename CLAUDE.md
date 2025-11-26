# CLAUDE.md

Guidance for AI agents (Claude Code, Cursor, etc.) working with this repository.

## Project Overview

Quick Cuts is a Python CLI tool that uses OCR to find specific words in images and creates new images with the word perfectly centered. Used for documentary-style video editing effects.

## Project Structure

```
quick-cuts/
├── quick_cuts/           # Main package
│   ├── __init__.py       # Package exports
│   ├── aligner.py        # Core ImageWordAligner class
│   ├── cli.py            # Command-line interface
│   └── scraper.py        # Web content aggregator (optional feature)
├── assets/               # Static assets (images, gifs for docs)
├── samples/              # Sample images for testing
├── install.sh            # One-command installer
├── pyproject.toml        # Package configuration
├── README.md             # User documentation
└── CLAUDE.md             # This file
```

## Key Commands

```bash
# Install (handles Tesseract + Python deps)
./install.sh

# Run the tool
quick-cuts images/ -w "word" --partial

# Or run directly
python -m quick_cuts.cli images/ -w "word"
```

## Architecture

### `aligner.py` - Core Processing

- `ImageWordAligner` class: Main processing engine
  - `find_word_in_image()` - Uses Tesseract OCR to locate target words
  - `create_aligned_image()` - Centers detected word, scales to consistent size
  - `get_dominant_color()` - K-means clustering for background color extraction
  - `process_images()` - Batch processing with progress callbacks

### `cli.py` - Command Line Interface

- Argument parsing with argparse
- `collect_image_paths()` - Handles files, directories, glob patterns
- Entry point: `main()`

### `scraper.py` - Web Aggregator (Optional)

- Fetches news/articles from Google News, Bing News, Hacker News
- `aggregate_content()` - Main function for fetching related content

## Technical Details

- **OCR**: pytesseract with preprocessing (bilateral filter, OTSU thresholding)
- **Confidence threshold**: 30 (configurable in code)
- **Image formats**: jpg, jpeg, png, bmp, tiff, webp
- **Unicode paths**: Handled via `cv2.imdecode()` + `numpy.fromfile()`
- **Background options**: white, black, dominant (K-means), transparent (PNG)

## Dependencies

Core:
- opencv-python (image processing)
- pytesseract (OCR interface)
- numpy (array operations)
- scikit-learn (K-means for dominant color)

Optional (for scraper):
- requests, feedparser

System:
- Tesseract OCR must be installed (`brew install tesseract` or `apt install tesseract-ocr`)

## Common Tasks

### Adding a new CLI option

Edit `cli.py`:
1. Add argument to `parser.add_argument()`
2. Pass to `ImageWordAligner` constructor
3. Handle in `aligner.py` if needed

### Modifying OCR behavior

Edit `aligner.py`:
- `find_word_in_image()` for detection logic
- Confidence threshold is hardcoded as `30`
- Preprocessing pipeline: grayscale → bilateral filter → OTSU threshold

### Testing changes

```bash
quick-cuts samples/ -w "cookie" --partial -o test_output
```
