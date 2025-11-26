"""
Video creation from aligned images.
"""

from pathlib import Path
from typing import List, Optional


def get_image_files(input_dir: str = "output") -> List[Path]:
    """Get sorted list of image files from directory."""
    extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
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
        output_dir: Directory to save video (default: same as input_dir)
        
    Returns:
        dict with keys: success, path, frames, fps, duration_sec, error
    """
    import cv2
    
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
    
    # Read first image to get dimensions
    first_img = cv2.imread(str(image_files[0]))
    if first_img is None:
        result['error'] = "Could not read first image"
        return result
    
    height, width = first_img.shape[:2]
    
    # Calculate FPS from delay
    fps = 1000.0 / delay_ms
    
    # Determine output path
    if output_dir:
        video_path = Path(output_dir) / output_file
    else:
        video_path = Path(input_dir) / output_file
    
    # Ensure output directory exists
    video_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Ensure .mp4 extension
    if not str(video_path).endswith('.mp4'):
        video_path = Path(str(video_path) + '.mp4')
    
    try:
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video = cv2.VideoWriter(str(video_path), fourcc, fps, (width, height))
        
        # Write frames
        frame_count = 0
        for img_path in image_files:
            img = cv2.imread(str(img_path))
            if img is not None:
                # Resize if needed to match first image
                if img.shape[:2] != (height, width):
                    img = cv2.resize(img, (width, height))
                video.write(img)
                frame_count += 1
        
        video.release()
        
        result['success'] = True
        result['path'] = str(video_path)
        result['frames'] = frame_count
        result['fps'] = fps
        result['duration_sec'] = frame_count * delay_ms / 1000
        
    except Exception as e:
        result['error'] = str(e)
    
    return result
