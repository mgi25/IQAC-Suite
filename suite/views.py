import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .ai_client import AIError, chat
from .ai_safety import (allowed_numbers_from_facts,
                        enforce_no_unverified_numbers, parse_model_json,
                        strip_unverifiable_phrases)
from .facts import collect_basic_facts, load_fields
from .prompts import (SYSTEM_LEARNING, SYSTEM_OBJECTIVES, SYSTEM_WHY_EVENT,
                      user_prompt_wyhevent)

logger = logging.getLogger(__name__)


def _sanitize(text: str, facts: dict) -> str:
    text = strip_unverifiable_phrases(text)
    text = enforce_no_unverified_numbers(text, allowed_numbers_from_facts(facts))
    return text


def _bullets(value, facts):
    """Normalize model output into a list of sanitized bullet strings."""
    if isinstance(value, str):
        items = value.splitlines()
    elif isinstance(value, list):
        items = value
    else:
        items = []
    return [
        _sanitize(
            b.strip().lstrip("•-*0123456789. "),
            facts,
        )
        for b in items
        if b and b.strip()
    ]


@login_required
@require_POST
def generate_why_event(request):
    fields = load_fields("why_event")
    facts = collect_basic_facts(request, fields)
    try:
        result = chat(
            [{"role": "user", "content": user_prompt_wyhevent(facts)}],
            system=SYSTEM_WHY_EVENT,
            timeout=getattr(settings, "AI_HTTP_TIMEOUT", 120),
            options={"num_predict": 300},
        )
        data = parse_model_json(result)
        need = _sanitize(data.get("need_analysis", "").strip(), facts)

        objectives = _bullets(data.get("objectives", []), facts)
        if not objectives:
            try:
                prompt = (
                    f"facts = {facts}\n"
                    "Task: 4–6 objectives. No numbers unless in facts."
                )
                obj_text = chat(
                    [{"role": "user", "content": prompt}],
                    system=SYSTEM_OBJECTIVES,
                    timeout=getattr(settings, "AI_HTTP_TIMEOUT", 120),
                    options={"num_predict": 300},
                )
                objectives = _bullets(obj_text, facts)
            except AIError as e2:
                logger.error("generate_why_event objectives fallback failed: %s", e2)
                objectives = []

        outcomes = _bullets(data.get("learning_outcomes", []), facts)
        if not outcomes:
            try:
                prompt = (
                    f"facts = {facts}\n"
                    "Task: 3–5 learning outcomes. Bloom verbs. No numbers unless in facts."
                )
                out_text = chat(
                    [{"role": "user", "content": prompt}],
                    system=SYSTEM_LEARNING,
                    timeout=getattr(settings, "AI_HTTP_TIMEOUT", 120),
                    options={"num_predict": 300},
                )
                outcomes = _bullets(out_text, facts)
            except AIError as e3:
                logger.error("generate_why_event outcomes fallback failed: %s", e3)
                outcomes = []

        return JsonResponse(
            {
                "ok": True,
                "need_analysis": need,
                "objectives": objectives,
                "learning_outcomes": outcomes,
            }
        )
    except AIError as e:
        logger.error("generate_why_event failed: %s", e)
        return JsonResponse({"ok": False, "error": str(e)}, status=503)
    except Exception as e:
        logger.error("generate_why_event parse error: %s", e)
        return JsonResponse({"ok": False, "error": f"Parse error: {e}"}, status=500)


@login_required
@require_POST
def generate_need_analysis(request):
    fields = load_fields("need_analysis")
    facts = collect_basic_facts(request, fields)
    topic = facts.get(
        "event_title",
        (request.POST.get("topic") or request.POST.get("title") or "").strip(),
    )

    system = (
        "You write concise academic text for university proposals using ONLY provided facts. "
        "No invented surveys/stats/quotes/partners/dates. Unknowns -> [TBD]. 120–180 words."
    )
    prompt = f"facts = {facts}\nNeed Analysis for: {topic}. Keep it fact-only."
    messages = [{"role": "user", "content": prompt}]

    try:
        text = chat(
            messages,
            system=system,
            timeout=getattr(settings, "AI_HTTP_TIMEOUT", 120),
            options={"num_predict": 300},
        ).strip()
        return JsonResponse({"ok": True, "field": "need_analysis", "value": text})
    except AIError as e:
        logger.error("generate_need_analysis failed: %s", e)
        return JsonResponse({"ok": False, "error": str(e)}, status=503)
    except Exception as e:
        logger.error("generate_need_analysis unexpected error: %s", e)
        return JsonResponse(
            {"ok": False, "error": f"Unexpected error: {e}"}, status=500
        )


@login_required
@require_POST
def generate_objectives(request):
    fields = load_fields("objectives")
    facts = collect_basic_facts(request, fields)
    try:
        prompt = f"facts = {facts}\nTask: 4–6 objectives. No numbers unless in facts."
        text = chat(
            [{"role": "user", "content": prompt}],
            system=SYSTEM_OBJECTIVES,
            timeout=getattr(settings, "AI_HTTP_TIMEOUT", 120),
            options={"num_predict": 300},
        )
        bullets = [
            b.strip(" •-*0123456789.").strip() for b in text.splitlines() if b.strip()
        ]
        return JsonResponse({"ok": True, "field": "objectives", "value": bullets})
    except AIError as e:
        logger.error("generate_objectives failed: %s", e)
        return JsonResponse({"ok": False, "error": str(e)}, status=503)
    except Exception as e:
        logger.error("generate_objectives unexpected error: %s", e)
        return JsonResponse(
            {"ok": False, "error": f"Unexpected error: {e}"}, status=500
        )


@login_required
@require_POST
def generate_learning_outcomes(request):
    fields = load_fields("learning_outcomes")
    facts = collect_basic_facts(request, fields)
    try:
        prompt = f"facts = {facts}\nTask: 3–5 learning outcomes. Bloom verbs. No numbers unless in facts."
        text = chat(
            [{"role": "user", "content": prompt}],
            system=SYSTEM_LEARNING,
            timeout=getattr(settings, "AI_HTTP_TIMEOUT", 120),
            options={"num_predict": 300},
        )
        bullets = [
            b.strip(" •-*0123456789.").strip() for b in text.splitlines() if b.strip()
        ]
        return JsonResponse(
            {"ok": True, "field": "learning_outcomes", "value": bullets}
        )
    except AIError as e:
        logger.error("generate_learning_outcomes failed: %s", e)
        return JsonResponse({"ok": False, "error": str(e)}, status=503)
    except Exception as e:
        logger.error("generate_learning_outcomes unexpected error: %s", e)
        return JsonResponse(
            {"ok": False, "error": f"Unexpected error: {e}"}, status=500
        )
