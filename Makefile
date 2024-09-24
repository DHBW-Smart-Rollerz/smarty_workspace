.PHONY: clean build setup update_precommit install_python install_extensions

clean:
	rm -rf build/ install/ log/;

build:
	./scripts/build.sh $(PKG)

test:
	./scripts/test.sh

setup:
	./setup.sh

update_precommit:
	find . -type d -name .git -exec sh -c 'if [ "$$(dirname "$$1")" != "." ]; then echo "Replacing in dir: $$(dirname "$$1")" && cp -f .pre-commit-config.yaml "$$(dirname "$$1")"; fi' _ {} \;

install_python:
	# Install depndencies by finding all requirements.txt files
	find . -type f -name requirements.txt -exec sh -c 'pip install -r "$$1"' _ {} \;

install_extensions:
	./scripts/install_recomended_extensions.sh

filter_dependencies:
	@if [ -z "$(SUBDIR)" ]; then \
		echo "Please provide a SUBDIR variable to filter dependencies"; \
	else \
		if [ -f "src/$(SUBDIR)/requirements.txt" ]; then \
			grep -v -E -f skip_dependencies.txt "src/$(SUBDIR)/requirements.txt" > "src/$(SUBDIR)/filtered_requirements.txt"; \
			echo "Filtered requirements in src/$(SUBDIR)"; \
			mv "src/$(SUBDIR)/filtered_requirements.txt" "src/$(SUBDIR)/requirements.txt"; \
		else \
			echo "No requirements.txt found in src/$(SUBDIR)"; \
		fi \
	fi
