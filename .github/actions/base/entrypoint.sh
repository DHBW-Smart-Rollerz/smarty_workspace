#!/bin/bash

set -e

# Setup workspace
# mkdir -p ros2_ws/src/workingdir
# cp -r $GITHUB_WORKSPACE ros2_ws/src/workingdir

# Clone dependencies
vcs import ros2_ws/src < $(find workspace/* -maxdepth 2 -name dependencies.repos)

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
find ros2_ws/src/* -maxdepth 3 -name requirements.txt -exec pip install -r {} \;

# Build the workspace
cd ros2_ws
colcon build --symlink-install
