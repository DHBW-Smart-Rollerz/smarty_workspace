#!/bin/bash
set -e

WORKSPACE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"

sudo apt update
sudo rosdep init || echo "rosdep is already initilized. The above error can be ignored."
rosdep update --rosdistro=$ROS_DISTRO
rosdep install --from-paths "$WORKSPACE_DIR/src" --ignore-src -y --rosdistro=$ROS_DISTRO
