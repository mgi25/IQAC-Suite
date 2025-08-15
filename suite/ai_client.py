import os
import requests
from django.conf import settings


class AIError(Exception):
    pass


def _get(name: str, default=None):
    """Read from Django settings first, then OS env, then default."""
    return getattr(settings, name, os.getenv(name, default))


def _ollama_available(base: str, timeout: int = 2) -> bool:
    try:
        r = requests.get(f"{base}/v1/models", timeout=timeout)
        return r.ok
    except requests.RequestException:
        return False


def _ollama_chat(messages, system=None, model=None, temperature=0.2, timeout=None, base=None):
    base = base or _get("OLLAMA_BASE", "http://127.0.0.1:11434")
    model = model or _get("OLLAMA_MODEL", "llama3")
    timeout = timeout or int(_get("AI_HTTP_TIMEOUT", "20"))

    payload = {
        "model": model,
        "messages": ([{"role": "system", "content": system}] if system else []) + messages,
        "temperature": temperature,
    }
    r = requests.post(f"{base}/v1/chat/completions", json=payload, timeout=timeout)
    r.raise_for_status()
    try:
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        raise AIError(f"Ollama unexpected response: {r.text[:400]} ({e})")


def _openrouter_chat(messages, system=None, model=None, temperature=0.2, timeout=None, api_key=None):
    api_key = api_key or _get("OPENROUTER_API_KEY", "")
    if not api_key:
        # no key -> skip gracefully
        raise AIError("OpenRouter API key missing")

    or_model = model or _get("OPENROUTER_MODEL", "qwen/qwen3.5:free")
    timeout = timeout or int(_get("AI_HTTP_TIMEOUT", "20"))
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://iqac.local",
        "X-Title": "IQAC-Suite",
    }
    payload = {
        "model": or_model,
        "messages": ([{"role": "system", "content": system}] if system else []) + messages,
        "temperature": temperature,
    }
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=timeout)
    r.raise_for_status()
    try:
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        raise AIError(f"OpenRouter unexpected response: {r.text[:400]} ({e})")


def chat(messages, system=None, model=None, temperature=0.2, timeout=None):
    """
    Main entry point:
    - Honors AI_BACKEND (default OLLAMA)
    - Uses OpenRouter only if AI_BACKEND='OPENROUTER' OR OPENROUTER_API_KEY is present
    - Provides clear failure reasons
    """
    backend = _get("AI_BACKEND", "OLLAMA").upper()
    ollama_base = _get("OLLAMA_BASE", "http://127.0.0.1:11434")
    or_key = _get("OPENROUTER_API_KEY", "")

    order = []
    if backend == "OPENROUTER":
        order = ["OPENROUTER", "OLLAMA"]
    elif backend == "OLLAMA":
        # Only add OpenRouter as soft fallback if a key exists
        order = ["OLLAMA"] + (["OPENROUTER"] if or_key else [])
    else:
        # unknown backend -> try safest path
        order = ["OLLAMA"] + (["OPENROUTER"] if or_key else [])

    last_err = None
    for b in order:
        try:
            if b == "OLLAMA":
                if not _ollama_available(ollama_base, timeout=2):
                    raise AIError(f"Ollama not reachable at {ollama_base}")
                return _ollama_chat(messages, system=system, model=model, temperature=temperature, timeout=timeout, base=ollama_base)

            if b == "OPENROUTER":
                return _openrouter_chat(messages, system=system, model=model, temperature=temperature, timeout=timeout, api_key=or_key)

        except Exception as e:
            last_err = e
            continue

    raise AIError(f"All AI backends failed: {last_err}")

