#!/bin/bash

# Check if the current directory is a VS Code workspace
if [ ! -f ".vscode/extensions.json" ]; then
  echo "No .vscode/extensions.json file found in the current directory."
  echo "Please run this script from the root of a VS Code workspace."
  exit 1
fi

# Read the recommended extensions from the extensions.json file
recommended_extensions=$(jq -r '.recommendations[]' .vscode/extensions.json)

# Check if jq is installed
if ! command -v jq &> /dev/null; then
  echo "jq is not installed. Please install jq to parse JSON files."
  exit 1
fi

# Install each recommended extension
for extension in $recommended_extensions; do
  echo "Installing $extension..."
  code --install-extension "$extension"
done

echo "All recommended extensions have been installed."
