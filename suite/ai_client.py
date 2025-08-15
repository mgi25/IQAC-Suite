import logging
from typing import List, Dict, Optional
import requests
from django.conf import settings as django_settings

logger = logging.getLogger(__name__)

class AIError(Exception):
    """Raised when all AI backends are unavailable."""
    pass


def _ollama_available(base: str) -> bool:
    try:
        resp = requests.get(f"{base}/v1/models", timeout=2)
        resp.raise_for_status()
        return True
    except Exception as exc:  # pragma: no cover - health check failure
        logger.warning("Ollama health check failed: %s", exc)
        return False


def _post_chat(url: str, headers: Dict[str, str], body: Dict, timeout: int) -> str:
    resp = requests.post(url, headers=headers, json=body, timeout=timeout)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def chat(messages: List[Dict[str, str]], system: Optional[str] = None,
         model: Optional[str] = None, settings=None) -> str:
    """Send a chat completion request with automatic backend fallback."""
    settings = settings or django_settings
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    preferred = settings.AI_BACKEND.upper()
    order = [preferred, "OPENROUTER" if preferred == "OLLAMA" else "OLLAMA"]

    errors = []
    for backend in order:
        try:
            if backend == "OLLAMA":
                base = getattr(settings, "OLLAMA_BASE", None)
                if not base:
                    raise AIError("Ollama base URL not configured")
                if not _ollama_available(base):
                    raise AIError("Ollama backend unreachable")
                model_name = model or getattr(settings, "OLLAMA_GEN_MODEL", None)
                if not model_name:
                    raise AIError("Ollama model not configured")
                body = {
                    "model": model_name,
                    "messages": full_messages,
                    "temperature": 0.2,
                }
                return _post_chat(f"{base}/v1/chat/completions",
                                  {"Content-Type": "application/json"},
                                  body, settings.AI_HTTP_TIMEOUT)
            else:  # OPENROUTER
                api_key = getattr(settings, "OPENROUTER_API_KEY", None)
                if not api_key:
                    raise AIError("OpenRouter API key missing")
                model_name = getattr(settings, "OPENROUTER_MODEL", None)
                if not model_name:
                    raise AIError("OpenRouter model not configured")
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                body = {
                    "model": model_name,
                    "messages": full_messages,
                    "temperature": 0.2,
                }
                return _post_chat("https://openrouter.ai/api/v1/chat/completions",
                                  headers, body, settings.AI_HTTP_TIMEOUT)
        except Exception as exc:
            logger.warning("%s backend failed: %s", backend, exc)
            errors.append(f"{backend}: {exc}")
            continue
    raise AIError("All AI backends failed: " + "; ".join(errors))
