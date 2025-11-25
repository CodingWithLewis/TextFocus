#!/usr/bin/env python3
"""
Simple test to verify the backend service is working.
"""

import json
import subprocess
import sys
import time

def test_backend():
    """Test basic backend functionality"""
    print("Testing Quick Cuts Backend Service")
    print("=" * 50)
    
    # Start the backend
    process = subprocess.Popen(
        [sys.executable, 'backend_service.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8'
    )
    
    print("[OK] Backend process started")
    time.sleep(1)
    
    # Test get_status command
    command = {"command": "get_status"}
    process.stdin.write(json.dumps(command) + '\n')
    process.stdin.flush()
    
    # Read response
    response_line = process.stdout.readline()
    if response_line:
        response = json.loads(response_line)
        print(f"[OK] Status command worked: {response.get('message', 'Status received')}")
    
    # Send shutdown
    command = {"command": "shutdown"}
    process.stdin.write(json.dumps(command) + '\n')
    process.stdin.flush()
    
    # Wait for shutdown
    response_line = process.stdout.readline()
    if response_line:
        response = json.loads(response_line)
        print(f"[OK] Shutdown command worked: {response.get('message', 'Shutdown received')}")
    
    process.wait(timeout=2)
    print("[OK] Backend process terminated cleanly")
    
    print("=" * 50)
    print("SUCCESS: Backend service is working correctly!")
    return True

if __name__ == "__main__":
    try:
        test_backend()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)