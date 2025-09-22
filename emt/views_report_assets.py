from __future__ import annotations

import copy
import json
import mimetypes
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Max
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from PIL import Image, UnidentifiedImageError

from core.models import Report

from .models import ReportAsset
from .report_assets_utils import (
    ALLOWED_EXTENSIONS,
    BROCHURE_LIMIT,
    IMAGE_EXTENSIONS,
    MAX_UPLOAD_SIZE,
    SINGLETON_CATEGORIES,
    build_annexures_payload,
    serialize_asset,
)


def _user_can_edit_report(user, report: Report) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return getattr(report, "submitted_by_id", None) == user.id


@login_required
@csrf_protect
def submit_step_7(request, report_id: int):
    report = get_object_or_404(Report, id=report_id)
    if not _user_can_edit_report(request.user, report):
        return HttpResponseForbidden("You do not have permission to edit this report.")

    panel_config: List[Dict[str, object]] = [
        {
            "category": ReportAsset.Category.PHOTO,
            "title": "Photographs",
            "slug": "photos",
            "multiple": True,
            "max_items": None,
            "description": "Upload event photographs for Annexure A.",
        },
        {
            "category": ReportAsset.Category.BROCHURE,
            "title": "Brochure",
            "slug": "brochure",
            "multiple": True,
            "max_items": BROCHURE_LIMIT,
            "description": "Upload up to 4 brochure pages.",
        },
        {
            "category": ReportAsset.Category.COMMUNICATION,
            "title": "Communication with Institution",
            "slug": "communication",
            "multiple": True,
            "max_items": None,
            "description": "Letters or emails sent to the institution (images or PDFs).",
        },
        {
            "category": ReportAsset.Category.WORKSHEET,
            "title": "Worksheets / Activities",
            "slug": "worksheets",
            "multiple": True,
            "max_items": None,
            "description": "Activity sheets, worksheets, or similar evidence.",
        },
        {
            "category": ReportAsset.Category.EVALUATION,
            "title": "Evaluation Sheet",
            "slug": "evaluation",
            "multiple": False,
            "max_items": 1,
            "description": "Single evaluation sheet (new upload replaces the existing one).",
        },
        {
            "category": ReportAsset.Category.FEEDBACK,
            "title": "Feedback Form",
            "slug": "feedback",
            "multiple": False,
            "max_items": 1,
            "description": "Single feedback form (new upload replaces the existing one).",
        },
    ]

    assets_by_category = {}
    for panel in panel_config:
        category = panel["category"]
        qs = report.assets.filter(category=category).order_by("order_index", "id")
        assets_by_category[category] = [serialize_asset(asset) for asset in qs]

    annexures_payload = build_annexures_payload(report)["annexures"]

    if request.method == "POST":
        payload = copy.deepcopy(report.generated_payload or {})
        payload["annexures"] = annexures_payload
        report.generated_payload = payload
        report.save(update_fields=["generated_payload"])
        messages.success(request, "Annexures saved successfully.")
        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect(reverse("emt:report_annexures", args=[report.id]))

    context = {
        "report": report,
        "panel_config": panel_config,
        "assets_by_category": assets_by_category,
        "annexures_payload": annexures_payload,
        "singleton_categories": SINGLETON_CATEGORIES,
        "next_url": request.GET.get("next", ""),
    }
    return render(request, "reports/submit_step_7.html", context)


def _load_report(report_id: int, user) -> Report:
    report = get_object_or_404(Report, id=report_id)
    if not _user_can_edit_report(user, report):
        raise PermissionDenied
    return report


def _json_error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


def _extension_for(upload) -> str:
    name = getattr(upload, "name", "")
    return Path(name).suffix.lower()


def _content_type_for(upload, extension: str) -> Optional[str]:
    content_type = getattr(upload, "content_type", None)
    if content_type:
        return content_type
    guessed, _ = mimetypes.guess_type(getattr(upload, "name", ""))
    return guessed


