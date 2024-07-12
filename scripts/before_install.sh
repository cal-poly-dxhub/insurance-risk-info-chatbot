#!/bin/bash
set -e

# Update the system
sudo yum update -y

# Install Python 3 and pip if not already installed
sudo yum install -y python3 python3-pip

# Install virtualenv using pip
sudo python3 -m pip install virtualenv

echo "Installation of system packages and virtualenv complete."
