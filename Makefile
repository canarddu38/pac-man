PYTHON			= python3
VENV			= .venv
VENV_BIN		= $(VENV)/bin
V_PYTHON		= $(VENV_BIN)/python
V_PIP			= $(VENV_BIN)/python -m pip
MAIN			= pac-man.py

MYPY_FLAGS		= --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs
DEPENDENCIES	= pyinstaller pytest flake8 pyray pyinstaller raylib pydantic mypy mazegenerator-00001-py3-none-any.whl
FLAKE			= $(VENV_BIN)/flake8
MYPY			= $(VENV_BIN)/mypy
EXCLUDE			= $(VENV)
SRC_FILES		=	./src/pac-man.py \
					./src/config.py \
					./src/components.py \
					./src/character.py \
					./src/enums.py \
					./src/graphics.py \
					./src/multiplayer.py \
					./src/pacgums.py \
					./src/pathfinding.py \
					./src/rlights.py \
					./src/scenes.py


all: install build

install:
	@if [ ! -f pyproject.toml ]; then \
		echo "Initialization of uv..."; \
		uv init; \
	fi
	uv sync
	UV_SKIP_WHEEL_FILENAME_CHECK=1 uv pip install mazegenerator-00001-py3-none-any.whl

build: install pac-man

pac-man: $(SRC_FILES) pyproject.toml
	rm -rf dist
	uv run pyinstaller -F src/$(MAIN)
	mv dist/pac-man .
	rm -rf dist build pac-man.spec

run: install build
	./pac-man config.json

debug: install
	uv run python3 -m pdb src/$(MAIN)

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache pac-man.spec dist $(VENV) pac-man uv.lock .cache/

lint: install
	$(FLAKE) . --exclude '$(VENV)'
	$(MYPY) $(MYPY_FLAGS) src

lint-strict: install
	$(FLAKE) . --exclude '$(VENV)'
	$(MYPY) $(MYPY_FLAGS) --strict src


.PHONY: all install build run debug clean lint lint-strict