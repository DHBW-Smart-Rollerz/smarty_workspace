# Use the official ROS 2 base image
ARG ROS_DISTRO=jazzy
FROM osrf/ros:${ROS_DISTRO}-desktop

# Install necessary packages
RUN apt-get update && apt-get install -y \
    python3-venv \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /workspace

# Copy the entire GitHub workspace into the Docker container
COPY . /workspace

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
