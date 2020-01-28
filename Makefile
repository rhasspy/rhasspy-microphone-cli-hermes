SHELL := bash
PYTHON_NAME = rhasspymicrophone_cli_hermes
PACKAGE_NAME = rhasspy-microphone-cli-hermes
SOURCE = $(PYTHON_NAME)
PYTHON_FILES = $(SOURCE)/*.py *.py
SHELL_FILES = bin/* debian/bin/*
PIP_INSTALL ?= install

.PHONY: reformat check venv dist sdist pyinstaller debian docker deploy

version := $(shell cat VERSION)
architecture := $(shell bash architecture.sh)

debian_package := $(PACKAGE_NAME)_$(version)_$(architecture)
debian_dir := debian/$(debian_package)

# -----------------------------------------------------------------------------
# Python
# -----------------------------------------------------------------------------

reformat:
	black .
	isort $(PYTHON_FILES)

check:
	flake8 $(PYTHON_FILES)
	pylint $(PYTHON_FILES)
	mypy $(PYTHON_FILES)
	black --check .
	isort --check-only $(PYTHON_FILES)
	bashate $(SHELL_FILES)
	yamllint .
	pip list --outdated

venv:
	rm -rf .venv/
	python3 -m venv .venv
	.venv/bin/pip3 $(PIP_INSTALL) --upgrade pip
	.venv/bin/pip3 $(PIP_INSTALL) wheel setuptools
	.venv/bin/pip3 $(PIP_INSTALL) -r requirements.txt
	.venv/bin/pip3 $(PIP_INSTALL) -r requirements_dev.txt

dist: sdist debian

sdist:
	python3 setup.py sdist

# -----------------------------------------------------------------------------
# Docker
# -----------------------------------------------------------------------------

docker: pyinstaller
	docker build . -t "rhasspy/rhasspy-microphone-cli-hermes:$(version)" -t "rhasspy/$(PACKAGE_NAME):latest"

deploy:
	echo "$$DOCKER_PASSWORD" | docker login -u "$$DOCKER_USERNAME" --password-stdin
	docker push rhasspy/$(PACKAGE_NAME):$(version)

# -----------------------------------------------------------------------------
# Debian
# -----------------------------------------------------------------------------

pyinstaller:
	mkdir -p dist
	pyinstaller -y --workpath pyinstaller/build --distpath pyinstaller/dist $(PYTHON_NAME).spec
	tar -C pyinstaller/dist -czf dist/$(PACKAGE_NAME)_$(version)_$(architecture).tar.gz $(SOURCE)/

debian: pyinstaller
	mkdir -p dist
	rm -rf "$(debian_dir)"
	mkdir -p "$(debian_dir)/DEBIAN" "$(debian_dir)/usr/bin" "$(debian_dir)/usr/lib"
	cat debian/DEBIAN/control | version=$(version) architecture=$(architecture) envsubst > "$(debian_dir)/DEBIAN/control"
	cp debian/bin/* "$(debian_dir)/usr/bin/"
	cp -R pyinstaller/dist/$(PYTHON_NAME) "$(debian_dir)/usr/lib/"
	cd debian/ && fakeroot dpkg --build "$(debian_package)"
	mv "debian/$(debian_package).deb" dist/
