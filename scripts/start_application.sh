#!/bin/bash
set -e

# Navigate to the application directory
cd /home/ec2-user/prism/demo

# Activate the virtual environment
source venv/bin/activate

# Kill any existing Streamlit processes
pkill -f "streamlit run main.py" || true

# Start the Streamlit application
nohup streamlit run main.py > streamlit.log 2>&1 &

# Save the PID of the Streamlit process
echo $! > streamlit.pid

# Wait for a short time to ensure Streamlit has started
sleep 10

# Check if Streamlit is running
if ps -p $(cat streamlit.pid) > /dev/null
then
    echo "Streamlit application started successfully"
    exit 0
else
    echo "Failed to start Streamlit application"
    exit 1
fi

# Note: The virtual environment will be deactivated when the script exits
