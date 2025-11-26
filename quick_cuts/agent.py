"""
Agent mode - Automated workflow to collect a target number of aligned images.
"""

import os
import shutil
import logging
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
    
    # Suppress aligner logging
    logging.getLogger('quick_cuts.aligner').setLevel(logging.WARNING)
    
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
    extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff'}
    for f in Path("input").iterdir():
        if f.is_file() and f.suffix.lower() in extensions:
            f.unlink()
    
    # Create aligner
    aligner = ImageWordAligner(
        target_word=keyword,
        output_size=output_size,
        word_height=word_height,
        exact_match=not partial_match,
        background=background
    )
    
    # Track state
    all_downloaded_urls = set()
    search_offset = 0
    input_file_counter = 1
    total_fetched = 0
    batch_num = 0
    max_batches = 50  # Safety limit
    no_new_images_count = 0
    
    # Count existing aligned images
    initial_aligned = get_image_count("output")
    log(f"Target: {target_count} aligned images for '{keyword}'")
    log(f"Starting with {initial_aligned} existing images in output/")
    
    while get_image_count("output") < target_count and batch_num < max_batches:
        batch_num += 1
        current_aligned = get_image_count("output")
        
        log(f"\nBatch {batch_num}: Fetching images (offset {search_offset})...")
        
        # Clear input for this batch
        for f in Path("input").iterdir():
            if f.is_file() and f.suffix.lower() in extensions:
                f.unlink()
        
        # Fetch images with pagination and exclusion
        fetched_files, new_urls = fetch_images(
            keyword, 
            limit=batch_size, 
            output_dir="input",
            offset=search_offset,
            exclude_urls=all_downloaded_urls,
            filename_start=input_file_counter
        )
        
        fetched_count = len(fetched_files)
        total_fetched += fetched_count
        all_downloaded_urls.update(new_urls)
        input_file_counter += fetched_count
        
        # Increment offset for next batch
        search_offset += batch_size
        
        if fetched_count == 0:
            no_new_images_count += 1
            log(f"No new images found (attempt {no_new_images_count}/3)")
            if no_new_images_count >= 3:
                log("No more images available, stopping.")
                break
            continue
        else:
            no_new_images_count = 0
        
        log(f"Fetched {fetched_count} new images")
        
        # Get input image paths
        image_paths = [str(f) for f in Path("input").iterdir() 
                       if f.is_file() and f.suffix.lower() in extensions]
        
        # Align images
        log(f"Aligning...")
        
        try:
            results = aligner.process_images(image_paths, Path("output"))
            successful = sum(1 for success, _, _ in results if success)
            log(f"Aligned {successful}/{len(image_paths)} images")
        except Exception as e:
            log(f"Alignment error: {e}")
            successful = 0
        
        new_aligned = get_image_count("output")
        log(f"Progress: {new_aligned}/{target_count}")
    
    # Clean up input folder
    for f in Path("input").iterdir():
        if f.is_file() and f.suffix.lower() in extensions:
            f.unlink()
    
    final_aligned = get_image_count("output")
    result['total_aligned'] = final_aligned
    result['total_fetched'] = total_fetched
    result['batches'] = batch_num
    result['success'] = final_aligned >= target_count
    
    if final_aligned >= target_count:
        log(f"\nComplete! {final_aligned} aligned images ready.")
    else:
        log(f"\nStopped at {final_aligned} aligned images (target: {target_count})")
        if final_aligned < target_count:
            result['error'] = f"Only found {final_aligned} matching images"
    
    return result
