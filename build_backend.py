#!/usr/bin/env python3
"""
Build script for creating the Quick Cuts backend executable using PyInstaller.
"""

import subprocess
import sys
import shutil
from pathlib import Path


def check_dependencies():
    """Check if all required dependencies are installed"""
    print("Checking dependencies...")
    
    required_modules = [
        'cv2', 'numpy', 'pytesseract', 'sklearn', 'PIL', 'PyInstaller'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"  [OK] {module}")
        except ImportError:
            missing.append(module)
            print(f"  [MISSING] {module}")
    
    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}")
        print("Install with: pip install -r requirements-backend.txt")
        return False
    
    print("All dependencies available!")
    return True


def clean_build():
    """Clean previous build artifacts"""
    print("\nCleaning previous build artifacts...")
    
    paths_to_clean = ['build', 'dist', '__pycache__']
    
    for path in paths_to_clean:
        if Path(path).exists():
            if Path(path).is_dir():
                shutil.rmtree(path)
                print(f"  Removed directory: {path}")
            else:
                Path(path).unlink()
                print(f"  Removed file: {path}")


def build_executable():
    """Build the executable using PyInstaller"""
    print("\nBuilding executable with PyInstaller...")
    
    # Use the spec file for consistent builds
    spec_file = "backend_service.spec"
    
    if not Path(spec_file).exists():
        print(f"Error: {spec_file} not found!")
        return False
    
    try:
        # Run PyInstaller
        result = subprocess.run([
            sys.executable, '-m', 'PyInstaller',
            '--clean',  # Clean cache and remove temp files
            spec_file
        ], check=True, capture_output=True, text=True)
        
        print("Build completed successfully!")
        print(f"Executable created: dist/quick_cuts_backend.exe")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def test_executable():
    """Test the built executable"""
    print("\nTesting built executable...")
    
    exe_path = Path("dist/quick_cuts_backend.exe")
    
    if not exe_path.exists():
        print("Error: Executable not found!")
        return False
    
    try:
        # Test with a simple command
        result = subprocess.run([
            str(exe_path)
        ], input='{"command": "get_status"}\n{"command": "shutdown"}\n',
        capture_output=True, text=True, timeout=10)
        
        # Check if it produced expected output
        if '"success": true' in result.stdout and '"type": "startup"' in result.stdout:
            print("  [OK] Executable test passed!")
            return True
        else:
            print("  [ERROR] Executable test failed!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("  [ERROR] Executable test timed out!")
        return False
    except Exception as e:
        print(f"  [ERROR] Executable test failed: {e}")
        return False


def main():
    """Main build process"""
    print("Quick Cuts Backend Build Script")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Clean previous builds
    clean_build()
    
    # Build executable
    if not build_executable():
        return False
    
    # Test executable
    if not test_executable():
        print("\nWarning: Executable test failed, but build completed.")
        print("You may want to test manually.")
    
    print("\n" + "=" * 50)
    print("Build process completed!")
    print("Executable location: dist/quick_cuts_backend.exe")
    print("\nTo test manually:")
    print('  echo \'{"command": "get_status"}\' | dist/quick_cuts_backend.exe')
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)