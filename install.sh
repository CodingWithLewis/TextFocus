#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Quick Cuts Installer${NC}"
echo "====================="
echo ""

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
else
    echo -e "${RED}Unsupported OS: $OSTYPE${NC}"
    exit 1
fi

echo "Detected OS: $OS"

# Check for Python 3.8+
echo ""
echo "Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [[ $PYTHON_MAJOR -ge 3 ]] && [[ $PYTHON_MINOR -ge 8 ]]; then
        echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
    else
        echo -e "${RED}Python 3.8+ required, found $PYTHON_VERSION${NC}"
        exit 1
    fi
else
    echo -e "${RED}Python 3 not found. Please install Python 3.8+${NC}"
    exit 1
fi

# Install Tesseract OCR
echo ""
echo "Checking Tesseract OCR..."
if command -v tesseract &> /dev/null; then
    TESS_VERSION=$(tesseract --version 2>&1 | head -1)
    echo -e "${GREEN}✓ $TESS_VERSION${NC}"
else
    echo -e "${YELLOW}Tesseract not found. Installing...${NC}"
    
    if [[ "$OS" == "macos" ]]; then
        if command -v brew &> /dev/null; then
            brew install tesseract
        else
            echo -e "${RED}Homebrew not found. Please install Homebrew first:${NC}"
            echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            exit 1
        fi
    elif [[ "$OS" == "linux" ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y tesseract-ocr
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y tesseract
        elif command -v pacman &> /dev/null; then
            sudo pacman -S tesseract
        else
            echo -e "${RED}Could not detect package manager. Please install Tesseract manually.${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✓ Tesseract installed${NC}"
fi

# Install Python package
echo ""
echo "Installing Quick Cuts..."

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Install with pip
pip3 install -e "$SCRIPT_DIR" --quiet

echo -e "${GREEN}✓ Quick Cuts installed${NC}"

# Add to PATH if needed
PIP_BIN=$(python3 -c "import site; print(site.USER_BASE)")/bin

if ! command -v quick-cuts &> /dev/null; then
    # Determine shell config file
    if [[ "$SHELL" == *"zsh"* ]]; then
        SHELL_RC="$HOME/.zshrc"
    else
        SHELL_RC="$HOME/.bashrc"
    fi
    
    # Check if already in rc file
    if ! grep -q "$PIP_BIN" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# Added by Quick Cuts installer" >> "$SHELL_RC"
        echo "export PATH=\"$PIP_BIN:\$PATH\"" >> "$SHELL_RC"
        echo -e "${GREEN}✓ Added $PIP_BIN to $SHELL_RC${NC}"
    fi
    
    # Add to current session
    export PATH="$PIP_BIN:$PATH"
fi

echo ""
echo -e "${GREEN}✓ Installation complete!${NC}"
echo ""
echo "Usage:"
echo "  quick-cuts                              # Interactive mode"
echo "  quick-cuts fetch \"keyword\" -n 10        # Download images"
echo "  quick-cuts align input/ -w \"word\"       # Align images"
echo ""

# Check if running with source
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo -e "${YELLOW}Run 'source ~/.zshrc' or open a new terminal to use quick-cuts${NC}"
else
    echo "Try it now: quick-cuts"
fi
