"""
Command-line interface for Quick Cuts.
"""

import argparse
from pathlib import Path
import logging
import sys
import glob
import json

from .aligner import ImageWordAligner
from .scraper import aggregate_content, fetch_images
from .video import create_video

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


def cmd_align(args):
    """Handle the align command."""
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


def cmd_scrape(args):
    """Handle the scrape command."""
    query = args.query
    limit = args.limit
    
    # Parse sources
    sources = None
    if args.sources:
        sources = [s.strip() for s in args.sources.split(',')]
    
    logger.info(f"Searching for: {query}")
    
    try:
        results = aggregate_content(query, limit=limit, sources=sources, logger=logger)
        
        if not results:
            print("No results found.")
            return
        
        print(f"\nFound {len(results)} articles:\n")
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for i, item in enumerate(results, 1):
                source = item.get('source', 'unknown')
                title = item.get('title', 'No title')
                url = item.get('url', '')
                published = item.get('published_at', '')
                
                print(f"{i}. [{source}] {title}")
                if published:
                    print(f"   Published: {published[:10]}")
                print(f"   {url}")
                print()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


def cmd_fetch(args):
    """Handle the fetch command - download images."""
    query = args.query
    limit = args.limit
    output_dir = args.output
    
    print(f"Fetching {limit} images for '{query}'...")
    
    try:
        saved_files = fetch_images(query, limit=limit, output_dir=output_dir)
        
        if not saved_files:
            print("No images found or downloaded.")
            sys.exit(1)
        
        print(f"Downloaded {len(saved_files)} images to {output_dir}/")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


def cmd_clear(args):
    """Clear input, output, or attributions folder."""
    import shutil
    
    folder = args.folder
    
    if folder == 'attributions':
        folder_path = Path('copyright_attributions')
        if not folder_path.exists():
            print("No copyright attributions folder.")
            return
        shutil.rmtree(folder_path)
        print("Cleared copyright_attributions/")
        return
    
    folder_path = Path(folder)
    
    if not folder_path.exists():
        print(f"Folder '{folder}' does not exist.")
        return
    
    extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff'}
    count = 0
    
    for f in folder_path.iterdir():
        if f.is_file() and f.suffix.lower() in extensions:
            f.unlink()
            count += 1
    
    print(f"Cleared {count} images from {folder}/")


def cmd_video(args):
    """Create video from images."""
    result = create_video(
        input_dir=args.input,
        output_file=args.output,
        delay_ms=args.delay
    )
    
    if result['success']:
        print(f"Video created: {result['path']}")
        print(f"Frames: {result['frames']}, FPS: {result['fps']:.1f}, Duration: {result['duration_sec']:.1f}s")
    else:
        print(f"Error: {result['error']}")
        sys.exit(1)


def main():
    """Main entry point for the quick-cuts CLI."""
    parser = argparse.ArgumentParser(
        prog='quick-cuts',
        description='OCR-based image alignment and content research tools'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Align command
    align_parser = subparsers.add_parser('align', help='Align and center words in images')
    align_parser.add_argument('images', nargs='+', help='Input image file(s) or directory')
    align_parser.add_argument('-w', '--word', required=True, help='Target word to center')
    align_parser.add_argument('-o', '--output', default='./aligned_{word}', help='Output directory')
    align_parser.add_argument('-s', '--size', default='1920x1080', help='Output size (WIDTHxHEIGHT)')
    align_parser.add_argument('--word-height', type=int, default=100, help='Target word height in pixels')
    align_parser.add_argument('--partial', action='store_true', help='Enable partial word matching')
    align_parser.add_argument('--background', choices=['white', 'black', 'dominant'], default='white', help='Background color')
    
    # Fetch command (download images)
    fetch_parser = subparsers.add_parser('fetch', help='Download images related to a search term')
    fetch_parser.add_argument('query', help='Search term for images')
    fetch_parser.add_argument('-n', '--limit', type=int, default=10, help='Number of images to download (default: 10)')
    fetch_parser.add_argument('-o', '--output', default='input', help='Output directory (default: input/)')
    
    # Scrape command (news articles)
    scrape_parser = subparsers.add_parser('scrape', help='Search for news/articles on a topic')
    scrape_parser.add_argument('query', help='Search query')
    scrape_parser.add_argument('-n', '--limit', type=int, default=10, help='Max results per source (default: 10)')
    scrape_parser.add_argument('--sources', help='Comma-separated sources: news,hn (default: all)')
    scrape_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # Clear command
    clear_parser = subparsers.add_parser('clear', help='Clear images from a folder')
    clear_parser.add_argument('folder', choices=['input', 'output', 'attributions'], help='Folder to clear')
    
    # Video command
    video_parser = subparsers.add_parser('video', help='Create video from images')
    video_parser.add_argument('-i', '--input', default='output', help='Input directory (default: output/)')
    video_parser.add_argument('-o', '--output', default='output.mp4', help='Output filename (default: output.mp4)')
    video_parser.add_argument('-d', '--delay', type=int, default=100, help='Delay between frames in ms (default: 100)')
    
    args = parser.parse_args()
    
    if args.command == 'align':
        cmd_align(args)
    elif args.command == 'fetch':
        cmd_fetch(args)
    elif args.command == 'scrape':
        cmd_scrape(args)
    elif args.command == 'clear':
        cmd_clear(args)
    elif args.command == 'video':
        cmd_video(args)
    else:
        # No command given - launch interactive mode
        from .interactive import main as interactive_main
        interactive_main()


if __name__ == "__main__":
    main()
