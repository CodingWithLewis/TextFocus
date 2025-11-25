# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Quick Cuts is a Python tool that automatically aligns and centers specific words in images using OCR (Optical Character Recognition). It's designed for creating documentary-style video effects where words need to be consistently positioned across multiple frames.

## Key Commands

### Running the Tool
```bash
# Basic usage - align word in images
python quick_cuts.py images/*.png -w "word"

# Process entire directory with partial matching
python quick_cuts.py images/ -w "word" --partial

# Custom output size and word height
python quick_cuts.py images/ -w "word" -s 1920x1080 --word-height 100
```

### Installation
```bash
# Install dependencies (requires Python 3.8+ and Tesseract OCR)
pip install -r requirements.txt
# or with uv:
uv pip install -r requirements.txt
```

## Architecture

The codebase consists of a single main module `quick_cuts.py` with the following structure:

- **ImageWordAligner class**: Core processing logic
  - `find_word_in_image()`: Uses Tesseract OCR to locate target words with bounding boxes
  - `create_aligned_image()`: Centers detected words and scales them to consistent size
  - `get_dominant_color()`: Extracts dominant color using K-means clustering for background
  - `process_images()`: Parallel processing coordinator using multiprocessing Pool

- **Processing Pipeline**:
  1. OCR detection with preprocessing (bilateral filter, OTSU thresholding)
  2. Word matching (exact or partial via `--partial` flag)
  3. Image transformation (scaling and centering)
  4. Background handling (white, black, transparent, or dominant color)
  5. Parallel batch processing for performance

## Important Technical Details

- **OCR Configuration**: Uses pytesseract with confidence threshold of 30
- **Image Formats**: Supports jpg, jpeg, png, bmp, tiff
- **Unicode Handling**: Special handling for Unicode filenames using `cv2.imdecode()` and `numpy.fromfile()`
- **Parallel Processing**: Uses multiprocessing.Pool with configurable worker count
- **Background Options**: dominant (K-means), white, black, or transparent (outputs as PNG)
- **Partial Matching**: When enabled, matches beginning of words and estimates target word width proportionally

## Dependencies

- opencv-python >= 4.8.0 (image processing)
- pytesseract >= 0.3.10 (OCR interface)
- numpy >= 1.26.0 (array operations)
- Pillow >= 10.0.0 (image handling)
- scikit-learn >= 1.3.0 (K-means clustering for dominant color)

## External Requirements

Tesseract OCR must be installed separately on the system before using this tool.