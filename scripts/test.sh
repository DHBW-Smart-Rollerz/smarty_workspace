#!/bin/bash
set -e

# Check the Python code of all packages with ruff (configured in ruff.toml).
# --no-respect-gitignore is needed, because src/ is ignored by the .gitignore of the workspace.
echo "Checking the Python code with ruff ..."
python -m ruff check --no-respect-gitignore src
python -m ruff format --check --no-respect-gitignore src

# ROS and the workspace packages are needed for pyright and the tests
if [ -f install/setup.bash ]; then source install/setup.bash; fi

# Check the types of the Python code with pyright ("standard" mode, like Pylance in VS Code).
# Pyright finds ROS and the workspace packages via the sourced environment.
echo "Checking the Python types with pyright ..."
python -m pyright src

# Run the tests of all packages. The flake8 and pep257 tests of the ROS package
# templates are skipped, because ruff replaces them.
python -m colcon test \
    --pytest-args -m "not flake8 and not pep257" \
    --ctest-args -E "flake8|pep257"
python -m colcon test-result --verbose
