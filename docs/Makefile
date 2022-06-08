PIP=pip3

.PHONY: docs  # necessary so it doesn't look for 'docs/makefile html'

init:
	rm -rf _build
	rm -rf api/generated
	cd sphinx && poetry run make doctest && poetry run make html