#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS2_SMARTY_WORKSPACE_DIR="/home/smarty/smarty_workspace"
source $ROS2_SMARTY_WORKSPACE_DIR/install/setup.bash
export PYTHON_EXECUTABLE="/home/$USER/.pyenv/versions/default/bin/python3"


# Script to launch multiple ROS 2 nodes in separate terminals
# Save this file as ~/ros2_startup.sh and make it executable with:
# chmod +x ~/ros2_startup.sh

# Define the working directory
WORKSPACE_DIR="/home/smartrollerz/smarty_workspace"

# Array of commands to execute
commands=(
    "ros2 launch vimbax_camera vimbax_camera.launch.py"
    "ros2 launch camera_preprocessing camera_preprocessing.launch.py"
    "ros2 launch lane_detection_ai lane_detection_ai.launch.py"
    "ros2 launch pathplanning pathplanning.launch.py"
    "ros2 launch pose_estimation pose_estimation.launch.py"
    "ros2 launch state_machine state_machine.launch.py"
    "ros2 run querregelung querregelung"
    "ros2 run uart uart_publisher"
    "ros2 run uart uart_subscriber"
    "ros2 topic pub /control/active std_msgs/Bool '{data: 1}'"
    "ros2 launch object_detection object_detection.launch.py"
)

# Check if gnome-terminal is installed (common on Ubuntu)
if command -v gnome-terminal &> /dev/null; then
    # For each command, open a new gnome-terminal window
    for cmd in "${commands[@]}"; do
        gnome-terminal -- bash -c "cd $WORKSPACE_DIR && $cmd; exec bash"
        # Small delay to prevent terminal windows from stacking exactly on top of each other
        sleep 2
    done
# Check if xterm is installed (fallback)
elif command -v xterm &> /dev/null; then
    # For each command, open a new xterm window
    for cmd in "${commands[@]}"; do
        xterm -e "cd $WORKSPACE_DIR && $cmd; exec bash" &
        sleep 0.5
    done
else
    echo "Error: Neither gnome-terminal nor xterm is installed."
    echo "Please install one of them with:"
    echo "sudo apt install gnome-terminal"
    echo "or"
    echo "sudo apt install xterm"
    exit 1
fi

echo "All ROS 2 nodes launched in separate terminals."
