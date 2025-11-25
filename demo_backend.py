#!/usr/bin/env python3
"""
Demo script showing how to use the Quick Cuts backend service.
This simulates how an Electron app would communicate with the backend.
"""

import json
import subprocess
import sys
import time
import threading
from pathlib import Path


class BackendDemo:
    """Simple demo client for the Quick Cuts backend service"""
    
    def __init__(self):
        self.process = None
        self.running = False
    
    def start_backend(self):
        """Start the backend service"""
        print("Starting Quick Cuts backend service...")
        
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
        
        # Start output reader thread
        self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self.reader_thread.start()
        
        # Wait for startup confirmation
        time.sleep(1)
        print("Backend service started!")
    
    def _read_output(self):
        """Read and display output from backend"""
        while self.running and self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if line:
                    try:
                        response = json.loads(line.strip())
                        self._handle_response(response)
                    except json.JSONDecodeError:
                        print(f"Invalid JSON: {line}")
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f"Error reading output: {e}")
                break
    
    def _handle_response(self, response):
        """Handle different types of responses"""
        response_type = response.get('type', 'command_response')
        
        if response_type == 'startup':
            print("[OK] Backend ready!")
        elif response_type == 'progress':
            status = response['status']
            current = status.get('current_image', 0)
            total = status.get('total_images', 0)
            operation = status.get('current_operation', '')
            print(f"Progress: {current}/{total} - {operation}")
        elif response_type == 'completed':
            results = response.get('results', {})
            successful = results.get('successful_count', 0)
            failed = results.get('failed_count', 0)
            print(f"[OK] Processing completed! {successful} successful, {failed} failed")
        elif response_type == 'error':
            error = response.get('error', 'Unknown error')
            print(f"[ERROR] {error}")
        else:
            # Regular command response
            if response.get('success'):
                message = response.get('message', 'Command executed successfully')
                print(f"[OK] {message}")
            else:
                error = response.get('error', 'Command failed')
                print(f"[ERROR] {error}")
    
    def send_command(self, command):
        """Send a command to the backend"""
        if not self.process:
            print("Backend not started!")
            return
        
        try:
            command_json = json.dumps(command)
            print(f"\nSending command: {command['command']}")
            self.process.stdin.write(command_json + '\n')
            self.process.stdin.flush()
            time.sleep(0.5)  # Give time for response
        except Exception as e:
            print(f"Error sending command: {e}")
    
    def demo_basic_commands(self):
        """Demonstrate basic commands"""
        print("\n" + "="*50)
        print("DEMO: Basic Commands")
        print("="*50)
        
        # Get status
        self.send_command({"command": "get_status"})
        
        # Test invalid command
        self.send_command({"command": "invalid_command"})
        
        # Test cancellation (even though nothing is running)
        self.send_command({"command": "cancel_processing"})
    
    def demo_processing_validation(self):
        """Demonstrate processing command validation"""
        print("\n" + "="*50)
        print("DEMO: Processing Command Validation")
        print("="*50)
        
        # Missing required parameters
        print("\n--- Testing missing parameters ---")
        self.send_command({
            "command": "process_images",
            "target_word": "test"
            # Missing image_paths and output_dir
        })
        
        # Invalid image paths
        print("\n--- Testing invalid image paths ---")
        self.send_command({
            "command": "process_images",
            "target_word": "test",
            "image_paths": ["/nonexistent/image1.jpg", "/fake/image2.png"],
            "output_dir": "./demo_output"
        })
    
    def shutdown(self):
        """Shutdown the backend service"""
        print("\n" + "="*50)
        print("DEMO: Shutdown")
        print("="*50)
        
        self.send_command({"command": "shutdown"})
        
        self.running = False
        
        if self.process:
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait()
        
        print("[OK] Backend service stopped")
    
    def run_demo(self):
        """Run the complete demo"""
        try:
            print("Quick Cuts Backend Service Demo")
            print("="*50)
            
            # Start backend
            self.start_backend()
            
            # Run demos
            self.demo_basic_commands()
            self.demo_processing_validation()
            
            # Shutdown
            self.shutdown()
            
        except KeyboardInterrupt:
            print("\nDemo interrupted by user")
            self.shutdown()
        except Exception as e:
            print(f"Demo error: {e}")
            self.shutdown()


def main():
    """Main demo function"""
    demo = BackendDemo()
    demo.run_demo()


if __name__ == "__main__":
    main()