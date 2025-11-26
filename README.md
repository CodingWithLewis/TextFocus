# Quick Cuts

Automatically center specific words in images using OCR. Perfect for creating that "busy" documentary-style video effect.

![Example](assets/example.gif)

## Quick Start

```bash
git clone https://github.com/yourusername/quick-cuts.git
cd quick-cuts
source ./install.sh
```

That's it! The install script handles Tesseract OCR, Python dependencies, and PATH setup automatically.

## Usage

### Interactive Mode

Launch the interactive CLI for a guided experience:

```bash
quick-cuts
```

```
==================================================
  QUICK CUTS - Word Alignment Tool
==================================================

  Input folder:  0 images
  Output folder: 0 images

  [1] Fetch images from web
  [2] Align images
  [3] Agent mode (auto-collect)
  [4] Create video from output
  [5] Clear input folder
  [6] Clear output folder
  [7] Clear attributions
  [8] Exit
```

### Command Line

#### Align Images

```bash
# Basic - find and center a word
quick-cuts align images/ -w "breaking"

# Partial matching - "cookie" matches "cookies", "Cookiebot", etc.
quick-cuts align images/ -w "cookie" --partial

# Custom output size and background
quick-cuts align images/ -w "news" -s 1920x1080 --background dominant
```

| Option | Description | Default |
|--------|-------------|---------|
| `-w, --word` | Word to find and center | Required |
| `-o, --output` | Output directory | `./aligned_{word}` |
| `-s, --size` | Output dimensions | `1920x1080` |
| `--word-height` | Target word height (px) | `100` |
| `--partial` | Match word prefixes | `false` |
| `--background` | `white`, `black`, or `dominant` | `white` |

#### Fetch Images

```bash
quick-cuts fetch "cookie banner" -n 10
quick-cuts fetch "breaking news" -n 5 -o my_images/
```

#### Scrape News

```bash
quick-cuts scrape "breaking news" -n 5
```

## How It Works

1. **OCR** - Tesseract scans each image for text
2. **Match** - Finds your target word with bounding box
3. **Align** - Creates new image with word perfectly centered
4. **Scale** - Maintains consistent word size across all outputs

## Use Case

Create smooth documentary-style cuts where a keyword stays centered:

1. Export frames from different video clips
2. Run `quick-cuts` to align all frames on your keyword
3. Import aligned images into Premiere/After Effects
4. Cut between clips with the word always in the same position

## Project Structure

```
quick-cuts/
├── quick_cuts/              # Python package
├── input/                   # Downloaded images (from fetch command)
├── output/                  # Aligned images (from align command)
├── copyright_attributions/  # Source URLs for downloaded images
├── samples/                 # Sample images to test with
├── install.sh               # One-command installer
└── pyproject.toml           # Package config
```

## Requirements

- Python 3.8+
- Tesseract OCR (installed automatically by `./install.sh`)

## License

MIT
