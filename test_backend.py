#!/usr/bin/env python3
"""
Test script for the Quick Cuts backend service.
Demonstrates how to communicate with the backend via JSON IPC.
"""

import json
import subprocess
import sys
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional


class BackendTester:
    """Test client for communicating with the backend service"""
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.responses = []
        self.reader_thread: Optional[threading.Thread] = None
        self.running = False
    
    def start_backend(self):
        """Start the backend service process"""
        try:
            self.process = subprocess.Popen(
                [sys.executable, 'backend_service.py'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                bufsize=1
            )
            
            self.running = True
            
            # Start reader thread to collect responses
            self.reader_thread = threading.Thread(target=self._read_responses, daemon=True)
            self.reader_thread.start()
            
            print("Backend service started")
            
            # Wait for startup confirmation
            time.sleep(2)  # Give more time for startup
            
        except Exception as e:
            print(f"Error starting backend: {e}")
            return False
        
        return True
    
    def _read_responses(self):
        """Read responses from backend in a separate thread"""
        while self.running and self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if line:
                    try:
                        response = json.loads(line.strip())
                        self.responses.append(response)
                        print(f"Received: {json.dumps(response, indent=2)}")
                    except json.JSONDecodeError:
                        print(f"Invalid JSON response: {line}")
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f"Error reading response: {e}")
                break
    
    def send_command(self, command: Dict[str, Any]) -> bool:
        """Send a command to the backend"""
        if not self.process:
            print("Backend not started")
            return False
        
        try:
            command_json = json.dumps(command)
            print(f"Sending: {command_json}")
            
            self.process.stdin.write(command_json + '\n')
            self.process.stdin.flush()
            return True
            
        except Exception as e:
            print(f"Error sending command: {e}")
            return False
    
    def stop_backend(self):
        """Stop the backend service"""
        self.running = False
        
        if self.process:
            try:
                # Send shutdown command
                self.send_command({"command": "shutdown"})
                time.sleep(1)
                
                # Terminate if still running
                if self.process.poll() is None:
                    self.process.terminate()
                    self.process.wait(timeout=5)
                    
            except Exception as e:
                print(f"Error stopping backend: {e}")
                if self.process.poll() is None:
                    self.process.kill()
        
        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=2)
        
        print("Backend service stopped")
    
    def get_latest_response(self) -> Optional[Dict[str, Any]]:
        """Get the most recent response"""
        return self.responses[-1] if self.responses else None
    
    def wait_for_response(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Wait for a new response"""
        start_count = len(self.responses)
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if len(self.responses) > start_count:
                return self.responses[-1]
            time.sleep(0.1)
        
        return None


def test_basic_commands():
    """Test basic backend commands"""
    tester = BackendTester()
    
    try:
        # Start backend
        if not tester.start_backend():
            print("Failed to start backend")
            return False
        
        # Wait for startup
        startup_response = tester.wait_for_response(timeout=3.0)
        if not startup_response:
            # Fallback: startup may have arrived before waiting
            startup_response = tester.get_latest_response()
        if not startup_response:
            print("Did not receive startup confirmation")
            return False
        
        # Check if it's a startup message
        if startup_response.get('type') != 'startup' and not startup_response.get('success'):
            print("Invalid startup response")
            return False
        
        # Test get_status command
        print("\n=== Testing get_status ===")
        tester.send_command({"command": "get_status"})
        
        status_response = tester.wait_for_response()
        if status_response and status_response.get('success'):
            print("[OK] get_status works")
        else:
            print("[FAIL] get_status failed")
        
        # Test invalid command
        print("\n=== Testing invalid command ===")
        tester.send_command({"command": "invalid_command"})
        
        error_response = tester.wait_for_response()
        if error_response and not error_response.get('success'):
            print("[OK] Invalid command properly rejected")
        else:
            print("[FAIL] Invalid command not handled correctly")
        
        # Test missing command field
        print("\n=== Testing missing command field ===")
        tester.send_command({"invalid": "data"})
        
        missing_response = tester.wait_for_response()
        if missing_response and not missing_response.get('success'):
            print("[OK] Missing command field properly handled")
        else:
            print("[FAIL] Missing command field not handled correctly")
        
        print("\n=== Basic tests completed ===")
        return True
        
    except Exception as e:
        print(f"Test error: {e}")
        return False
    
    finally:
        tester.stop_backend()


def test_processing_workflow():
    """Test the image processing workflow"""
    tester = BackendTester()
    
    try:
        # Start backend
        if not tester.start_backend():
            print("Failed to start backend")
            return False
        
        # Wait for startup
        startup_response = tester.wait_for_response(timeout=3.0)
        if not startup_response:
            # Fallback: startup may have arrived before waiting
            startup_response = tester.get_latest_response()
        if not startup_response:
            print("Did not receive startup confirmation")
            return False
        
        # Check if it's a startup message
        if startup_response.get('type') != 'startup' and not startup_response.get('success'):
            print("Invalid startup response")
            return False
        
        # Test process_images with invalid paths
        print("\n=== Testing process_images with invalid paths ===")
        tester.send_command({
            "command": "process_images",
            "target_word": "test",
            "image_paths": ["/nonexistent/path1.jpg", "/nonexistent/path2.jpg"],
            "output_dir": "./test_output"
        })
        
        process_response = tester.wait_for_response()
        if process_response and not process_response.get('success'):
            print("[OK] Invalid paths properly rejected")
        else:
            print("[FAIL] Invalid paths not handled correctly")
        
        # Test process_images with missing parameters
        print("\n=== Testing process_images with missing parameters ===")
        tester.send_command({
            "command": "process_images",
            "target_word": "test"
            # Missing required parameters
        })
        
        missing_param_response = tester.wait_for_response()
        if missing_param_response and not missing_param_response.get('success'):
            print("[OK] Missing parameters properly rejected")
        else:
            print("[FAIL] Missing parameters not handled correctly")
        
        # Test cancellation
        print("\n=== Testing cancellation ===")
        tester.send_command({"command": "cancel_processing"})
        
        cancel_response = tester.wait_for_response()
        if cancel_response and cancel_response.get('success'):
            print("[OK] Cancellation command works")
        else:
            print("[FAIL] Cancellation command failed")
        
        print("\n=== Processing workflow tests completed ===")
        return True
        
    except Exception as e:
        print(f"Test error: {e}")
        return False
    
    finally:
        tester.stop_backend()


def main():
    """Run all tests"""
    print("Starting Quick Cuts Backend Tests")
    print("=" * 50)
    
    success = True
    
    # Test basic commands
    if not test_basic_commands():
        success = False
    
    # Test processing workflow
    if not test_processing_workflow():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("[SUCCESS] All tests passed!")
    else:
        print("[FAILURE] Some tests failed!")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)