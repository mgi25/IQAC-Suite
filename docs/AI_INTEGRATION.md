# AI Integration

The application can use OpenRouter or a local HTTP server for AI-generated Need Analysis.

## Local HTTP backend

1. Start the local server:
   ```bash
   uvicorn local_ai_server:app --host 127.0.0.1 --port 8000
   ```
2. Configure `.env`:
   ```bash
   AI_BACKEND=LOCAL_HTTP
   LOCAL_AI_BASE_URL=http://127.0.0.1:8000
   LOCAL_AI_MODEL=Qwen2.5-7B-Instruct-1M
   ```
3. Restart Django and use the "Generate with AI" button.
