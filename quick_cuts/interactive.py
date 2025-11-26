"""
Interactive CLI for Quick Cuts.
Professional menu-driven interface for fetching and aligning images.
"""

import os
import sys
from pathlib import Path

from .aligner import ImageWordAligner
from .scraper import fetch_images
from .video import create_video, get_image_files
from .agent import run_agent


def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def get_image_count(directory):
    """Count images in a directory."""
    if not Path(directory).exists():
        return 0
    extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff'}
    return sum(1 for f in Path(directory).iterdir() 
               if f.is_file() and f.suffix.lower() in extensions)


def print_header():
    """Print application header."""
    print()
    print("=" * 50)
    print("  QUICK CUTS - Word Alignment Tool")
    print("=" * 50)
    print()


def print_status():
    """Print current status of input/output folders."""
    input_count = get_image_count("input")
    output_count = get_image_count("output")
    
    print(f"  Input folder:  {input_count} images")
    print(f"  Output folder: {output_count} images")
    print()


def print_menu():
    """Print main menu options."""
    print("  [1] Fetch images from web")
    print("  [2] Align images")
    print("  [3] Agent mode (auto-collect)")
    print("  [4] Create video from output")
    print("  [5] Clear input folder")
    print("  [6] Clear output folder")
    print("  [7] Clear attributions")
    print("  [8] Exit")
    print()


def fetch_images_interactive():
    """Interactive image fetching."""
    clear_screen()
    print_header()
    print("  FETCH IMAGES")
    print("  " + "-" * 30)
    print()
    
    # Get search query
    query = input("  Search term: ").strip()
    if not query:
        print("\n  Cancelled - no search term provided.")
        input("\n  Press Enter to continue...")
        return
    
    # Get number of images
    try:
        count_str = input("  Number of images [10]: ").strip()
        count = int(count_str) if count_str else 10
        if count < 1 or count > 50:
            print("\n  Error: Number must be between 1 and 50.")
            input("\n  Press Enter to continue...")
            return
    except ValueError:
        print("\n  Error: Invalid number.")
        input("\n  Press Enter to continue...")
        return
    
    print()
    print(f"  Fetching {count} images for '{query}'...")
    print()
    
    # Fetch images
    saved = fetch_images(query, limit=count, output_dir="input")
    
    print()
    if saved:
        print(f"  Downloaded {len(saved)} images to input/")
    else:
        print("  No images were downloaded.")
    
    input("\n  Press Enter to continue...")


def align_images_interactive():
    """Interactive image alignment."""
    clear_screen()
    print_header()
    print("  ALIGN IMAGES")
    print("  " + "-" * 30)
    print()
    
    # Check input folder
    input_count = get_image_count("input")
    if input_count == 0:
        print("  Error: No images in input folder.")
        print("  Use option [1] to fetch images first.")
        input("\n  Press Enter to continue...")
        return
    
    print(f"  Found {input_count} images in input/")
    print()
    
    # Get target word
    word = input("  Target word to center: ").strip()
    if not word:
        print("\n  Cancelled - no word provided.")
        input("\n  Press Enter to continue...")
        return
    
    # Partial matching
    partial_input = input("  Enable partial matching? [y/N]: ").strip().lower()
    partial = partial_input in ['y', 'yes']
    
    # Output size
    size_input = input("  Output size [1920x1080]: ").strip()
    if size_input:
        try:
            width, height = map(int, size_input.split('x'))
            output_size = (width, height)
        except ValueError:
            print("\n  Error: Invalid size format. Use WIDTHxHEIGHT.")
            input("\n  Press Enter to continue...")
            return
    else:
        output_size = (1920, 1080)
    
    # Word height
    height_input = input("  Word height in pixels [100]: ").strip()
    try:
        word_height = int(height_input) if height_input else 100
    except ValueError:
        print("\n  Error: Invalid number.")
        input("\n  Press Enter to continue...")
        return
    
    # Background
    print()
    print("  Background options: white, black, dominant")
    bg_input = input("  Background [white]: ").strip().lower()
    background = bg_input if bg_input in ['white', 'black', 'dominant'] else 'white'
    
    print()
    print("  Processing...")
    print()
    
    # Collect image paths
    extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff'}
    image_paths = [str(f) for f in Path("input").iterdir() 
                   if f.is_file() and f.suffix.lower() in extensions]
    
    # Create output directory
    Path("output").mkdir(exist_ok=True)
    
    # Process
    aligner = ImageWordAligner(
        target_word=word,
        output_size=output_size,
        word_height=word_height,
        exact_match=not partial,
        background=background
    )
    
    results = aligner.process_images(image_paths, Path("output"))
    
    successful = sum(1 for success, _, _ in results if success)
    failed = len(results) - successful
    
    print()
    print("  " + "-" * 30)
    print(f"  Completed: {successful} aligned, {failed} failed")
    print(f"  Output saved to: output/")
    
    input("\n  Press Enter to continue...")


