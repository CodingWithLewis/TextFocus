# Quick Cuts Examples

## Basic Examples

### 1. Simple Word Alignment
Align all PNG images with the word "breaking":
```bash
python quick_cuts.py images/*.png -w "breaking"
```

### 2. Process Entire Directory
Process all images in a folder:
```bash
python quick_cuts.py images/ -w "news"
```

### 3. Partial Word Matching
Match words that start with "warp" (like "warpdotdev"):
```bash
python quick_cuts.py images/ -w "warp" --partial
```

## Advanced Examples

### 4. Custom Output Size for 4K
Create 4K resolution outputs:
```bash
python quick_cuts.py images/ -w "alert" -s 3840x2160 --word-height 200
```

### 5. Specific Output Directory
Save to a custom location:
```bash
python quick_cuts.py images/ -w "update" -o "C:\Users\lewis\aligned_outputs"
```

### 6. Performance Optimization
Use 16 workers for faster processing:
```bash
python quick_cuts.py images/ -w "flash" --workers 16
```

### 7. Small Word Size
For subtle word placement:
```bash
python quick_cuts.py images/ -w "live" --word-height 50
```

## Workflow Examples

### News Ticker Style
```bash
# Process multiple news screenshots
python quick_cuts.py "news_screenshots/*.png" -w "breaking" -s 1920x1080 --word-height 120
```

### Social Media Clips
```bash
# Process vertical format for social media
python quick_cuts.py tiktok_frames/ -w "viral" -s 1080x1920 --word-height 150
```

### Multi-Word Processing
```bash
# Process same images for different words
python quick_cuts.py images/ -w "breaking"
python quick_cuts.py images/ -w "news"
python quick_cuts.py images/ -w "alert"
# Results in: aligned_breaking/, aligned_news/, aligned_alert/
```

## Troubleshooting Examples

### Debug OCR Issues
If words aren't being detected, try:
```bash
# Use partial matching for better detection
python quick_cuts.py problem_image.png -w "text" --partial

# Process with fewer workers to see detailed logs
python quick_cuts.py images/ -w "word" --workers 1
```

### Handle Special Characters
For filenames with unicode characters:
```bash
# The tool handles these automatically
python quick_cuts.py "Screenshot*.png" -w "update"
```