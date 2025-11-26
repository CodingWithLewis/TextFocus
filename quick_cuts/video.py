"""
Video creation from aligned images.
"""

from pathlib import Path
from typing import List, Optional

import imageio.v3 as iio
import numpy as np
from PIL import Image


def get_image_files(input_dir: str = "output") -> List[Path]:
    """Get sorted list of image files from directory."""
    extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif'}
    input_path = Path(input_dir)
    
    if not input_path.exists():
        return []
    
    return sorted([f for f in input_path.iterdir() 
                   if f.is_file() and f.suffix.lower() in extensions])


def create_video(
    input_dir: str = "output",
    output_file: str = "output.mp4",
    delay_ms: int = 100,
    output_dir: Optional[str] = None
) -> dict:
    """
    Create video from images in a directory.
    
    Args:
        input_dir: Directory containing source images
        output_file: Output video filename
        delay_ms: Delay between frames in milliseconds
        output_dir: Directory to save video (default: current directory)
        
    Returns:
        dict with keys: success, path, frames, fps, duration_sec, error
    """
    result = {
        'success': False,
        'path': None,
        'frames': 0,
        'fps': 0,
        'duration_sec': 0,
        'error': None
    }
    
    # Get image files
    image_files = get_image_files(input_dir)
    
    if not image_files:
        result['error'] = f"No images found in {input_dir}/"
        return result
    
    # Calculate FPS from delay
    fps = 1000.0 / delay_ms
    
    # Determine output path
    if output_dir:
        video_path = Path(output_dir) / output_file
    else:
        video_path = Path(output_file)
    
    # Ensure output directory exists
    video_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Ensure .mp4 extension
    if not str(video_path).lower().endswith('.mp4'):
        video_path = Path(str(video_path) + '.mp4')
    
    try:
        # Read first image to determine target size
        first_img = Image.open(image_files[0])
        if first_img.mode == 'RGBA':
            first_img = first_img.convert('RGB')
        target_size = first_img.size  # (width, height)
        
        # Collect all frames
        frames = []
        for img_path in image_files:
            try:
                img = Image.open(img_path)
                
                # Convert to RGB if needed (remove alpha channel)
                if img.mode == 'RGBA':
                    # Create white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize to match first image if needed
                if img.size != target_size:
                    img = img.resize(target_size, Image.Resampling.LANCZOS)
                
                frames.append(np.array(img))
            except Exception:
                continue
        
        if not frames:
            result['error'] = "Could not read any images"
            return result
        
        # Write video using imageio with ffmpeg backend
        iio.imwrite(
            str(video_path),
            frames,
            fps=fps,
            codec='libx264',
            plugin='pyav'
        )
        
        result['success'] = True
        result['path'] = str(video_path)
        result['frames'] = len(frames)
        result['fps'] = fps
        result['duration_sec'] = len(frames) * delay_ms / 1000
        
    except Exception as e:
        result['error'] = str(e)
    
    return result
