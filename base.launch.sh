#!/bin/bash

# Exit on error
set -e

# Check if debug mode is requested
DEBUG=""
if [ "$1" = "--debug" ] || [ "$1" = "-d" ]; then
    DEBUG="debug:=true"
    echo "Debug mode enabled"
fi

# Source ROS 2 environment
source /opt/ros/$(ls /opt/ros)/setup.bash

# Assuming the workspace is in the user's home directory
# Change this path if your workspace is elsewhere
WS_DIR="$ROS2_SMARTY_WORKSPACE_DIR"

echo "Sourcing ROS 2 workspace..."
if [ -f "$WS_DIR/install/setup.bash" ]; then
    source "$WS_DIR/install/setup.bash"
else
    echo "Error: ROS 2 workspace not found at $WS_DIR"
    echo "Installing workspace dependencies..."
    cd "$WS_DIR"
    rosdep install --from-paths src --ignore-src -r -y

    echo "Building workspace..."
    colcon build --symlink-install

    # Source the workspace after building
    source "$WS_DIR/install/setup.bash"
fi
echo "Sourcing workspace complete."
echo "Launching nodes..."

# Launch all required nodes
ros2 launch camera_preprocessing camera_preprocessing.launch.py $DEBUG &
CAMERA_PID=$!

# Wait a bit for camera to start
sleep 2

ros2 launch lane_detection_ai lane_detection_ai.launch.py $DEBUG &
LANE_PID=$!

ros2 launch pathplanning pathplanning.launch.py $DEBUG &
PATH_PID=$!

ros2 launch pose_estimation pose_estimation.launch.py $DEBUG &
POSE_PID=$!

# Wait for all processes to complete (or Ctrl+C)
wait $CAMERA_PID $LANE_PID $PATH_PID $POSE_PID
