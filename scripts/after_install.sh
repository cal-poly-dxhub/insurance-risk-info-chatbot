#!/bin/bash
set -e

# Navigate to the application directory
cd /home/ec2-user/prism/demo

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
pip install --ignore-installed -r requirements.txt -v

# Deactivate the virtual environment
deactivate

echo "Installation complete."
