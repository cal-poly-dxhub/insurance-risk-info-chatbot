#!/bin/bash
set -e

# Navigate to the application directory
cd /home/ec2-user/prism/demo

# Activate the virtual environment
source venv/bin/activate

# Start the Streamlit application
nohup streamlit run main.py &

