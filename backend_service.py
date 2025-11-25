#!/usr/bin/env python3
"""
Backend service for Quick Cuts Electron app.
Communicates with frontend via JSON messages over stdin/stdout.
"""

import sys
import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import traceback

# Import our processing classes
from quick_cuts_backend import ImageWordAligner, ProcessingError
# Web scraping aggregator (optional import; handled gracefully if missing)
try:
    from web_scraper import aggregate_content
except Exception:
    aggregate_content = None


class CommandType(Enum):
    PROCESS_IMAGES = "process_images"
    GET_STATUS = "get_status"
    CANCEL_PROCESSING = "cancel_processing"
    SCRAPE_CONTENT = "scrape_content"
    SHUTDOWN = "shutdown"


@dataclass
class ProcessingStatus:
    """Status information for image processing operations"""
    is_processing: bool = False
    current_image: int = 0
    total_images: int = 0
    processed_images: List[str] = None
    failed_images: List[str] = None
    current_operation: str = ""
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.processed_images is None:
            self.processed_images = []
        if self.failed_images is None:
            self.failed_images = []


class BackendService:
    """Main backend service that handles IPC communication and coordinates processing"""
    
    def __init__(self):
        self.setup_logging()
        self.status = ProcessingStatus()
        self.current_aligner: Optional[ImageWordAligner] = None
        self.processing_thread: Optional[threading.Thread] = None
        self.should_shutdown = False
        
        self.logger.info("Backend service initialized")
    
    def setup_logging(self):
        """Configure logging for subprocess mode"""
        # Create a custom formatter that outputs JSON-safe logs
        self.logger = logging.getLogger('backend_service')
        self.logger.setLevel(logging.INFO)
        
        # Remove any existing handlers to avoid conflicts
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create a file handler for logging (avoid stdout conflicts)
        log_file = Path("backend_service.log")
        handler = logging.FileHandler(log_file, mode='w')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Also log to stderr (not stdout to avoid IPC conflicts)
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(formatter)
        self.logger.addHandler(stderr_handler)
    
    def send_response(self, response: Dict[str, Any]):
        """Send JSON response to stdout"""
        try:
            json_response = json.dumps(response, ensure_ascii=False)
            print(json_response, flush=True)
            self.logger.debug(f"Sent response: {json_response}")
        except Exception as e:
            self.logger.error(f"Error sending response: {e}")
            error_response = {
                "success": False,
                "error": f"Failed to serialize response: {str(e)}"
            }
            print(json.dumps(error_response), flush=True)
    
    def send_progress_update(self):
        """Send current processing status as progress update"""
        response = {
            "type": "progress",
            "status": asdict(self.status)
        }
        self.send_response(response)
    
    def progress_callback(self, current: int, total: int, current_file: str, operation: str):
        """Callback function for progress updates during processing"""
        self.status.current_image = current
        self.status.total_images = total
        self.status.current_operation = operation
        
        self.logger.info(f"Progress: {current}/{total} - {operation} - {current_file}")
        self.send_progress_update()
    
    def handle_process_images(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Handle process_images command"""
        try:
            # Validate required parameters
            required_params = ['target_word', 'image_paths', 'output_dir']
            for param in required_params:
                if param not in command:
                    return {
                        "success": False,
                        "error": f"Missing required parameter: {param}"
                    }
            
            # Extract parameters
            target_word = command['target_word']
            image_paths = command['image_paths']
            output_dir = Path(command['output_dir'])
            
            # Optional parameters with defaults
            output_size = tuple(command.get('output_size', [1920, 1080]))
            word_height = command.get('word_height', 100)
            exact_match = command.get('exact_match', True)
            background = command.get('background', 'dominant')
            workers = command.get('workers', None)
            
            # Validate image paths exist
            valid_paths = []
            for path in image_paths:
                if Path(path).exists():
                    valid_paths.append(path)
                else:
                    self.logger.warning(f"Image path does not exist: {path}")
            
            if not valid_paths:
                return {
                    "success": False,
                    "error": "No valid image paths provided"
                }
            
            # Create output directory
            output_dir.mkdir(exist_ok=True, parents=True)
            
            # Initialize status
            self.status = ProcessingStatus(
                is_processing=True,
                total_images=len(valid_paths),
                current_operation="Initializing processing..."
            )
            
            # Create aligner with progress callback
            self.current_aligner = ImageWordAligner(
                target_word=target_word,
                output_size=output_size,
                word_height=word_height,
                exact_match=exact_match,
                background=background,
                progress_callback=self.progress_callback
            )
            
            # Start processing in a separate thread
            self.processing_thread = threading.Thread(
                target=self._run_processing,
                args=(valid_paths, output_dir, workers),
                daemon=True
            )
            self.processing_thread.start()
            
            return {
                "success": True,
                "message": "Processing started",
                "total_images": len(valid_paths)
            }
            
        except Exception as e:
            self.logger.error(f"Error in handle_process_images: {e}")
            self.logger.error(traceback.format_exc())
            self.status.is_processing = False
            self.status.error_message = str(e)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _run_processing(self, image_paths: List[str], output_dir: Path, workers: Optional[int]):
        """Run image processing in background thread"""
        try:
            self.logger.info(f"Starting processing of {len(image_paths)} images")
            
            # Process images
            results = self.current_aligner.process_images(
                image_paths=image_paths,
                output_dir=output_dir,
                workers=workers
            )
            
            # Update final status
            successful = [name for success, name, _ in results if success]
            failed = [name for success, name, _ in results if not success]
            
            self.status.processed_images = successful
            self.status.failed_images = failed
            self.status.is_processing = False
            self.status.current_operation = "Processing complete"
            
            # Send final update
            response = {
                "type": "completed",
                "status": asdict(self.status),
                "results": {
                    "successful_count": len(successful),
                    "failed_count": len(failed),
                    "successful_images": successful,
                    "failed_images": failed
                }
            }
            self.send_response(response)
            
            self.logger.info(f"Processing completed: {len(successful)} successful, {len(failed)} failed")
            
        except Exception as e:
            self.logger.error(f"Error during processing: {e}")
            self.logger.error(traceback.format_exc())
            
            self.status.is_processing = False
            self.status.error_message = str(e)
            
            error_response = {
                "type": "error",
                "status": asdict(self.status),
                "error": str(e)
            }
            self.send_response(error_response)
    
    def handle_scrape_content(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scrape_content command"""
        try:
            if 'query' not in command:
                return {
                    "success": False,
                    "error": "Missing required parameter: query"
                }

            query = command['query']
            limit = command.get('limit', 10)
            sources = command.get('sources', None)

            # Normalize sources: allow comma-separated string or list
            if isinstance(sources, str):
                sources = [s.strip() for s in sources.split(',') if s.strip()]
            elif sources is not None and not isinstance(sources, list):
                sources = None

            if aggregate_content is None:
                return {
                    "success": False,
                    "error": "Web scraping dependencies not installed. Please install 'requests' and 'feedparser'."
                }

            items = aggregate_content(query=query, limit=limit, sources=sources, logger=self.logger)

            return {
                "success": True,
                "count": len(items),
                "items": items
            }
        except Exception as e:
            self.logger.error(f"Error in handle_scrape_content: {e}")
            self.logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }

    def handle_get_status(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_status command"""
        return {
            "success": True,
            "status": asdict(self.status)
        }
    
    def handle_cancel_processing(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Handle cancel_processing command"""
        try:
            if self.current_aligner:
                self.current_aligner.cancel()
            
            if self.processing_thread and self.processing_thread.is_alive():
                # Set cancellation flag and wait briefly for thread to finish
                self.logger.info("Attempting to cancel processing...")
                self.processing_thread.join(timeout=2.0)
            
            self.status.is_processing = False
            self.status.current_operation = "Cancelled"
            
            return {
                "success": True,
                "message": "Processing cancelled"
            }
            
        except Exception as e:
            self.logger.error(f"Error cancelling processing: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def handle_shutdown(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Handle shutdown command"""
        self.logger.info("Shutdown requested")
        self.should_shutdown = True
        
        # Cancel any ongoing processing
        if self.status.is_processing:
            self.handle_cancel_processing({})
        
        return {
            "success": True,
            "message": "Shutting down"
        }
    
    def process_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single command and return response"""
        try:
            command_type = command.get('command')
            
            if not command_type:
                return {
                    "success": False,
                    "error": "Missing 'command' field"
                }
            
            self.logger.info(f"Processing command: {command_type}")
            
            # Route to appropriate handler
            if command_type == CommandType.PROCESS_IMAGES.value:
                return self.handle_process_images(command)
            elif command_type == CommandType.GET_STATUS.value:
                return self.handle_get_status(command)
            elif command_type == CommandType.CANCEL_PROCESSING.value:
                return self.handle_cancel_processing(command)
            elif command_type == CommandType.SCRAPE_CONTENT.value:
                return self.handle_scrape_content(command)
            elif command_type == CommandType.SHUTDOWN.value:
                return self.handle_shutdown(command)
            else:
                return {
                    "success": False,
                    "error": f"Unknown command: {command_type}"
                }
                
        except Exception as e:
            self.logger.error(f"Error processing command: {e}")
            self.logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }
    
    def run(self):
        """Main service loop - read commands from stdin and send responses to stdout"""
        self.logger.info("Backend service starting...")
        
        try:
            # Send startup confirmation
            self.send_response({
                "type": "startup",
                "success": True,
                "message": "Backend service ready"
            })
            
            # Main command processing loop
            while not self.should_shutdown:
                try:
                    # Read line from stdin
                    line = sys.stdin.readline()
                    
                    if not line:
                        # EOF reached
                        self.logger.info("EOF reached, shutting down")
                        break
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse JSON command
                    try:
                        command = json.loads(line)
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Invalid JSON received: {e}")
                        self.send_response({
                            "success": False,
                            "error": f"Invalid JSON: {str(e)}"
                        })
                        continue
                    
                    # Process command
                    response = self.process_command(command)
                    self.send_response(response)
                    
                except KeyboardInterrupt:
                    self.logger.info("Keyboard interrupt received")
                    break
                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}")
                    self.logger.error(traceback.format_exc())
                    self.send_response({
                        "success": False,
                        "error": str(e)
                    })
            
        except Exception as e:
            self.logger.error(f"Fatal error in service: {e}")
            self.logger.error(traceback.format_exc())
            self.send_response({
                "success": False,
                "error": f"Fatal error: {str(e)}"
            })
        
        finally:
            self.logger.info("Backend service shutting down")


def main():
    """Main entry point"""
    service = BackendService()
    service.run()


if __name__ == "__main__":
    main()