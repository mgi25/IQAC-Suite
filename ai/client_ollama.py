class AIError(Exception):
    """Raised when the Ollama backend fails."""


def chat(messages, system=None, model=None, temperature=0.2, timeout=None, options=None, settings=None):
    """All Ollama requests are disabled."""
    raise AIError("AI integration is disabled.")