def clear_folder(folder_name):
    """Clear all images from a folder."""
    folder = Path(folder_name)
    if not folder.exists():
        return 0
    
    extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff'}
    count = 0
    for f in folder.iterdir():
        if f.is_file() and f.suffix.lower() in extensions:
            f.unlink()
            count += 1
    return count


def clear_input_interactive():
    """Clear input folder."""
    deleted = clear_folder("input")
    # No prompt needed, will refresh on next menu display


def clear_output_interactive():
    """Clear output folder."""
    deleted = clear_folder("output")
    # No prompt needed, will refresh on next menu display


def clear_attributions_interactive():
    """Clear copyright attributions folder."""
    import shutil
    attr_path = Path("copyright_attributions")
    if attr_path.exists():
        shutil.rmtree(attr_path)
    # No prompt needed, will refresh on next menu display


def agent_interactive():
    """Run agent mode to auto-collect aligned images."""
    clear_screen()
    print_header()
    print("  AGENT MODE")
    print("  " + "-" * 30)
    print()
    print("  Automatically fetch and align images until target is reached.")
    print()
    
    # Get keyword
    keyword = input("  Keyword to search and align: ").strip()
    if not keyword:
        print("\n  Cancelled - no keyword provided.")
        input("\n  Press Enter to continue...")
        return
    
    # Get target count
    target_input = input("  Target number of aligned images [100]: ").strip()
    try:
        target = int(target_input) if target_input else 100
        if target < 1 or target > 1000:
            print("\n  Error: Target must be between 1 and 1000.")
            input("\n  Press Enter to continue...")
            return
    except ValueError:
        print("\n  Error: Invalid number.")
        input("\n  Press Enter to continue...")
        return
    
    # Get batch size
    batch_input = input("  Images per batch [50]: ").strip()
    try:
        batch_size = int(batch_input) if batch_input else 50
        if batch_size < 10 or batch_size > 100:
            print("\n  Error: Batch size must be between 10 and 100.")
            input("\n  Press Enter to continue...")
            return
    except ValueError:
        print("\n  Error: Invalid number.")
        input("\n  Press Enter to continue...")
        return
    
    print()
    print("  Starting agent...")
    print()
    
    def progress(msg):
        print(f"  {msg}")
    
    result = run_agent(
        keyword=keyword,
        target_count=target,
        batch_size=batch_size,
        partial_match=True,
        progress_callback=progress
    )
    
    print()
    print("  " + "-" * 30)
    print(f"  Batches: {result['batches']}")
    print(f"  Total fetched: {result['total_fetched']}")
    print(f"  Total aligned: {result['total_aligned']}")
    
    if result['success']:
        print(f"  Status: Complete!")
    else:
        print(f"  Status: {result['error'] or 'Stopped early'}")
    
    input("\n  Press Enter to continue...")


def create_video_interactive():
    """Create video from output images."""
    clear_screen()
    print_header()
    print("  CREATE VIDEO")
    print("  " + "-" * 30)
    print()
    
    # Check output folder
    output_count = get_image_count("output")
    if output_count == 0:
        print("  Error: No images in output folder.")
        print("  Use option [2] to align images first.")
        input("\n  Press Enter to continue...")
        return
    
    print(f"  Found {output_count} images in output/")
    print()
    
    # Get delay
    delay_input = input("  Delay between frames in ms [100]: ").strip()
    try:
        delay_ms = int(delay_input) if delay_input else 100
        if delay_ms < 10 or delay_ms > 5000:
            print("\n  Error: Delay must be between 10 and 5000 ms.")
            input("\n  Press Enter to continue...")
            return
    except ValueError:
        print("\n  Error: Invalid number.")
        input("\n  Press Enter to continue...")
        return
    
    # Get output filename
    filename_input = input("  Output filename [output.mp4]: ").strip()
    filename = filename_input if filename_input else "output.mp4"
    
    print()
    print("  Creating video...")
    print()
    
    result = create_video(
        input_dir="output",
        output_file=filename,
        delay_ms=delay_ms
    )
    
    if result['success']:
        print("  " + "-" * 30)
        print(f"  Video created: {result['path']}")
        print(f"  Frames: {result['frames']}")
        print(f"  FPS: {result['fps']:.1f} ({delay_ms}ms delay)")
        print(f"  Duration: {result['duration_sec']:.1f}s")
    else:
        print(f"  Error: {result['error']}")
    
    input("\n  Press Enter to continue...")


def main():
    """Main interactive loop."""
    while True:
        clear_screen()
        print_header()
        print_status()
        print_menu()
        
        choice = input("  Select option: ").strip()
        
        if choice == '1':
            fetch_images_interactive()
        elif choice == '2':
            align_images_interactive()
        elif choice == '3':
            agent_interactive()
        elif choice == '4':
            create_video_interactive()
        elif choice == '5':
            clear_input_interactive()
        elif choice == '6':
            clear_output_interactive()
        elif choice == '7':
            clear_attributions_interactive()
        elif choice == '8':
            clear_screen()
            print("\n  Goodbye.\n")
            sys.exit(0)
        else:
            pass  # Invalid input, just refresh menu


if __name__ == "__main__":
    main()
