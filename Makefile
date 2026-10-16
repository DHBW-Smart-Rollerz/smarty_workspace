.PHONY: clean build rosdep test setup pull_src update_precommit install_python install_extensions

clean:
	rm -rf build/ install/ log/;

build:
	@python -c "import colcon_core" 2>/dev/null || { \
		echo "colcon is not installed in the active Python environment ($$(command -v python))."; \
		echo "Run 'pyenv activate default' and 'make install_python' first."; \
		exit 1; }
	./scripts/build.sh $(PKG)

rosdep:
	./scripts/install_dependencies.sh

test:
	./scripts/test.sh

setup:
	./setup.sh

pull_src:
	find . -type d -name .git -exec sh -c 'if [ "$$(dirname "$$1")" != "." ]; then echo "Pulling in dir: $$(dirname "$$1")" && git -C "$$(dirname "$$1")" pull; fi' _ {} \;

update_precommit:
	find src -type d -name .git -exec sh -c 'if [ "$$(dirname "$$1")" != "." ]; then echo "Replacing in dir: $$(dirname "$$1")" && cp -f .pre-commit-config.yaml "$$(dirname "$$1")" && (cd "$$(dirname "$$1")" && pre-commit install -f --install-hooks); fi' _ {} \;

install_python:
	# Install dependencies by finding all requirements.txt files (including colcon from ./requirements.txt)
	find . -type f -name requirements.txt -exec sh -c 'pip install -r "$$1"' _ {} \;

install_extensions:
	./scripts/install_recomended_extensions.sh
