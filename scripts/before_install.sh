#!/bin/bash
set -e

# Update the system
sudo yum update -y

# Install Python 3 and pip if not already installed
sudo yum install -y python3 python3-pip

# Install venv module
sudo yum install -y python3-venv
