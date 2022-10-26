install:
	pipenv install -d
	pipenv shell || echo "Continuing"

test:
	pytest -vvv --doctest-modules --junitxml=junit/test-results.xml --cov=. --cov-report=xml

code:
	black src/dl_light_infra --check
	flake8 src/dl_light_infra
	mypy src/dl_light_infra

# Just for local build
build: clean
	python -m build -C--global-option=egg_info -C--global-option=--tag-build=dev0 --wheel

clean:
	@rm -rf .pytest_cache/ .mypy_cache/ junit/ build/ dist/
	@find . -not -path './.venv*' -path '*/__pycache__*' -delete
	@find . -not -path './.venv*' -path '*/*.egg-info*' -delete