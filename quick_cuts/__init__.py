"""
Quick Cuts - Automatically align and center words in images using OCR.
"""

from .aligner import ImageWordAligner, ProcessingError
from .scraper import aggregate_content

__version__ = "1.0.0"
__all__ = ["ImageWordAligner", "ProcessingError", "aggregate_content"]
