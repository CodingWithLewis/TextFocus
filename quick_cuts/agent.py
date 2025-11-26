"""
Agent mode - Automated workflow to collect a target number of aligned images.
"""

import os
import shutil
from pathlib import Path
from typing import Callable, Optional

from .aligner import ImageWordAligner
from .scraper import fetch_images


def get_image_count(directory: str) -> int:
    """Count images in a directory."""
    path = Path(directory)
    if not path.exists():
        return 0
    extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff'}
    return sum(1 for f in path.iterdir() 
               if f.is_file() and f.suffix.lower() in extensions)


def run_agent(
    keyword: str,
    target_count: int,
    batch_size: int = 50,
    output_size: tuple = (1920, 1080),
    word_height: int = 100,
    partial_match: bool = True,
    background: str = 'white',
    progress_callback: Optional[Callable[[str], None]] = None
) -> dict:
    """
    Automated agent that fetches and aligns images until target count is reached.
    
    Args:
        keyword: Word to search for and align on
        target_count: Target number of aligned images
        batch_size: Images to fetch per batch (default: 50)
        output_size: Output image dimensions
        word_height: Target word height in pixels
        partial_match: Enable partial word matching
        background: Background color (white/black/dominant)
        progress_callback: Function to call with progress messages
        
    Returns:
        dict with keys: success, total_aligned, total_fetched, batches, error
    """
    
    def log(msg: str):
        if progress_callback:
            progress_callback(msg)
    
    result = {
        'success': False,
        'total_aligned': 0,
        'total_fetched': 0,
        'batches': 0,
        'error': None
    }
    
    # Create directories
    Path("input").mkdir(exist_ok=True)
    Path("output").mkdir(exist_ok=True)
    
    # Clear input folder for fresh start
    for f in Path("input").iterdir():
        if f.is_file() and f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff'}:
            f.unlink()
    
    # Create aligner
    aligner = ImageWordAligner(
        target_word=keyword,
        output_size=output_size,
        word_height=word_height,
        exact_match=not partial_match,
        background=background
    )
    
    total_aligned = get_image_count("output")
    total_fetched = 0
    batch_num = 0
    max_batches = 20  # Safety limit
    
    log(f"Target: {target_count} aligned images for '{keyword}'")
    log(f"Starting with {total_aligned} existing images in output/")
    
    while total_aligned < target_count and batch_num < max_batches:
        batch_num += 1
        log(f"\nBatch {batch_num}: Fetching {batch_size} images...")
        
        # Clear input for this batch
        for f in Path("input").iterdir():
            if f.is_file() and f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff'}:
                f.unlink()
        
        # Fetch images
        fetched = fetch_images(keyword, limit=batch_size, output_dir="input")
        fetched_count = len(fetched)
        total_fetched += fetched_count
        
        if fetched_count == 0:
            log("No images fetched, stopping.")
            break
        
        log(f"Fetched {fetched_count} images")
        
        # Get input image paths
        extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff'}
        image_paths = [str(f) for f in Path("input").iterdir() 
                       if f.is_file() and f.suffix.lower() in extensions]
        
        # Align images
        log(f"Aligning images...")
        before_align = get_image_count("output")
        
        try:
            results = aligner.process_images(image_paths, Path("output"))
            successful = sum(1 for success, _, _ in results if success)
            log(f"Aligned {successful} out of {len(image_paths)} images")
        except Exception as e:
            log(f"Alignment error: {e}")
            successful = 0
        
        total_aligned = get_image_count("output")
        log(f"Total aligned: {total_aligned}/{target_count}")
        
        # Check if we're making progress
        if successful == 0 and batch_num > 3:
            log("No successful alignments in recent batches, stopping.")
            break
    
    # Clean up input folder
    for f in Path("input").iterdir():
        if f.is_file() and f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff'}:
            f.unlink()
    
    result['total_aligned'] = total_aligned
    result['total_fetched'] = total_fetched
    result['batches'] = batch_num
    result['success'] = total_aligned >= target_count
    
    if total_aligned >= target_count:
        log(f"\nComplete! {total_aligned} aligned images ready.")
    else:
        log(f"\nStopped at {total_aligned} aligned images (target: {target_count})")
        if total_aligned < target_count:
            result['error'] = f"Only found {total_aligned} matching images"
    
    return result
