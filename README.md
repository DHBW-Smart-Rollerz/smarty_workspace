# Smarty Workspace

This is the basic ros2 workspace for the Smarty project. It contains useful setups and configurations for the project.

## Files

- `.vscode/`: Contains the vscode settings and configurations for the workspace
  - `c_cpp_properties.json`: Contains the c/c++ properties for the workspace
  - `extensions.json`: Contains the list of recommended extensions (installed by `make install_extensions`)
  - `launch.json`: Contains the launch configurations for the workspace
  - `settings.json`: Contains the settings for the workspace
  - `tasks.json`: Contains the tasks for the workspace
- `scripts/`: Contains useful scripts for the workspace
  - `build.sh`: Build script for the workspace (`make build`)
  - `install_dependencies.sh`: Install script for the ros dependencies (`make rosdep`)
  - `install_recomended_extensions.sh`: Install script for the recommended VS Code extensions (`make install_extensions`)
  - `test.sh`: Checks the python code with ruff and pyright and runs the tests of all packages (`make test`)
- `src/`: Contains the source code for the project (**clone here the ros2 packages**)
  - `smarty_utils/`: Contains the utility packages for the project (**after setup available**)
  - `camera_preprocessing/`: Contains the camera preprocessing package for the project (**after setup available**)
  - ... other packages
- `.gitignore`: Gitignore file for the workspace (**ignores the build and install folders**)
- `.pre-commit-config.yaml`: Configuration file for the pre-commit hooks
- `ruff.toml`: Configuration of [Ruff](https://docs.astral.sh/ruff/) (python linter and formatter) for all packages in `src/`
- `default.repos`: Default repos file for the vcs tool (**clones the base packages**)
- `Makefile`: All commands for the daily work with the workspace (see [Usage](#usage))
- `requirements.txt`: Python tools for the workspace (`colcon`, `pre-commit`, `ruff`, `pyright`, `pytest`)
- `LICENSE`: License file
- `README.md`: This file
- `setup.sh`: Setup script for the workspace

## Setup

The setup is divided into two parts:

1. Setup repository and workspace
2. Setup VSCode

### 1. Setup repository and workspace

1. Clone the repository into your home directory (`~/smarty_workspace`)
2. Run the setup and build the workspace
```bash
cd ~/smarty_workspace
pyenv activate default # or your private environment
make setup
make build
```

`make setup` clones the base packages and installs the dependencies (including `colcon`, `pre-commit`, `ruff`, `pyright` and `pytest` into the active Python environment). Currently, the following packages are cloned:

- [smarty_utils](https://github.com/DHBW-Smart-Rollerz/smarty_utils)
- [camera_preprocessing](https://github.com/DHBW-Smart-Rollerz/camera_preprocessing)

Furthermore, the pre-commit hooks are installed. More about the pre-commit hooks can be found [here](https://pre-commit.com/).

### 2. Setup VSCode

1. Install the recommended extensions (already done by `make setup`):

  ```bash
  cd ~/smarty_workspace
  make install_extensions
  ```

2. Open the workspace in VSCode and check if the extensions are installed.
3. If the extensions are not installed, install them manually:
   1. Open the extensions tab in VSCode
   2. Search for `@recommended` and install all workspace recommendations
   3. Reload the workspace
   4. Check if the extensions are installed

## Usage

Open the folder in VSCode and start developing. The workspace is configured to use the pre-commit hooks. This means that the code is checked before committing. If the code is not compliant with the rules, the commit is rejected and the files are changed accordingly. We use the following pre-commit hooks:

- `ruff-check`: Linter for python to check the code for errors and style, the import order and the docstrings (fixes many issues automatically)
- `ruff-format`: Code formatter for python to have a consistent code style
- `ament_uncrustify`: Code formatter for C++ (ROS 2 code style)
- `check-yaml`: Linter for yaml files to check the syntax
- `end-of-file-fixer`: Linter to check if the files end with a newline
- `trailing-whitespace`: Linter to check for trailing whitespaces

To run the pre-commit hooks manually, use the following command:

```bash
pre-commit run --all-files
```

The workspace is used via `make` (always run it from the workspace root):

```bash
make build                          # build all packages
make build PKG=<package-name>       # build a single package (or PKG="<pkg1> <pkg2>")
make test                           # check the python code with ruff and pyright and run the tests of all packages
make clean                          # remove build/, install/ and log/
make rosdep                         # install the ROS dependencies
make install_python                 # install all requirements.txt files into the active Python env
make pull_src                       # git pull all packages in src/
make update_precommit               # copy .pre-commit-config.yaml to all packages and install the hooks
make install_extensions             # install the recommended VS Code extensions
```

To run the setup script again, use the following command:

```bash
./setup.sh -f # Force the copy of the .pre-commit-config.yaml file
```

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
