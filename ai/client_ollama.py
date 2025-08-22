import logging
import os
from typing import List, Dict, Optional

import requests
from django.conf import settings as django_settings

logger = logging.getLogger(__name__)


class AIError(Exception):
    """Raised when the Ollama backend fails."""
    pass


def chat(
    messages: List[Dict[str, str]],
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
    timeout: Optional[int] = None,
    options: Optional[Dict] = None,
    settings=django_settings,
) -> str:
    """Send a chat completion request to the configured Ollama backend."""
    base = getattr(settings, "OLLAMA_BASE", os.getenv("OLLAMA_BASE", "http://127.0.0.1:11434"))
    timeout = int(timeout or getattr(settings, "AI_HTTP_TIMEOUT", os.getenv("AI_HTTP_TIMEOUT", 120)))
    model_name = model or getattr(settings, "OLLAMA_GEN_MODEL", os.getenv("OLLAMA_GEN_MODEL", "llama3"))

    payload: Dict = {
        "model": model_name,
        "messages": ([{"role": "system", "content": system}] if system else []) + messages,
        "temperature": temperature,
        "stream": False,
    }
    opts = {"num_predict": 300}
    if isinstance(options, dict):
        opts.update(options)
    payload["options"] = opts

    try:
        resp = requests.post(
            f"{base}/v1/chat/completions",
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.Timeout as exc:
        logger.error("Ollama request timed out after %ss", timeout)
        raise AIError(f"Ollama request timed out after {timeout}s") from exc
    except requests.RequestException as exc:
        logger.error("Ollama request failed: %s", exc)
        raise AIError(f"Ollama request failed: {exc}") from exc
    except (KeyError, IndexError, ValueError) as exc:
        logger.error("Invalid Ollama response: %s", exc)
        raise AIError(f"Invalid Ollama response: {exc}") from exc
