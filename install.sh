#!/bin/bash

# --- Colors ---
RED='\033[91m'
GRN='\033[92m'
YEL='\033[93m'
CYN='\033[96m'
BLD='\033[1m'
DIM='\033[90m'
RST='\033[0m'

echo ""
echo -e "  ${CYN}============================================${RST}"
echo -e "  ${BLD}     LiteWing Library Installer${RST}"
echo -e "  ${CYN}============================================${RST}"
echo ""

# --- Detect OS ---
OS="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="mac"
elif [[ "$OSTYPE" == "linux"* ]]; then
    OS="linux"
fi

# =========================================
#  STEP 1: Verify System Date and Time
# =========================================
echo -e "  ${BLD}[Step 1/3]${RST} System date and time:"
echo ""
echo -e "           ${BLD}$(date '+%Y-%m-%d  %H:%M:%S')${RST}"
echo ""
echo -e "  ${YEL}Make sure the above date and time is correct!${RST}"
echo -e "  ${DIM}Wrong date/time will cause download errors${RST}"
echo ""

# =========================================
#  STEP 2: Check / Install Python 3.11
# =========================================
echo -e "  ${BLD}[Step 2/3]${RST} Checking for Python 3.11..."

PY311_CMD=""

# Method 1: python3.11 command
if command -v python3.11 &>/dev/null; then
    PY311_CMD="python3.11"
fi

# Method 2: python3 command (check version)
if [ -z "$PY311_CMD" ] && command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version 2>&1 | grep -o '3\.11\.[0-9]*')
    if [ -n "$PY_VER" ]; then
        PY311_CMD="python3"
    fi
fi

# Method 3: Install Python 3.11
if [ -z "$PY311_CMD" ]; then
    echo -e "  ${YEL}[!] Python 3.11 not found. Installing...${RST}"
    echo ""

    if [ "$OS" == "mac" ]; then
        # macOS: use Homebrew
        if ! command -v brew &>/dev/null; then
            echo -e "  ${YEL}[!] Homebrew not found. Installing Homebrew first...${RST}"
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            if [ $? -ne 0 ]; then
                echo -e "  ${RED}[ERROR] Homebrew installation failed!${RST}"
                echo "  Install manually: https://brew.sh"
                exit 1
            fi
            # Add Homebrew to PATH for this session
            if [ -f /opt/homebrew/bin/brew ]; then
                eval "$(/opt/homebrew/bin/brew shellenv)"
            elif [ -f /usr/local/bin/brew ]; then
                eval "$(/usr/local/bin/brew shellenv)"
            fi
        fi
        echo "  Installing Python 3.11 via Homebrew..."
        brew install python@3.11
        if [ $? -ne 0 ]; then
            echo -e "  ${RED}[ERROR] Python installation failed!${RST}"
            echo "  Try manually: brew install python@3.11"
            exit 1
        fi
        PY311_CMD="python3.11"

    elif [ "$OS" == "linux" ]; then
        # Linux: use apt (Ubuntu/Debian) or dnf (Fedora)
        if command -v apt &>/dev/null; then
            echo "  Installing Python 3.11 via apt..."
            sudo apt update -qq
            sudo apt install -y software-properties-common
            sudo add-apt-repository -y ppa:deadsnakes/ppa
            sudo apt update -qq
            sudo apt install -y python3.11 python3.11-venv python3.11-distutils python3-pip
        elif command -v dnf &>/dev/null; then
            echo "  Installing Python 3.11 via dnf..."
            sudo dnf install -y python3.11
        elif command -v pacman &>/dev/null; then
            echo "  Installing Python 3.11 via pacman..."
            sudo pacman -S --noconfirm python
        else
            echo -e "  ${RED}[ERROR] Could not detect package manager!${RST}"
            echo "  Please install Python 3.11 manually:"
            echo "    https://www.python.org/downloads/release/python-3119/"
            exit 1
        fi

        if [ $? -ne 0 ]; then
            echo -e "  ${RED}[ERROR] Python installation failed!${RST}"
            echo ""
            echo "  Possible causes:"
            echo "    - No internet connection"
            echo -e "    - System date/time is wrong - causes SSL errors"
            exit 1
        fi
        PY311_CMD="python3.11"
    else
        echo -e "  ${RED}[ERROR] Unsupported OS: $OSTYPE${RST}"
        echo "  Please install Python 3.11 manually:"
        echo "    https://www.python.org/downloads/release/python-3119/"
        exit 1
    fi

    echo -e "  ${GRN}[OK] Python 3.11 installed!${RST}"
    echo ""
fi

# Verify Python is available
if ! command -v $PY311_CMD &>/dev/null; then
    echo -e "  ${RED}[ERROR] Python 3.11 command not found after install!${RST}"
    echo "  Try opening a new terminal and running this script again."
    exit 1
fi

echo -e "  ${GRN}[OK]${RST} Python: $PY311_CMD"
echo -e "       ${DIM}$($PY311_CMD --version 2>&1)${RST}"
echo ""

# =========================================
#  STEP 3: Install LiteWing Library
# =========================================
echo -e "  ${BLD}[Step 3/3]${RST} Installing LiteWing library..."
echo -e "  ${DIM}Downloads cflib + matplotlib = may take a few minutes${RST}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Ensure pip is available
if ! $PY311_CMD -m pip --version &>/dev/null; then
    echo -e "  ${DIM}Setting up pip...${RST}"
    $PY311_CMD -m ensurepip --upgrade 2>/dev/null
    if ! $PY311_CMD -m pip --version &>/dev/null; then
        echo -e "  ${YEL}[!] pip not found, installing via get-pip.py...${RST}"
        curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
        $PY311_CMD /tmp/get-pip.py 2>/dev/null
        rm -f /tmp/get-pip.py
    fi
    if ! $PY311_CMD -m pip --version &>/dev/null; then
        echo -e "  ${RED}[ERROR] Could not install pip!${RST}"
        echo "  Try: sudo apt install python3-pip"
        exit 1
    fi
fi

$PY311_CMD -m pip install --upgrade pip 2>/dev/null
$PY311_CMD -m pip install "$SCRIPT_DIR"

if [ $? -ne 0 ]; then
    echo ""
    echo -e "  ${RED}[ERROR] LiteWing installation failed!${RST}"
    echo ""
    echo "  Possible causes:"
    echo "    - No internet connection"
    echo -e "    - System date/time is wrong - causes SSL errors"
    echo -e "      ${YEL}Fix your system date/time and try again${RST}"
    echo ""
    echo "  Try manually: $PY311_CMD -m pip install $SCRIPT_DIR --verbose"
    echo ""
    exit 1
fi

# =========================================
#  Verify
# =========================================
echo ""
$PY311_CMD -c "from litewing import LiteWing; print('  \033[92m[OK] LiteWing library imported successfully!\033[0m')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "  ${YEL}[WARN] LiteWing installed but import check failed.${RST}"
fi

echo ""
echo -e "  ${GRN}============================================${RST}"
echo -e "  ${GRN}${BLD}       Installation Complete!  ${RST}"
echo -e "  ${GRN}============================================${RST}"
echo ""
echo -e "  ${GRN}[OK]${RST} Python 3.11"
echo -e "  ${GRN}[OK]${RST} LiteWing library"
echo -e "  ${GRN}[OK]${RST} cflib + matplotlib"
echo ""
echo -e "  ${BLD}To fly your drone:${RST}"
echo "    1. Turn on the drone"
echo "    2. Connect to the drone's WiFi network"
echo -e "    3. Run: ${CYN}$PY311_CMD examples/level_1/01_battery_voltage.py${RST}"
echo ""
