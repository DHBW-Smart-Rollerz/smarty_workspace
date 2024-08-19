#!/bin/bash

sudo apt-get update
sudo rosdep init
rosdep update --rosdistro=$ROS_DISTRO
rosdep install --from-paths src --ignore-src -y --rosdistro=$ROS_DISTRO
