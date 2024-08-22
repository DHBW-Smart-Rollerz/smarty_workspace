#!/bin/bash

set -e

# Setup workspace
mkdir -p ros2_ws/src/workingdir
# cp -r $GITHUB_WORKSPACE ros2_ws/src/workingdir

# Clone dependencies
repos_file=$(find * -maxdepth 2 -name dependencies.repos)
if [ -z "$repos_file" ]; then
    echo "No dependencies.repos file found"
else
    echo "Cloning dependencies defined in $repos_file"
    vcs import < "$repos_file" ros2_ws/src
fi

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
find ros2_ws/src/* -maxdepth 3 -name requirements.txt -exec pip install -r {} \;

# Build the workspace
cd ros2_ws
ls -la src
colcon build --symlink-install --event-handlers console_direct+
