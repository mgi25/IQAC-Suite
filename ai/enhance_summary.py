from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST


@login_required
@require_POST
def enhance_summary(request):
    text = request.POST.get("text", "").strip()
    title = request.POST.get("title", "").strip()
    department = request.POST.get("department", "").strip()
    start = request.POST.get("start_date", "").strip()
    end = request.POST.get("end_date", "").strip()

    if not text:
        return JsonResponse(
            {"ok": False, "error": "No summary provided"}, status=400
        )

    return JsonResponse(
        {"ok": False, "error": "AI integration is disabled."},
        status=503,
    )
