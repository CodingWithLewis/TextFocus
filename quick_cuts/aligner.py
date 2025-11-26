"""
Core image processing engine for Quick Cuts.
Detects words via OCR and creates aligned images with the word centered.
"""

import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable
import logging
from multiprocessing import cpu_count
from sklearn.cluster import KMeans
import threading
import time
import traceback


class ProcessingError(Exception):
    """Custom exception for processing errors"""
    pass


class ImageWordAligner:
    """
    Finds a target word in images using OCR and creates new images
    with the word centered and consistently sized.
    """
    
    def __init__(
        self, 
        target_word: str, 
        output_size: Tuple[int, int] = (1920, 1080), 
        word_height: int = 100, 
        exact_match: bool = True, 
        background: str = 'dominant',
        progress_callback: Optional[Callable[[int, int, str, str], None]] = None
    ):
        self.target_word = target_word.lower()
        self.output_width, self.output_height = output_size
        self.target_word_height = word_height
        self.exact_match = exact_match
        self.background = background
        self.progress_callback = progress_callback
        
        self._cancelled = threading.Event()
        self._processing_lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
    def cancel(self):
        """Request cancellation of processing"""
        self._cancelled.set()
        self.logger.info("Cancellation requested")
    
    def is_cancelled(self) -> bool:
        """Check if processing has been cancelled"""
        return self._cancelled.is_set()
    
    def _report_progress(self, current: int, total: int, current_file: str, operation: str):
        """Report progress if callback is available"""
        if self.progress_callback:
            try:
                self.progress_callback(current, total, current_file, operation)
            except Exception as e:
                self.logger.error(f"Error in progress callback: {e}")
    
    def get_dominant_color(self, image: np.ndarray, n_colors: int = 5) -> Tuple[int, int, int]:
        """Extract the dominant color from an image using K-means clustering"""
        try:
            pixels = image.reshape((-1, 3))
            kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            labels = kmeans.labels_
            label_counts = np.bincount(labels)
            dominant_label = label_counts.argmax()
            dominant_color = kmeans.cluster_centers_[dominant_label]
            
            return tuple(map(int, dominant_color))
        except Exception as e:
            self.logger.error(f"Error extracting dominant color: {e}")
            return (255, 255, 255)
    
    def find_word_in_image(self, image_path: str) -> Optional[Dict]:
        """Use OCR to find the target word and its bounding box in an image"""
        try:
            # Handle Unicode characters in path
            try:
                image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            except Exception:
                image = cv2.imread(image_path)
                
            if image is None:
                raise ProcessingError(f"Could not read image: {image_path}")
                
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Preprocessing for better OCR
            gray = cv2.bilateralFilter(gray, 9, 75, 75)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            data = pytesseract.image_to_data(thresh, output_type=Output.DICT)
            
            best_match = None
            highest_conf = 0
            
            for i, word in enumerate(data['text']):
                word_lower = word.lower()
                
                if self.exact_match:
                    is_match = word_lower == self.target_word
                else:
                    is_match = word_lower.startswith(self.target_word)
                
                if is_match:
                    conf = data['conf'][i]
                    if conf > highest_conf and conf > 30:
                        x = data['left'][i]
                        y = data['top'][i]
                        w = data['width'][i]
                        h = data['height'][i]
                        
                        if not self.exact_match and word_lower != self.target_word:
                            proportion = len(self.target_word) / len(word_lower)
                            w = int(w * proportion)
                        
                        best_match = {
                            'x': x, 'y': y,
                            'width': w, 'height': h,
                            'center_x': x + w // 2,
                            'center_y': y + h // 2,
                            'confidence': conf,
                            'image': image,
                            'detected_word': word
                        }
                        highest_conf = conf
            
            return best_match
            
        except Exception as e:
            self.logger.error(f"Error processing image {image_path}: {e}")
            return None
    
    def create_aligned_image(self, word_data: Dict) -> np.ndarray:
        """Create a new image with the word centered and at consistent size"""
        try:
            source_image = word_data['image']
            
            scale = self.target_word_height / word_data['height'] if word_data['height'] > 0 else 1.0
            
            new_width = int(source_image.shape[1] * scale)
            new_height = int(source_image.shape[0] * scale)
            resized = cv2.resize(source_image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            
            word_center_x = int(word_data['center_x'] * scale)
            word_center_y = int(word_data['center_y'] * scale)
            
            # Create output with background
            if self.background == 'dominant':
                dominant_color = self.get_dominant_color(source_image)
                output = np.ones((self.output_height, self.output_width, 3), dtype=np.uint8)
                output[:] = dominant_color
            elif self.background == 'black':
                output = np.zeros((self.output_height, self.output_width, 3), dtype=np.uint8)
            elif self.background == 'transparent':
                output = np.ones((self.output_height, self.output_width, 4), dtype=np.uint8) * 255
                output[:, :, 3] = 0
            else:  # white
                output = np.ones((self.output_height, self.output_width, 3), dtype=np.uint8) * 255
            
            output_center_x = self.output_width // 2
            output_center_y = self.output_height // 2
            
            src_left = max(0, word_center_x - output_center_x)
            src_top = max(0, word_center_y - output_center_y)
            src_right = min(new_width, word_center_x + output_center_x)
            src_bottom = min(new_height, word_center_y + output_center_y)
            
            dst_left = max(0, output_center_x - word_center_x)
            dst_top = max(0, output_center_y - word_center_y)
            
            copy_width = min(src_right - src_left, self.output_width - dst_left)
            copy_height = min(src_bottom - src_top, self.output_height - dst_top)
            
            dst_right = dst_left + copy_width
            dst_bottom = dst_top + copy_height
            
            if copy_width > 0 and copy_height > 0:
                if self.background == 'transparent':
                    output[dst_top:dst_bottom, dst_left:dst_right, :3] = \
                        resized[src_top:src_top + copy_height, src_left:src_left + copy_width]
                    output[dst_top:dst_bottom, dst_left:dst_right, 3] = 255
                else:
                    output[dst_top:dst_bottom, dst_left:dst_right] = \
                        resized[src_top:src_top + copy_height, src_left:src_left + copy_width]
            
            return output
            
        except Exception as e:
            self.logger.error(f"Error creating aligned image: {e}")
            raise ProcessingError(f"Failed to create aligned image: {str(e)}")
    
    def process_single_image(self, image_path: str, output_dir: Path, current_index: int, total_count: int) -> Tuple[bool, str, Optional[str]]:
        """Process a single image and return success status"""
        try:
            if self.is_cancelled():
                return False, Path(image_path).name, "Processing cancelled"
            
            filename = Path(image_path).name
            self._report_progress(current_index, total_count, filename, f"Processing {filename}")
            
            word_data = self.find_word_in_image(image_path)
            
            if word_data:
                if self.is_cancelled():
                    return False, filename, "Processing cancelled"
                
                aligned_image = self.create_aligned_image(word_data)
                
                output_filename = f"aligned_{filename}"
                if self.background == 'transparent':
                    output_filename = output_filename.rsplit('.', 1)[0] + '.png'
                output_path = output_dir / output_filename
                
                try:
                    success = cv2.imwrite(str(output_path), aligned_image)
                    if not success:
                        raise ProcessingError("cv2.imwrite failed")
                except Exception:
                    ext = '.png' if self.background == 'transparent' else Path(image_path).suffix
                    is_success, im_buf_arr = cv2.imencode(ext, aligned_image)
                    if is_success:
                        im_buf_arr.tofile(str(output_path))
                    else:
                        raise ProcessingError("Failed to encode image")
                
                detected = word_data.get('detected_word', self.target_word)
                self.logger.info(f"Saved: {output_filename} (detected '{detected}')")
                return True, filename, detected
            else:
                self.logger.warning(f"'{self.target_word}' not found in {filename}")
                return False, filename, f"Word '{self.target_word}' not found"
                
        except Exception as e:
            error_msg = f"Error processing {Path(image_path).name}: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            return False, Path(image_path).name, error_msg
    
    def process_images(self, image_paths: List[str], output_dir: Path, workers: int = None) -> List[Tuple[bool, str, Optional[str]]]:
        """Process all images and return results as (success, filename, message) tuples."""
        if workers is None:
            workers = min(cpu_count(), len(image_paths))
        
        self.logger.info(f"Processing {len(image_paths)} images...")
        
        results = []
        self._cancelled.clear()
        
        try:
            with self._processing_lock:
                for i, image_path in enumerate(image_paths):
                    if self.is_cancelled():
                        self.logger.info("Processing cancelled by user")
                        break
                    
                    result = self.process_single_image(image_path, output_dir, i + 1, len(image_paths))
                    results.append(result)
                    time.sleep(0.01)
        
        except Exception as e:
            self.logger.error(f"Error in process_images: {e}")
            self.logger.error(traceback.format_exc())
            raise ProcessingError(f"Processing failed: {str(e)}")
        
        successful = sum(1 for success, _, _ in results if success)
        failed = len(results) - successful
        
        self.logger.info(f"Done! {successful} successful, {failed} failed")
        
        return results
