#!/bin/bash
# Install script for planet-power-law-distribution
# Usage: curl -fsSL <link-to-script-on-github> | bash
# Or: bash install.sh [repo-url] [install-dir]

set -e

REPO_URL="${1:-https://github.com/cory/planet-power-law-distribution}"
INSTALL_DIR="${2:-$HOME/planet-power-law-distribution}"

echo "=== planet-power-law-distribution installer ==="
echo "Repo: $REPO_URL"
echo "Install dir: $INSTALL_DIR"
echo ""

# Check for git
if ! command -v git &>/dev/null; then
	echo "Error: git is required but not installed."
	echo "Please install git and try again."
	exit 1
fi

# Check for python
if ! command -v python3 &>/dev/null; then
	echo "Error: Python 3 is required but not installed."
	echo "Please install Python 3 and try again."
	exit 1
fi

# Check python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Found Python $PYTHON_VERSION"

# Check for pip
if ! command -v pip3 &>/dev/null && ! python3 -m pip --version &>/dev/null; then
	echo "Error: pip is required but not installed."
	echo "Please install pip and try again."
	exit 1
fi

# Clone or update repository
if [ -d "$INSTALL_DIR/.git" ]; then
	echo "Updating existing installation..."
	cd "$INSTALL_DIR"
	git pull
else
	echo "Cloning repository..."
	git clone "$REPO_URL" "$INSTALL_DIR"
	cd "$INSTALL_DIR"
fi

# Create virtual environment
if [ -d ".venv" ]; then
	echo "Updating virtual environment..."
	rm -rf .venv
fi

echo "Creating virtual environment..."
python3 -m venv .venv

# Activate venv
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -e .

echo ""
echo "=== Installation complete! ==="
echo "To activate the environment, run: source .venv/bin/activate"
echo "To run the tool, use: planet-power"
echo ""
echo "Or activate and run in one command:"
echo "  . .venv/bin/activate && planet-power --help"
