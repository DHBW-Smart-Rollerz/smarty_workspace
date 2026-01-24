#!/bin/bash
### ROS

source /opt/ros/jazzy/setup.zsh
export ROS2_SMARTY_WORKSPACE_DIR="/home/$USER/smarty_workspace"
source $ROS2_SMARTY_WORKSPACE_DIR/install/setup.sh
export PYTHON_EXECUTABLE="/home/$USER/.pyenv/versions/default/bin/python3"
pyenv activate default

### Camera
export GENICAM_GENTL64_PATH=$GENICAM_GENTL64_PATH:"/home/smartrollerz/Documents/VimbaX_2024-1/cti"

# Exit on error
set -e

# sleep 30
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
if [ -f "$WS_DIR/install/setup.sh" ]; then
    source "$WS_DIR/install/setup.sh"
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
ros2 launch vimbax_camera vimbax_camera.launch.py &
CPI=$!

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

ros2 run querregelung querregelung &
QUERREGELUNG=$!

ros2 topic pub /control/active std_msgs/Bool "{data: 1}" &
QACTIVE=$!


ros2 run uart uart_publisher &
UART_P=$!

ros2 run uart uart_subscriber &
UART_S=$!

ros2 launch state_machine state_machine.launch.py $DEBUG &
sm=$!

ros2 launch object_detection object_detection.launch.py $DEBUG &
od=$!

# Wait for all processes to complete (or Ctrl+C)
wait $od $CPI $CAMERA_PID $LANE_PID $PATH_PID $POSE_PID $QUERREGELUNG $QACTIVE $UART_P $UART_S $sm
