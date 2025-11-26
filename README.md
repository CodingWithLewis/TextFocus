# Quick Cuts

Automatically center specific words in images using OCR. Perfect for creating that "busy" documentary-style video effect.

![Example](assets/example.gif)

## Quick Start

```bash
git clone https://github.com/yourusername/quick-cuts.git
cd quick-cuts
./install.sh
```

That's it! The install script handles Tesseract OCR and Python dependencies automatically.

## Usage

```bash
# Basic - find and center a word
quick-cuts images/ -w "breaking"

# Partial matching - "cookie" matches "cookies", "Cookiebot", etc.
quick-cuts images/ -w "cookie" --partial

# Custom output size and background
quick-cuts images/ -w "news" -s 1920x1080 --background dominant
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-w, --word` | Word to find and center | Required |
| `-o, --output` | Output directory | `./aligned_{word}` |
| `-s, --size` | Output dimensions | `1920x1080` |
| `--word-height` | Target word height (px) | `100` |
| `--partial` | Match word prefixes | `false` |
| `--background` | `white`, `black`, or `dominant` | `white` |

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
├── quick_cuts/       # Python package
├── assets/           # Images and gifs for documentation
├── samples/          # Sample images to test with
├── install.sh        # One-command installer
└── pyproject.toml    # Package config
```

## Requirements

- Python 3.8+
- Tesseract OCR (installed automatically by `./install.sh`)

## License

MIT
