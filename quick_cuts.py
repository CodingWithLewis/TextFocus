import cv2
import numpy as np
import pytesseract
from pytesseract import Output
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable
import logging
import sys
from multiprocessing import Pool, cpu_count, Manager, Value
import functools
from sklearn.cluster import KMeans
import threading
import time

# Route logs to stdout so Electron treats them as normal output (not errors)
# Use force=True to ensure child processes (multiprocessing) pick up configuration
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(levelname)s:%(name)s:%(message)s', force=True)
logger = logging.getLogger(__name__)

class ImageWordAligner:
    def __init__(self, target_word: str, output_size: Tuple[int, int] = (1920, 1080), word_height: int = 100, exact_match: bool = True, background: str = 'dominant'):
        self.target_word = target_word.lower()
        self.output_width, self.output_height = output_size
        self.target_word_height = word_height
        self.exact_match = exact_match
        self.background = background
        self.cancelled = False
        self.progress_callback = None
        self.current_progress = 0
        self.total_images = 0
        
    def get_dominant_color(self, image: np.ndarray, n_colors: int = 5) -> Tuple[int, int, int]:
        """Extract the dominant color from an image using K-means clustering"""
        # Reshape image to be a list of pixels
        pixels = image.reshape((-1, 3))
        
        # Apply K-means clustering to find dominant colors
        kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
        kmeans.fit(pixels)
        
        # Get the color with the most pixels assigned to it
        labels = kmeans.labels_
        label_counts = np.bincount(labels)
        dominant_label = label_counts.argmax()
        
        # Get the dominant color (BGR format)
        dominant_color = kmeans.cluster_centers_[dominant_label]
        
        return tuple(map(int, dominant_color))
    
    def find_word_in_image(self, image_path: str) -> Optional[Dict]:
        """Use OCR to find the target word and its bounding box in an image"""
        # Handle Unicode characters in path
        try:
            # Try reading with Unicode path support
            image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        except:
            # Fallback to regular imread
            image = cv2.imread(image_path)
            
        if image is None:
            logger.error(f"Could not read image: {image_path}")
            return None
            
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply preprocessing for better OCR
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Get OCR data with bounding boxes
        data = pytesseract.image_to_data(thresh, output_type=Output.DICT)
        
        # Find the target word with highest confidence
        best_match = None
        highest_conf = 0
        
        for i, word in enumerate(data['text']):
            word_lower = word.lower()
            
            # Check for match based on mode
            is_match = False
            if self.exact_match:
                is_match = word_lower == self.target_word
            else:
                # Partial match: check if target word is at the beginning of the detected word
                is_match = word_lower.startswith(self.target_word)
            
            if is_match:
                conf = data['conf'][i]
                if conf > highest_conf and conf > 30:  # Confidence threshold
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    
                    # For partial matches, try to estimate the width of just the target word
                    if not self.exact_match and word_lower != self.target_word:
                        # Estimate the proportion of the word that is our target
                        proportion = len(self.target_word) / len(word_lower)
                        w = int(w * proportion)
                    
                    best_match = {
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                        'center_x': x + w // 2,
                        'center_y': y + h // 2,
                        'confidence': conf,
                        'image': image,
                        'detected_word': word
                    }
                    highest_conf = conf
        
        return best_match
    
    def create_aligned_image(self, word_data: Dict) -> np.ndarray:
        """Create a new image with the word centered and at consistent size"""
        source_image = word_data['image']
        
        # Calculate scale to make word the target height
        scale = self.target_word_height / word_data['height'] if word_data['height'] > 0 else 1.0
        
        # Resize the entire source image
        new_width = int(source_image.shape[1] * scale)
        new_height = int(source_image.shape[0] * scale)
        resized = cv2.resize(source_image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Calculate new word position after scaling
        word_center_x = int(word_data['center_x'] * scale)
        word_center_y = int(word_data['center_y'] * scale)
        
        # Create output image with background color
        if self.background == 'dominant':
            # Get dominant color from the source image
            dominant_color = self.get_dominant_color(source_image)
            output = np.ones((self.output_height, self.output_width, 3), dtype=np.uint8)
            output[:] = dominant_color
        elif self.background == 'black':
            output = np.zeros((self.output_height, self.output_width, 3), dtype=np.uint8)
        elif self.background == 'transparent':
            # For transparent, we'll use a 4-channel image (BGRA)
            output = np.ones((self.output_height, self.output_width, 4), dtype=np.uint8) * 255
            output[:, :, 3] = 0  # Set alpha channel to 0 (transparent)
        else:  # white
            output = np.ones((self.output_height, self.output_width, 3), dtype=np.uint8) * 255
        
        # Calculate where to place the resized image to center the word
        output_center_x = self.output_width // 2
        output_center_y = self.output_height // 2
        
        # Calculate the region of the resized image we want to copy
        src_left = max(0, word_center_x - output_center_x)
        src_top = max(0, word_center_y - output_center_y)
        src_right = min(new_width, word_center_x + output_center_x)
        src_bottom = min(new_height, word_center_y + output_center_y)
        
        # Calculate where to paste in the output image
        dst_left = max(0, output_center_x - word_center_x)
        dst_top = max(0, output_center_y - word_center_y)
        
        # Calculate the actual dimensions to copy
        copy_width = min(src_right - src_left, self.output_width - dst_left)
        copy_height = min(src_bottom - src_top, self.output_height - dst_top)
        
        # Ensure we don't exceed bounds
        dst_right = dst_left + copy_width
        dst_bottom = dst_top + copy_height
        
        # Copy the region
        if copy_width > 0 and copy_height > 0:
            if self.background == 'transparent':
                # For transparent background, copy RGB channels and set alpha to 255 for copied region
                output[dst_top:dst_bottom, dst_left:dst_right, :3] = \
                    resized[src_top:src_top + copy_height, src_left:src_left + copy_width]
                output[dst_top:dst_bottom, dst_left:dst_right, 3] = 255
            else:
                output[dst_top:dst_bottom, dst_left:dst_right] = \
                    resized[src_top:src_top + copy_height, src_left:src_left + copy_width]
        
        return output
    
    def process_single_image(self, image_path: str, output_dir: Path) -> Tuple[bool, str, Optional[str]]:
        """Process a single image and return success status"""
        logger.info(f"Processing: {image_path}")
        word_data = self.find_word_in_image(image_path)
        
        if word_data:
            # Create aligned image
            aligned_image = self.create_aligned_image(word_data)
            
            # Save with same name in output directory
            output_filename = f"aligned_{Path(image_path).name}"
            # Force PNG format for transparent images
            if self.background == 'transparent':
                output_filename = output_filename.rsplit('.', 1)[0] + '.png'
            output_path = output_dir / output_filename
            
            # Handle Unicode in output path as well
            try:
                cv2.imwrite(str(output_path), aligned_image)
            except:
                # Use numpy save method for Unicode paths
                ext = '.png' if self.background == 'transparent' else Path(image_path).suffix
                is_success, im_buf_arr = cv2.imencode(ext, aligned_image)
                if is_success:
                    im_buf_arr.tofile(str(output_path))
            
            detected = word_data.get('detected_word', self.target_word)
            if detected != self.target_word:
                logger.info(f"Saved aligned image: {output_filename} (detected '{detected}')")
            else:
                logger.info(f"Saved aligned image: {output_filename}")
            return True, Path(image_path).name, detected
        else:
            logger.warning(f"'{self.target_word}' not found in {Path(image_path).name}")
            return False, Path(image_path).name, None
    
    def process_images(self, image_paths: List[str], output_dir: Path, workers: int = None):
        """Process all images in parallel and save aligned versions"""
        if workers is None:
            workers = min(cpu_count(), len(image_paths))
        
        logger.info(f"Processing {len(image_paths)} images using {workers} workers...")
        
        # Create partial function with fixed output_dir
        process_func = functools.partial(self.process_single_image, output_dir=output_dir)
        
        # Process images in parallel
        with Pool(processes=workers) as pool:
            results = pool.map(process_func, image_paths)
        
        # Count successes and failures
        successful = sum(1 for success, _, _ in results if success)
        failed = [name for success, name, _ in results if not success]
        
        logger.info(f"\nProcessing complete!")
        logger.info(f"Successfully aligned: {successful} images")
        if failed:
            logger.info(f"Failed to find word in: {', '.join(failed)}")

def main():
    parser = argparse.ArgumentParser(
        description='Align words in images and export as ready-to-use image files'
    )
    parser.add_argument('images', nargs='+', help='Input image file(s) or directory')
    parser.add_argument('-w', '--word', required=True, help='Target word to center')
    parser.add_argument('-o', '--output', default=None, 
                       help='Output directory for aligned images (default: ./aligned_[word])')
    parser.add_argument('-s', '--size', default='1920x1080',
                       help='Output image size (default: 1920x1080)')
    parser.add_argument('--word-height', type=int, default=100,
                       help='Target height for the word in pixels (default: 100)')
    parser.add_argument('--background', default='dominant',
                       choices=['white', 'black', 'transparent', 'dominant'],
                       help='Background color (default: dominant - uses the most dominant color from the image)')
    parser.add_argument('--partial', action='store_true',
                       help='Enable partial matching (e.g., "warp" matches "warpdotdev")')
    parser.add_argument('--workers', type=int, default=None,
                       help='Number of parallel workers (default: number of CPU cores)')
    
    args = parser.parse_args()
    
    # Parse output size
    width, height = map(int, args.size.split('x'))
    
    # Collect all image files
    image_files = []
    for path in args.images:
        path_obj = Path(path)
        if path_obj.is_dir():
            # Get all common image formats from directory
            for pattern in ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']:
                image_files.extend(path_obj.glob(pattern))
        elif path_obj.exists():
            image_files.append(path_obj)
    
    if not image_files:
        logger.error("No image files found")
        return
    
    # Convert to string paths
    image_paths = [str(f) for f in image_files]
    logger.info(f"Found {len(image_paths)} images to process")
    
    # Create output directory
    if args.output is None:
        output_dir = Path(f"./aligned_{args.word}")
    else:
        output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Process images
    aligner = ImageWordAligner(args.word, (width, height), args.word_height, exact_match=not args.partial, background=args.background)
    aligner.process_images(image_paths, output_dir, workers=args.workers)
    
    logger.info(f"\nAligned images saved to: {output_dir.absolute()}")

if __name__ == "__main__":
    main()