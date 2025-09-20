import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .client_ollama import AIError, chat

logger = logging.getLogger(__name__)


@login_required
@require_POST
def enhance_summary(request):
    text = request.POST.get("text", "").strip()
    title = request.POST.get("title", "").strip()
    department = request.POST.get("department", "").strip()
    start = request.POST.get("start_date", "").strip()
    end = request.POST.get("end_date", "").strip()

    if not text:
        return JsonResponse({"ok": False, "error": "No summary provided"}, status=400)

    prompt = (
        f"Title: {title}\n"
        f"Department: {department}\n"
        f"Start Date: {start}\nEnd Date: {end}\n"
        f"Summary:\n{text}\n\n"
        "Enhance and polish this event summary while keeping facts intact."
    )
    try:
        result = chat([{"role": "user", "content": prompt}])
        return JsonResponse({"ok": True, "summary": result.strip()})
    except AIError as e:
        logger.error("enhance_summary failed: %s", e)
        return JsonResponse({"ok": False, "error": str(e)}, status=503)
    except Exception as e:
        logger.exception("enhance_summary unexpected error")
        return JsonResponse(
            {"ok": False, "error": f"Unexpected error: {e}"}, status=500
        )
