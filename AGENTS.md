# Agent Instructions

Ollama-based AI generation has been fully removed from this repository. Any legacy AI endpoints now return a `503 Service Unavailable` response with an “AI integration is disabled” message. There is no local model runtime to configure, and no environment variables related to AI are required.

If you are extending or refactoring the codebase:
- Do not reintroduce external AI calls without explicit approval.
- Keep view logic lightweight and surface clear user-facing errors when AI functionality is not available.
- Continue to add or update Django tests under `emt/tests/` when touching the former AI endpoints.
