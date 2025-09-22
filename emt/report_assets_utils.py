from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Final, Set

from .models import ReportAsset

if TYPE_CHECKING:  # pragma: no cover - import for type hints only
    from core.models import Report

MAX_UPLOAD_SIZE: Final[int] = 10 * 1024 * 1024  # 10 MB
IMAGE_EXTENSIONS: Final[Set[str]] = {".jpg", ".jpeg", ".png", ".webp"}
PDF_EXTENSIONS: Final[Set[str]] = {".pdf"}
ALLOWED_EXTENSIONS: Final[Set[str]] = IMAGE_EXTENSIONS | PDF_EXTENSIONS
SINGLETON_CATEGORIES: Final[Set[str]] = {
    ReportAsset.Category.EVALUATION,
    ReportAsset.Category.FEEDBACK,
}
BROCHURE_LIMIT: Final[int] = 4


def serialize_asset(asset: ReportAsset) -> Dict[str, Any]:
    """Return a serialisable representation of a report asset."""

    return {
        "id": asset.id,
        "category": asset.category,
        "src": asset.file.url if asset.file else "",
        "caption": asset.caption or "",
        "order_index": asset.order_index,
        "meta": asset.meta or {},
    }


def build_annexures_payload(report: "Report") -> Dict[str, Any]:
    """Compose the annexures payload expected by the IQAC preview hydrator."""

    def items(cat: str) -> List[Dict[str, Any]]:
        assets = report.assets.filter(category=cat).order_by("order_index", "id")
        results: List[Dict[str, Any]] = []
        for asset in assets:
            entry = {
                "src": asset.file.url if asset.file else "",
                "caption": asset.caption or "—",
            }
            if asset.meta:
                entry["meta"] = asset.meta
            results.append(entry)
        return results

    def first_item(cat: str) -> Dict[str, Any]:
        entries = items(cat)
        if entries:
            return entries[0]
        return {"src": "", "caption": "—"}

    payload = {
        "photos": items(ReportAsset.Category.PHOTO),
        "brochure_pages": items(ReportAsset.Category.BROCHURE),
        "communication": {
            "subject": getattr(report, "communication_subject", "") or "",
            "date": getattr(report, "communication_date", "") or "",
            "files": items(ReportAsset.Category.COMMUNICATION),
            "volunteer_list": getattr(report, "volunteer_rows", []) or [],
        },
        "worksheets": items(ReportAsset.Category.WORKSHEET),
        "evaluation_sheet": first_item(ReportAsset.Category.EVALUATION),
        "feedback_form": first_item(ReportAsset.Category.FEEDBACK),
    }
    return {"annexures": payload}
