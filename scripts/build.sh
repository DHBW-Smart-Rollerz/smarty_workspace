#!/bin/bash
set -e


# Set the default build type
BUILD_TYPE=RelWithDebInfo

# Check if the user has provided a package name
if [ "$#" -gt 0 ]; then
    colcon build \
    --symlink-install \
    --cmake-args "-DCMAKE_BUILD_TYPE=$BUILD_TYPE" "-DCMAKE_EXPORT_COMPILE_COMMANDS=On" \
    -Wall -Wextra -Wpedantic --packages-select "$@"
else
    colcon build \
    --symlink-install \
    --cmake-args "-DCMAKE_BUILD_TYPE=$BUILD_TYPE" "-DCMAKE_EXPORT_COMPILE_COMMANDS=On" \
    -Wall -Wextra -Wpedantic
fi
