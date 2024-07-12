#!/bin/bash
set -e

# Navigate to the application directory
cd /home/ec2-user/prism/demo

# Check if the Streamlit process is running
if ps -p $(cat streamlit.pid) > /dev/null
then
    echo "Streamlit application is running"
    exit 0
else
    echo "Streamlit application is not running"
    exit 1
fi
