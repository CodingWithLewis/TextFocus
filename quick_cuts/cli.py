"""
Command-line interface for Quick Cuts.
"""

import argparse
from pathlib import Path
import logging
import sys
from multiprocessing import cpu_count
import glob

from .aligner import ImageWordAligner

logging.basicConfig(
    level=logging.INFO, 
    stream=sys.stdout, 
    format='%(levelname)s: %(message)s',
    force=True
)
logger = logging.getLogger(__name__)


def collect_image_paths(inputs):
    """Collect all image paths from input arguments."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    image_paths = []
    
    for input_path in inputs:
        path = Path(input_path)
        
        if path.is_dir():
            for ext in image_extensions:
                image_paths.extend(path.glob(f'*{ext}'))
                image_paths.extend(path.glob(f'*{ext.upper()}'))
        elif path.is_file():
            if path.suffix.lower() in image_extensions:
                image_paths.append(path)
        else:
            matched = glob.glob(input_path)
            for m in matched:
                mp = Path(m)
                if mp.is_file() and mp.suffix.lower() in image_extensions:
                    image_paths.append(mp)
    
    return list(set(str(p) for p in image_paths))


def main():
    """Main entry point for the quick-cuts CLI."""
    parser = argparse.ArgumentParser(
        prog='quick-cuts',
        description='Align and center words in images using OCR'
    )
    parser.add_argument('images', nargs='+', help='Input image file(s) or directory')
    parser.add_argument('-w', '--word', required=True, help='Target word to center')
    parser.add_argument('-o', '--output', default='./aligned_{word}', help='Output directory')
    parser.add_argument('-s', '--size', default='1920x1080', help='Output size (WIDTHxHEIGHT)')
    parser.add_argument('--word-height', type=int, default=100, help='Target word height in pixels')
    parser.add_argument('--partial', action='store_true', help='Enable partial word matching')
    parser.add_argument('--background', choices=['white', 'black', 'dominant'], default='white', help='Background color')
    
    args = parser.parse_args()
    
    # Parse size
    try:
        width, height = map(int, args.size.split('x'))
        output_size = (width, height)
    except ValueError:
        logger.error("Invalid size format. Use WIDTHxHEIGHT (e.g., 1920x1080)")
        sys.exit(1)
    
    # Collect images
    image_paths = collect_image_paths(args.images)
    
    if not image_paths:
        logger.error("No valid images found")
        sys.exit(1)
    
    logger.info(f"Found {len(image_paths)} images")
    
    # Create output directory
    output_dir = Path(args.output.format(word=args.word))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process
    aligner = ImageWordAligner(
        target_word=args.word,
        output_size=output_size,
        word_height=args.word_height,
        exact_match=not args.partial,
        background=args.background
    )
    
    try:
        results = aligner.process_images(image_paths, output_dir)
        
        successful = sum(1 for success, _, _ in results if success)
        failed = len(results) - successful
        
        print(f"\n✓ Done! {successful} aligned, {failed} failed")
        print(f"  Output: {output_dir}")
        
    except KeyboardInterrupt:
        logger.info("Cancelled")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
