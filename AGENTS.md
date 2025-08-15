# Agent Instructions

This repository uses **local** AI models via [Ollama](https://github.com/ollama/ollama). All AI interactions must go through the helpers in `ai/` and respect the routing rules below.

## Runtime
- Environment variables configure the backend in `.env`:
  - `AI_BACKEND=OLLAMA`
  - `OLLAMA_BASE=http://127.0.0.1:11434`
  - `OLLAMA_GEN_MODEL` – writer model
  - `OLLAMA_CRITIC_MODEL` – critic model
- Use `ai/client_ollama.py` for OpenAI‑compatible `/v1/chat/completions` requests.

## Model routing
- `need-analysis`, `report-outline`, and `report-section` tasks → writer model
- `critique` → critic model
- Add new tasks in `ai/router.py`; **never** hardcode cloud models.

## Long reports
- Follow `ai/pipeline.py` pattern:
  1. Generate outline
  2. `parse_outline_to_titles`
  3. For each title: generate section → critique → save to `EventReport.summary`
- Stream progress through existing views: `ai_report_progress`, `ai_report_partial`, `generate_ai_report_stream`.

## Coding standards
- Keep views thin; put AI logic in `ai/` helpers.
- Use `logger = logging.getLogger(__name__)`.
- Keep settings in env; do not commit secrets or binaries.
- When editing AI endpoints, extend tests under `emt/tests/` and run `python manage.py test`.

These guidelines help other agents understand what AI to use and how the system should behave.
