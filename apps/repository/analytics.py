from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Iterable

from django.utils import timezone

from .models import Thesis
from .readiness import build_publication_readiness

ACTIVE_WORKFLOW_STATUSES = {"SUBMITTED", "IN_REVIEW", "APPROVED", "CHANGES_REQUESTED"}
STATUS_ORDER = [
    "DRAFT",
    "SUBMITTED",
    "IN_REVIEW",
    "CHANGES_REQUESTED",
    "APPROVED",
    "PUBLISHED",
    "ARCHIVED",
]
PIPELINE_ORDER = ["Submitted", "In review", "Approved", "Ready"]


def _to_label(value: str) -> str:
    return value.replace("_", " ").title()


def sanitize_month_window(month_count: int | None) -> int:
    allowed = {3, 6, 12, 24}
    if month_count in allowed:
        return month_count
    return 6


def _build_month_window(month_count: int = 6) -> list[dict[str, str]]:
    month_count = sanitize_month_window(month_count)
    today = timezone.localdate()
    current_month_index = today.year * 12 + today.month - 1
    window: list[dict[str, str]] = []

    for offset in range(month_count):
        month_index = current_month_index - (month_count - offset - 1)
        year = month_index // 12
        month = month_index % 12 + 1
        month_start = date(year, month, 1)
        window.append(
            {
                "key": f"{year}-{month:02d}",
                "month": month_start.strftime("%b"),
            }
        )

    return window


def _to_month_key(value: date | datetime | None) -> str | None:
    if not value:
        return None

    if isinstance(value, datetime) and timezone.is_aware(value):
        value = timezone.localtime(value)

    return f"{value.year}-{value.month:02d}"


def _build_monthly_activity(
    theses: list[Thesis],
    month_count: int = 6,
) -> list[dict[str, int | str]]:
    month_window = _build_month_window(month_count)
    rows = [
        {
            "key": entry["key"],
            "month": entry["month"],
            "created": 0,
            "submitted": 0,
            "published": 0,
        }
        for entry in month_window
    ]
    row_index_by_key = {entry["key"]: index for index, entry in enumerate(month_window)}

    for thesis in theses:
        created_key = _to_month_key(thesis.created_at)
        submitted_key = _to_month_key(thesis.submitted_at)
        published_key = _to_month_key(thesis.published_at)

        if created_key in row_index_by_key:
            rows[row_index_by_key[created_key]]["created"] += 1
        if submitted_key in row_index_by_key:
            rows[row_index_by_key[submitted_key]]["submitted"] += 1
        if published_key in row_index_by_key:
            rows[row_index_by_key[published_key]]["published"] += 1

    return rows


def _build_status_data(theses: list[Thesis]) -> list[dict[str, int | str]]:
    counts = Counter(thesis.status for thesis in theses)
    ordered_rows = [
        {"label": _to_label(status), "count": counts[status]}
        for status in STATUS_ORDER
        if counts[status]
    ]
    remaining_statuses = sorted(status for status in counts if status not in STATUS_ORDER)

    ordered_rows.extend(
        {"label": _to_label(status), "count": counts[status]}
        for status in remaining_statuses
        if counts[status]
    )
    return ordered_rows


def _build_department_data(theses: Iterable[Thesis]) -> list[dict[str, int | str]]:
    counts = Counter(thesis.department.name if thesis.department_id else "Unassigned" for thesis in theses)
    return [
        {"label": label, "count": count}
        for label, count in counts.most_common(6)
    ]


def _build_visibility_data(theses: list[Thesis]) -> list[dict[str, int | str]]:
    counts = Counter(thesis.visibility for thesis in theses)
    return [
        {"label": _to_label(label), "value": value}
        for label, value in counts.most_common()
    ]


def _build_blocker_data(readiness_by_thesis_id: dict) -> list[dict[str, int | str]]:
    blocker_counts: Counter[str] = Counter()

    for readiness in readiness_by_thesis_id.values():
        blocker_counts.update(readiness["blockers"])

    return [
        {"label": label, "count": count}
        for label, count in blocker_counts.most_common(6)
    ]


def _build_pipeline_data(
    theses: list[Thesis],
    readiness_by_thesis_id: dict,
) -> list[dict[str, int | str]]:
    counts = {
        "Submitted": 0,
        "In review": 0,
        "Approved": 0,
        "Ready": 0,
    }

    for thesis in theses:
        if thesis.status == "SUBMITTED":
            counts["Submitted"] += 1
        if thesis.status == "IN_REVIEW":
            counts["In review"] += 1
        if thesis.status == "APPROVED":
            counts["Approved"] += 1
        if readiness_by_thesis_id[thesis.id]["can_publish_now"]:
            counts["Ready"] += 1

    return [
        {"label": label, "count": counts[label]}
        for label in PIPELINE_ORDER
    ]


def _build_readiness_split(
    theses: list[Thesis],
    readiness_by_thesis_id: dict,
) -> list[dict[str, int | str]]:
    ready = sum(
        1 for thesis in theses if readiness_by_thesis_id[thesis.id]["can_publish_now"]
    )
    blocked = sum(
        1
        for thesis in theses
        if not readiness_by_thesis_id[thesis.id]["can_publish_now"]
        and readiness_by_thesis_id[thesis.id]["blocker_count"] > 0
    )
    in_workflow = sum(1 for thesis in theses if thesis.status in ACTIVE_WORKFLOW_STATUSES)

    return [
        {"label": label, "value": value}
        for label, value in [
            ("Ready", ready),
            ("Blocked", blocked),
            ("In workflow", in_workflow),
        ]
        if value > 0
    ]


def build_repository_analytics_overview(
    theses_queryset,
    month_count: int = 6,
) -> dict:
    month_count = sanitize_month_window(month_count)
    theses = list(theses_queryset)
    readiness_by_thesis_id = {
        thesis.id: build_publication_readiness(thesis)
        for thesis in theses
    }
    active_workflow_theses = [
        thesis for thesis in theses if thesis.status in ACTIVE_WORKFLOW_STATUSES
    ]

    total_records = len(theses)
    published_count = sum(1 for thesis in theses if thesis.status == "PUBLISHED")
    active_workflow_count = len(active_workflow_theses)
    ready_count = sum(
        1 for thesis in theses if readiness_by_thesis_id[thesis.id]["can_publish_now"]
    )
    blocked_count = sum(
        1
        for thesis in theses
        if not readiness_by_thesis_id[thesis.id]["can_publish_now"]
        and readiness_by_thesis_id[thesis.id]["blocker_count"] > 0
    )

    return {
        "as_of": timezone.localdate(),
        "window_months": month_count,
        "summary": {
            "total_records": total_records,
            "published_count": published_count,
            "active_workflow_count": active_workflow_count,
            "ready_count": ready_count,
            "blocked_count": blocked_count,
        },
        "monthly_activity": _build_monthly_activity(theses, month_count),
        "status_data": _build_status_data(theses),
        "department_data": _build_department_data(theses),
        "active_department_data": _build_department_data(active_workflow_theses),
        "visibility_data": _build_visibility_data(theses),
        "blocker_data": _build_blocker_data(readiness_by_thesis_id),
        "pipeline_data": _build_pipeline_data(theses, readiness_by_thesis_id),
        "readiness_split": _build_readiness_split(theses, readiness_by_thesis_id),
    }
