.PHONY: preview pipeline weekly test

preview:
	poetry run python main.py preview

pipeline:
	poetry run python main.py pipeline

weekly:
	poetry run python main.py weekly-email

test:
	poetry run pytest
