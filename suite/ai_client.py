class AIError(Exception):
    pass


def chat(
    messages, system=None, model=None, temperature=0.2, timeout=None, options=None
):
    """All AI endpoints are disabled after removing the Ollama integration."""
    raise AIError("AI integration is disabled.")
