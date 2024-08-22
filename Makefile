.PHONY: clean build setup update_precommit

clean:
	rm -rf build/ install/ log/;

build:
	./scripts/build.sh

setup:
	./setup.sh

update_precommit:
	find . -type d -name .git -exec sh -c 'if [ "$$(dirname "$$1")" != "." ]; then echo "Replacing in dir: $$(dirname "$$1")" && cp -f .pre-commit-config.yaml "$$(dirname "$$1")"; fi' _ {} \;
