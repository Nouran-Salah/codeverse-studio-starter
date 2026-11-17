.PHONY: install test lint format demo api

install:
	python -m pip install -e ".[dev,api]"

test:
	pytest --cov --cov-report=term-missing

lint:
	ruff check src tests
	ruff format --check src tests

format:
	ruff check --fix src tests
	ruff format src tests

demo:
	codeverse run "How do pointers work in C++?" -f json -f markdown -f srt -f manim

api:
	uvicorn codeverse.api:app --reload
