#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# setup.sh — Full environment setup for Form Automation Project
# Works on: Ubuntu / Debian / Linux Mint / WSL
# ═══════════════════════════════════════════════════════════════

set -e  # Stop on any error

# ── Colors for output ──────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ── Banner ─────────────────────────────────────────
echo -e "${CYAN}"
echo "═══════════════════════════════════════════════════"
echo "   FORM AUTOMATION — ENVIRONMENT SETUP"
echo "═══════════════════════════════════════════════════"
echo -e "${NC}"

# ═══════════════════════════════════════════════════
# STEP 1 — CHECK OS
# ═══════════════════════════════════════════════════
echo -e "${BLUE}[1/8] Checking operating system ...${NC}"

OS_TYPE=""
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_TYPE=$ID
    echo -e "${GREEN}✅ OS detected: $PRETTY_NAME${NC}"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="mac"
    echo -e "${GREEN}✅ OS detected: macOS${NC}"
else
    echo -e "${YELLOW}⚠️  Unknown OS — attempting Linux setup${NC}"
    OS_TYPE="linux"
fi

# ═══════════════════════════════════════════════════
# STEP 2 — INSTALL SYSTEM DEPENDENCIES
# ═══════════════════════════════════════════════════
echo -e "${BLUE}[2/8] Installing system dependencies ...${NC}"

if [[ "$OS_TYPE" == "ubuntu" || "$OS_TYPE" == "debian" || "$OS_TYPE" == "linuxmint" || "$OS_TYPE" == "linux" ]]; then
    sudo apt-get update -qq

    sudo apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        ffmpeg \
        wget \
        curl \
        unzip \
        build-essential \
        libssl-dev \
        libffi-dev \
        libasound2-dev \
        portaudio19-dev

    echo -e "${GREEN}✅ System dependencies installed${NC}"

elif [[ "$OS_TYPE" == "mac" ]]; then
    # Check if brew is installed
    if ! command -v brew &>/dev/null; then
        echo -e "${YELLOW}Installing Homebrew ...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi

    brew install python3 ffmpeg portaudio
    echo -e "${GREEN}✅ Mac dependencies installed${NC}"
fi

# ═══════════════════════════════════════════════════
# STEP 3 — CHECK PYTHON VERSION
# ═══════════════════════════════════════════════════
echo -e "${BLUE}[3/8] Checking Python version ...${NC}"

PYTHON_CMD=""
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}❌ Python not found! Please install Python 3.9+${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✅ Python found: $PYTHON_VERSION ($PYTHON_CMD)${NC}"

# ═══════════════════════════════════════════════════
# STEP 4 — CREATE VIRTUAL ENVIRONMENT
# ═══════════════════════════════════════════════════
echo -e "${BLUE}[4/8] Setting up virtual environment ...${NC}"

VENV_DIR="venv"

if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment already exists — skipping creation${NC}"
else
    $PYTHON_CMD -m venv $VENV_DIR
    echo -e "${GREEN}✅ Virtual environment created: ./$VENV_DIR${NC}"
fi

# ── Activate venv ──────────────────────────────────
source $VENV_DIR/bin/activate
echo -e "${GREEN}✅ Virtual environment activated${NC}"

# ── Upgrade pip ────────────────────────────────────
pip install --upgrade pip setuptools wheel -q
echo -e "${GREEN}✅ pip upgraded${NC}"

# ═══════════════════════════════════════════════════
# STEP 5 — INSTALL PYTORCH (CPU)
# ═══════════════════════════════════════════════════
echo -e "${BLUE}[5/8] Installing PyTorch (CPU version) ...${NC}"
echo -e "${YELLOW}    This may take a few minutes (~500MB) ...${NC}"

pip install torch --index-url https://download.pytorch.org/whl/cpu -q
echo -e "${GREEN}✅ PyTorch installed${NC}"

# ═══════════════════════════════════════════════════
# STEP 6 — INSTALL ALL REQUIREMENTS
# ═══════════════════════════════════════════════════
echo -e "${BLUE}[6/8] Installing Python packages from requirements.txt ...${NC}"

if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ requirements.txt not found!${NC}"
    echo -e "${YELLOW}Make sure you are running this script from the project root folder${NC}"
    exit 1
fi

pip install -r requirements.txt -q
echo -e "${GREEN}✅ All packages installed${NC}"

# ═══════════════════════════════════════════════════
# STEP 7 — INSTALL WHISPER MODEL
# ═══════════════════════════════════════════════════
echo -e "${BLUE}[7/8] Downloading Whisper base model ...${NC}"
echo -e "${YELLOW}    This downloads ~140MB model file ...${NC}"

$PYTHON_CMD -c "
import whisper
print('Downloading Whisper base model ...')
model = whisper.load_model('base')
print('Whisper model ready')
" && echo -e "${GREEN}✅ Whisper model downloaded${NC}" || echo -e "${YELLOW}⚠️  Whisper model download failed — will retry on first run${NC}"

# ═══════════════════════════════════════════════════
# STEP 8 — SETUP PROJECT FOLDERS & ENV FILE
# ═══════════════════════════════════════════════════
echo -e "${BLUE}[8/8] Setting up project folders and config ...${NC}"

# ── Create required folders ────────────────────────
mkdir -p screenshots/errors
mkdir -p screenshots/success
mkdir -p reports
mkdir -p logs
mkdir -p temp_audio

echo -e "${GREEN}✅ Project folders created${NC}"

# ── Create .env if not exists ──────────────────────
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ .env file created from .env.example${NC}"
        echo -e "${YELLOW}⚠️  Please edit .env and add your Google Sheet ID and credentials${NC}"
    else
        echo -e "${YELLOW}⚠️  No .env.example found — creating blank .env${NC}"
        cat > .env << 'EOF'
# ── Google Sheets ──────────────────────────────────
GOOGLE_SHEET_ID=your_google_sheet_id_here
GOOGLE_CREDENTIALS_FILE=credentials.json
SHEET_NAME=Sheet1

# ── Browser ────────────────────────────────────────
HEADLESS=False
BROWSER=chrome
PAGE_LOAD_TIMEOUT=30
ELEMENT_WAIT_TIMEOUT=15

# ── Retry ──────────────────────────────────────────
MAX_RETRIES=3
RETRY_DELAY=2

# ── Paths ──────────────────────────────────────────
SCREENSHOT_DIR=screenshots
RESULTS_CSV=reports/results.csv
EOF
        echo -e "${GREEN}✅ Blank .env created${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  .env already exists — skipping${NC}"
fi

# ── Verify credentials.json ────────────────────────
if [ ! -f "credentials.json" ]; then
    echo -e "${YELLOW}⚠️  credentials.json not found!${NC}"
    echo -e "${YELLOW}   Download it from Google Cloud Console and place it in project root${NC}"
fi

# ═══════════════════════════════════════════════════
# DONE
# ═══════════════════════════════════════════════════
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ SETUP COMPLETE!${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Edit ${CYAN}.env${NC} — add your GOOGLE_SHEET_ID"
echo -e "  2. Add ${CYAN}credentials.json${NC} to project root"
echo -e "  3. Activate venv:  ${CYAN}source venv/bin/activate${NC}"
echo -e "  4. Dry run:        ${CYAN}python main.py --dry-run${NC}"
echo -e "  5. Full run:       ${CYAN}python main.py${NC}"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"