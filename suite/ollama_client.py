import logging
from typing import List, Dict, Optional

import requests
from django.conf import settings as django_settings
import os

logger = logging.getLogger(__name__)


class AIError(Exception):
    """Raised when the Ollama backend fails."""
    pass


def chat(messages: List[Dict[str, str]], system: Optional[str] = None,
         model: Optional[str] = None, settings=django_settings) -> str:
    """Send a chat completion request to the configured Ollama backend."""
    base = getattr(settings, "OLLAMA_BASE", os.getenv("OLLAMA_BASE"))
    if not base:
        raise AIError("OLLAMA_BASE not configured")
    timeout = getattr(settings, "AI_HTTP_TIMEOUT", int(os.getenv("AI_HTTP_TIMEOUT", 30)))
    model_name = model or getattr(settings, "OLLAMA_MODEL", os.getenv("OLLAMA_MODEL"))
    if not model_name:
        raise AIError("OLLAMA_MODEL not configured")
    full_messages: List[Dict[str, str]] = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)
    try:
        resp = requests.post(
            f"{base}/v1/chat/completions",
            json={"model": model_name, "messages": full_messages},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.RequestException as exc:
        logger.error("Ollama request failed: %s", exc)
        raise AIError(f"Ollama request failed: {exc}") from exc
    except (KeyError, IndexError, ValueError) as exc:
        logger.error("Invalid Ollama response: %s", exc)
        raise AIError(f"Invalid Ollama response: {exc}") from exc
