#!/bin/bash
set -e

# Define the workspace directory (abs working dir to script)
WORKSPACE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Define the environment variable name
ENV_VAR_NAME="ROS2_SMARTY_WORKSPACE_DIR"

# Function to add or update the environment variable in a given file
add_or_update_env_var() {
    local config_file="$1"
    if [ -f "$config_file" ]; then
        if grep -q "$ENV_VAR_NAME" "$config_file"; then
            echo "Updating existing environment variable in $config_file"
            sed -i "s|export $ENV_VAR_NAME=.*|export $ENV_VAR_NAME=\"$WORKSPACE_DIR\"|" "$config_file"
        else
            echo "Adding environment variable to $config_file"
            echo "export $ENV_VAR_NAME=\"$WORKSPACE_DIR\"" >> "$config_file"
        fi
    fi
}

# Update .bashrc if it exists
add_or_update_env_var "$HOME/.bashrc"

# Update .zshrc if it exists
add_or_update_env_var "$HOME/.zshrc"

echo "Environment variable $ENV_VAR_NAME set to $WORKSPACE_DIR"

# Clone default repositories if they don't exist
echo "Cloning default repositories defined in default.repos"

if [ ! -d "$WORKSPACE_DIR/src" ]; then
    mkdir -p "$WORKSPACE_DIR/src"
    vcs import < default.repos "$WORKSPACE_DIR/src"
fi

sudo apt update
sudo rosdep init || echo "rosdep is already initilized. The above error can be ignored."
rosdep update --rosdistro=$ROS_DISTRO
rosdep install --from-paths src --ignore-src -y --rosdistro=$ROS_DISTRO

# Setup pre-commit hooks
echo "Setting up pre-commit hooks"

# Set up pre-commit-config.yaml for all repositories
CONFIG_FILE="$WORKSPACE_DIR/.pre-commit-config.yaml"

pip install -r $WORKSPACE_DIR/requirements.txt

# Find requirements.txt files in the src directory
for req_file in $(find "$WORKSPACE_DIR/src" -name "requirements.txt" -maxdepth 3); do
    echo "Installing requirements in $req_file"
    pip install -r "$req_file"
done

# Iterate over each repository in the workspace
for repo in $(find "$WORKSPACE_DIR" -maxdepth 3 -name ".git" | xargs -n1 dirname); do
    echo "Setting up .pre-commit-config.yaml in $repo"
    if [ ! -f "$repo/.pre-commit-config.yaml" ]; then
        cp "$CONFIG_FILE" "$repo/.pre-commit-config.yaml"
    elif [ "$1" == "-f" ] && [ "$WORKSPACE_DIR" != "$repo" ]; then
        echo "Forcing update of .pre-commit-config.yaml in $repo"
        # rm -f "$repo/.pre-commit-config.yaml"
        cp "$CONFIG_FILE" "$repo/.pre-commit-config.yaml" -f
    fi

    cd "$repo"
    pre-commit install -f --install-hooks
done

make -C $WORKSPACE_DIR install_extensions

echo "Pre-commit hooks set up successfully"
echo "Please restart your terminal to apply the changes and run ./scripts/install_recomended_extensions.sh to install all vscode extensions"
