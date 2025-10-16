# AI Integration (Deprecated)

The Ollama/OpenRouter based text generation pipeline has been removed from IQAC-Suite. The related Django views and JavaScript entry points now surface a `503 Service Unavailable` response so existing clients fail gracefully.

No local model server or AI-specific `.env` configuration is required. If you plan to add new automation features, document them separately and ensure they remain optional for deployments that do not run AI services.