def _build_meta(upload, extension: str, content_type: Optional[str]) -> dict:
    meta = {}
    if content_type:
        meta["content_type"] = content_type
    if extension:
        meta["extension"] = extension.lstrip(".")
    if extension in IMAGE_EXTENSIONS:
        upload.seek(0)
        try:
            with Image.open(upload) as img:
                width, height = img.size
        except UnidentifiedImageError as exc:  # pragma: no cover - sanity guard
            raise ValidationError("Unsupported image file.") from exc
        finally:
            upload.seek(0)
        meta.update({"width": width, "height": height})
    return meta


def _serialize_assets(qs: Iterable[ReportAsset]):
    return [serialize_asset(asset) for asset in qs]


@login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def assets_collection(request, report_id: int):
    try:
        report = _load_report(report_id, request.user)
    except PermissionDenied:
        return _json_error("You do not have permission to modify this report.", status=403)

    if request.method == "GET":
        category = request.GET.get("category")
        assets_qs = report.assets.all()
        if category:
            if category not in ReportAsset.Category.values:
                return _json_error("Invalid category.", status=400)
            assets_qs = assets_qs.filter(category=category)
        assets_qs = assets_qs.order_by("order_index", "id")
        data = _serialize_assets(assets_qs)
        return JsonResponse({"results": data, "count": len(data)})

    upload = request.FILES.get("file")
    category = request.POST.get("category")
    caption = request.POST.get("caption", "").strip()

    if not upload:
        return _json_error("No file uploaded.")
    if not category:
        return _json_error("Category is required.")
    if category not in ReportAsset.Category.values:
        return _json_error("Invalid category.")

    extension = _extension_for(upload)
    if extension not in ALLOWED_EXTENSIONS:
        return _json_error("Unsupported file type.")
    if upload.size and upload.size > MAX_UPLOAD_SIZE:
        return _json_error("File exceeds 10 MB limit.")

    existing = report.assets.filter(category=category).order_by("order_index", "id")
    if category == ReportAsset.Category.BROCHURE and existing.count() >= BROCHURE_LIMIT:
        return _json_error("Brochure limited to 4 pages.")
    if category in SINGLETON_CATEGORIES and existing.exists():
        for asset in existing:
            asset.file.delete(save=False)
            asset.delete()

    if category in SINGLETON_CATEGORIES:
        order_index = 0
    else:
        order_index = (
            existing.aggregate(Max("order_index")).get("order_index__max") or 0
        )
        if existing.exists():
            order_index += 1

    content_type = _content_type_for(upload, extension)
    meta = _build_meta(upload, extension, content_type)

    asset = ReportAsset(
        report=report,
        category=category,
        caption=caption,
        order_index=order_index,
        meta=meta,
    )
    asset.file = upload

    try:
        asset.full_clean()
        asset.save()
    except ValidationError as exc:
        return _json_error("; ".join(exc.messages))

    return JsonResponse(serialize_asset(asset), status=201)


@login_required
@csrf_protect
@require_http_methods(["PATCH", "DELETE"])
def asset_detail(request, asset_id: int):
    asset = get_object_or_404(ReportAsset, id=asset_id)
    try:
        _load_report(asset.report_id, request.user)
    except PermissionDenied:
        return _json_error("You do not have permission to modify this report.", status=403)

    if request.method == "DELETE":
        asset.file.delete(save=False)
        asset.delete()
        return JsonResponse({"ok": True})

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return _json_error("Invalid JSON payload.")

    fields_to_update = []
    caption = payload.get("caption")
    if caption is not None:
        asset.caption = str(caption)[:300]
        fields_to_update.append("caption")

    if "order_index" in payload:
        try:
            new_order = int(payload["order_index"])
        except (TypeError, ValueError):
            return _json_error("order_index must be an integer.")
        asset.order_index = max(new_order, 0)
        fields_to_update.append("order_index")

    if not fields_to_update:
        return _json_error("No valid fields to update.")

    asset.save(update_fields=fields_to_update)
    return JsonResponse(serialize_asset(asset))
