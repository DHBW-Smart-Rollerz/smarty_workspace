# Smarty Workspace

This is the basic ros2 workspace for the Smarty project. It contains useful setups and configurations for the project.

## Files

- `.vscode/`: Contains the vscode settings and configurations for the workspace
  - `c_cpp_properties.json`: Contains the c/c++ properties for the workspace
  - `extensions.json`: Contains the list of extensions to install
  - `launch.json`: Contains the launch configurations for the workspace
  - `settings.json`: Contains the settings for the workspace
  - `tasks.json`: Contains the tasks for the workspace
- `scripts/`: Contains useful scripts for the workspace
  - `build.sh`: Build script for the workspace
  - `install_dependencies.sh`: Install script for the ros dependencies
  - `test.sh`: Test script for the ros packages
- `src/`: Contains the source code for the project (**clone here the ros2 packages**)
  - `smarty_utils/`: Contains the utility packages for the project (**after setup available**)
  - `camera_preprocessing/`: Contains the camera preprocessing package for the project (**after setup available**)
  - ... other packages
- `.gitignore`: Gitignore file for the workspace (**ignores the build and install folders**)
- `.pre-commit-config.yaml`: Configuration file for the pre-commit hooks
- `default.repos`: Default repos file for the vcs tool (**clones the base packages**)
- `LICENSE`: License file
- `README.md`: This file
- `setup.sh`: Setup script for the workspace

## Setup

1. Clone the repository
2. Run the setup script
```bash
./setup.sh
```

**Note**: The setup script clones the base packages. The other packages need to be cloned manually.

## Usage

Open the folder in VSCode and start developing.

**Note**: Only VSCode is supported for now, but feel free to add support for other IDEs.

## Contributing

Please create a pull request for any changes you want to make:

- Fork the repository
- Create a new branch
- Make your changes
- Commit your changes
- Push your changes
- Create a pull request

It is welcome to create issues for any bugs or feature requests and required to use the pre-commit hooks.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
