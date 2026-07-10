INBOX ?= ./inbox

.PHONY: sync process api ui samples test

sync:
	uv sync

process:
	uv run python -m extract.process $(INBOX)

api:
	uv run uvicorn extract.api:app --reload --port 8000

ui:
	uv run streamlit run ui.py

samples:
	uv run python scripts/generate_samples.py

test:
	uv sync --extra dev
	uv run pytest
