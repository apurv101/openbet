#!/bin/bash

# Openbet Setup Script

echo "Setting up Openbet..."

# Check if Python 3.10+ is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file with your API credentials:"
    echo "   - KALSHI_API_KEY and KALSHI_API_SECRET"
    echo "   - ANTHROPIC_API_KEY (for Claude)"
    echo "   - OPENAI_API_KEY (for OpenAI)"
    echo "   - XAI_API_KEY (for Grok)"
    echo ""
fi

# Create data directory
echo "Creating data directory..."
mkdir -p data

# Install package in development mode
echo "Installing Openbet in development mode..."
pip install -e .

echo ""
echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your API credentials"
echo "2. Activate the virtual environment: source venv/bin/activate"
echo "3. Run: openbet --help"
echo ""
