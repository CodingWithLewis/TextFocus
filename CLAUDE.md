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
│   ├── interactive.py    # Interactive menu mode
│   ├── scraper.py        # Web scraper + image downloader
│   └── video.py          # Video creation from images
├── input/                # Downloaded images (from fetch command)
├── output/               # Aligned images (from align command)
├── copyright_attributions/  # Source URLs for downloaded images
├── samples/              # Sample images for testing
├── assets/               # Static assets (images, gifs for docs)
├── install.sh            # One-command installer
├── pyproject.toml        # Package configuration
├── README.md             # User documentation
└── CLAUDE.md             # This file
```

## Key Commands

```bash
# Install (handles Tesseract + Python deps + PATH)
source ./install.sh

# Launch interactive mode
quick-cuts            # or: qc

# Direct commands
quick-cuts fetch "keyword" -n 10      # Download images to input/
quick-cuts align input/ -w "word"     # Align images to output/
quick-cuts video -d 100               # Create video from output/
quick-cuts clear input                # Clear folder (input/output/attributions)
quick-cuts scrape "topic" -n 10       # Search news articles
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
- Entry point: `main()` - launches interactive mode by default

### `interactive.py` - Interactive Menu

- Menu-driven interface for guided workflow
- `fetch_images_interactive()` - Prompts for search term and count
- `align_images_interactive()` - Prompts for word, settings, runs alignment
- `create_video_interactive()` - Creates video from output images
- Automatically uses input/ and output/ folders

### `video.py` - Video Creation

- `create_video(input_dir, output_file, delay_ms)` - Creates MP4 from images
- Uses OpenCV for video encoding
- Returns dict with success, path, frames, fps, duration_sec

### `scraper.py` - Web Aggregator

- Fetches news/articles from Google News RSS, Bing News RSS, Hacker News API
- `aggregate_content(query, limit, sources, logger)` - Main function
- Sources: `news` (Google + Bing), `hn` (Hacker News)
- Returns list of `{source, title, url, snippet, published_at}` dicts

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
# Test alignment
quick-cuts align samples/ -w "cookie" --partial -o test_output

# Test scraper
quick-cuts scrape "test query" -n 3
```
