import logging
import json
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .ai_client import chat, AIError
from .prompts import (
    SYSTEM_WHY_EVENT,
    user_prompt_wyhevent,
    SYSTEM_NEED,
    SYSTEM_OBJECTIVES,
    SYSTEM_LEARNING,
)
from .facts import collect_basic_facts
from .ai_safety import (
    strip_unverifiable_phrases,
    allowed_numbers_from_facts,
    enforce_no_unverified_numbers,
    parse_model_json,
)

logger = logging.getLogger(__name__)

def _sanitize(text: str, facts: dict) -> str:
    text = strip_unverifiable_phrases(text)
    text = enforce_no_unverified_numbers(text, allowed_numbers_from_facts(facts))
    return text

@login_required
@require_POST
def generate_why_event(request):
    facts = collect_basic_facts(request)
    try:
        result = chat([{"role": "user", "content": user_prompt_wyhevent(facts)}], system=SYSTEM_WHY_EVENT)
        data = parse_model_json(result)
        need = _sanitize(data.get("need_analysis", "").strip(), facts)
        objectives = [o.strip() for o in data.get("objectives", [])]
        outcomes = [o.strip() for o in data.get("learning_outcomes", [])]
        return JsonResponse({
            "ok": True,
            "need_analysis": need,
            "objectives": objectives,
            "learning_outcomes": outcomes,
        })
    except AIError as e:
        logger.error("generate_why_event failed: %s", e)
        return JsonResponse({"ok": False, "error": str(e)}, status=503)
    except Exception as e:
        logger.error("generate_why_event parse error: %s", e)
        return JsonResponse({"ok": False, "error": f"Parse error: {e}"}, status=500)

@login_required
@require_POST
def generate_need_analysis(request):
    facts = collect_basic_facts(request)
    try:
        prompt = f"facts = {facts}\nTask: Write a need analysis. No invented claims or numbers not in facts."
        text = chat([{"role": "user", "content": prompt}], system=SYSTEM_NEED)
        text = _sanitize(text, facts)
        return JsonResponse({"ok": True, "field": "need_analysis", "value": text})
    except AIError as e:
        logger.error("generate_need_analysis failed: %s", e)
        return JsonResponse({"ok": False, "error": str(e)}, status=503)
    except Exception as e:
        logger.error("generate_need_analysis unexpected error: %s", e)
        return JsonResponse({"ok": False, "error": f"Unexpected error: {e}"}, status=500)

@login_required
@require_POST
def generate_objectives(request):
    facts = collect_basic_facts(request)
    try:
        prompt = f"facts = {facts}\nTask: 4–6 objectives. No numbers unless in facts."
        text = chat([{"role": "user", "content": prompt}], system=SYSTEM_OBJECTIVES)
        bullets = [b.strip(" •-*0123456789.").strip() for b in text.splitlines() if b.strip()]
        return JsonResponse({"ok": True, "field": "objectives", "value": bullets})
    except AIError as e:
        logger.error("generate_objectives failed: %s", e)
        return JsonResponse({"ok": False, "error": str(e)}, status=503)
    except Exception as e:
        logger.error("generate_objectives unexpected error: %s", e)
        return JsonResponse({"ok": False, "error": f"Unexpected error: {e}"}, status=500)

@login_required
@require_POST
def generate_learning_outcomes(request):
    facts = collect_basic_facts(request)
    try:
        prompt = f"facts = {facts}\nTask: 3–5 learning outcomes. Bloom verbs. No numbers unless in facts."
        text = chat([{"role": "user", "content": prompt}], system=SYSTEM_LEARNING)
        bullets = [b.strip(" •-*0123456789.").strip() for b in text.splitlines() if b.strip()]
        return JsonResponse({"ok": True, "field": "learning_outcomes", "value": bullets})
    except AIError as e:
        logger.error("generate_learning_outcomes failed: %s", e)
        return JsonResponse({"ok": False, "error": str(e)}, status=503)
    except Exception as e:
        logger.error("generate_learning_outcomes unexpected error: %s", e)
        return JsonResponse({"ok": False, "error": f"Unexpected error: {e}"}, status=500)
