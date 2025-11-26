"""
Quick Cuts - Automatically align and center words in images using OCR.
"""

from .aligner import ImageWordAligner, ProcessingError
from .scraper import aggregate_content, fetch_images
from .video import create_video

__version__ = "1.0.0"
__all__ = ["ImageWordAligner", "ProcessingError", "aggregate_content", "fetch_images", "create_video"]
