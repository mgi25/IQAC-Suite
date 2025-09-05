import logging
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from core.ai_client import AIClient

logger = logging.getLogger(__name__)


def _build_ctx_from_request(request):
    title = request.POST.get("title")
    department = request.POST.get("department") or getattr(request.user, "profile", None) and getattr(request.user.profile, "department_name", None)
    description = request.POST.get("description")
    objectives_hint = request.POST.get("objectives")
    outcomes_hint = request.POST.get("outcomes")
    pso_list = [p.code for p in getattr(request.user, "pso_available", [])] if hasattr(request.user, "pso_available") else []
    po_list = ["PO1", "PO2", "PO3"]
    sdg_list = ["SDG3", "SDG4", "SDG9"]
    ctx = {
        "title": title or "TBD",
        "department": department or "TBD",
        "description": description or "TBD",
        "objectives_hint": objectives_hint,
        "outcomes_hint": outcomes_hint,
        "pso_list": pso_list,
        "po_list": po_list,
        "sdg_list": sdg_list,
    }
    logger.debug("Built context %s", ctx)
    return ctx


@require_POST
@csrf_exempt
def ai_need_analysis(request):
    ctx = _build_ctx_from_request(request)
    data = AIClient().need_analysis(ctx)
    return JsonResponse(data)


@require_POST
@csrf_exempt
def ai_objectives(request):
    ctx = _build_ctx_from_request(request)
    data = AIClient().objectives(ctx)
    return JsonResponse(data)


@require_POST
@csrf_exempt
def ai_outcomes(request):
    ctx = _build_ctx_from_request(request)
    data = AIClient().outcomes(ctx)
    return JsonResponse(data)


@require_POST
@csrf_exempt
def ai_report(request):
    ctx = _build_ctx_from_request(request)
    data = AIClient().report(ctx)
    return JsonResponse(data)
