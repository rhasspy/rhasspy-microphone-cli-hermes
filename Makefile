SHELL := bash
PYTHON_FILES = rhasspymicrophone_cli_hermes/*.py *.py
SHELL_FILES = bin/* debian/bin/*

.PHONY: black check venv dist sdist pyinstaller debian docker

version := $(shell cat VERSION)
architecture := $(shell dpkg-architecture | grep DEB_BUILD_ARCH= | sed 's/[^=]\+=//')

debian_package := rhasspy-microphone-cli-hermes_$(version)_$(architecture)
debian_dir := debian/$(debian_package)

black:
	black .

check:
	flake8 $(PYTHON_FILES)
	pylint $(PYTHON_FILES)
	mypy $(PYTHON_FILES)
	black --check .
	bashate $(SHELL_FILES)
	pip list --outdated

venv:
	rm -rf .venv/
	python3 -m venv .venv
	.venv/bin/pip3 install --upgrade pip
	.venv/bin/pip3 install wheel setuptools
	.venv/bin/pip3 install -r requirements.txt
	.venv/bin/pip3 install -r requirements_dev.txt

dist: sdist debian

sdist:
	python3 setup.py sdist

pyinstaller:
	mkdir -p dist
	pyinstaller -y --workpath pyinstaller/build --distpath pyinstaller/dist rhasspymicrophone_cli_hermes.spec
	tar -C pyinstaller/dist -czf dist/rhasspy-microphone-cli-hermes_$(version)_$(architecture).tar.gz rhasspymicrophone_cli_hermes/

debian: pyinstaller
	mkdir -p dist
	rm -rf "$(debian_dir)"
	mkdir -p "$(debian_dir)/DEBIAN" "$(debian_dir)/usr/bin" "$(debian_dir)/usr/lib"
	cat debian/DEBIAN/control | version=$(version) architecture=$(architecture) envsubst > "$(debian_dir)/DEBIAN/control"
	cp debian/bin/* "$(debian_dir)/usr/bin/"
	cp -R pyinstaller/dist/rhasspymicrophone_cli_hermes "$(debian_dir)/usr/lib/"
	cd debian/ && fakeroot dpkg --build "$(debian_package)"
	mv "debian/$(debian_package).deb" dist/

docker: pyinstaller
	docker build . -t "rhasspy/rhasspy-microphone-cli-hermes:$(version)"
