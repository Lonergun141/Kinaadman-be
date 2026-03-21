from __future__ import annotations

from typing import Any, Optional

from .models import Thesis

READY = "READY"
PENDING = "PENDING"
MISSING = "MISSING"
BLOCKED = "BLOCKED"


def _build_check(
    *,
    check_id: str,
    label: str,
    status: str,
    detail: str,
    blocking: bool = True,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "label": label,
        "status": status,
        "detail": detail,
        "blocking": blocking,
    }


def _get_latest_adviser_review(thesis: Thesis):
    adviser_reviews = [
        review
        for review in thesis.reviews.all()
        if review.reviewer_membership_id and review.reviewer_membership.role == "ADVISER"
    ]
    adviser_reviews.sort(key=lambda review: review.created_at, reverse=True)
    return adviser_reviews[0] if adviser_reviews else None


def _get_main_pdf(thesis: Thesis):
    for thesis_file in thesis.files.all():
        if thesis_file.is_current and thesis_file.kind == "MAIN_PDF":
            return thesis_file
    return None


def build_publication_readiness(thesis: Thesis) -> dict[str, Any]:
    latest_adviser_review = _get_latest_adviser_review(thesis)
    main_pdf = _get_main_pdf(thesis)
    advisers = list(thesis.advisers.all())
    panel_members = thesis.panel_members or []
    checklist: list[dict[str, Any]] = []

    workflow_ready = thesis.status in {"APPROVED", "PUBLISHED"}
    if workflow_ready:
        workflow_detail = (
            "The thesis has already been approved for publication."
            if thesis.status == "APPROVED"
            else "The thesis is already published in the repository."
        )
        workflow_status = READY
    elif thesis.status in {"SUBMITTED", "IN_REVIEW"}:
        workflow_detail = "Review is still in progress before publication approval."
        workflow_status = PENDING
    else:
        workflow_detail = "The thesis must reach approved status before it can be published."
        workflow_status = MISSING
    checklist.append(
        _build_check(
            check_id="workflow",
            label="Workflow approval",
            status=workflow_status,
            detail=workflow_detail,
        )
    )

    checklist.append(
        _build_check(
            check_id="main_pdf",
            label="Main manuscript uploaded",
            status=READY if main_pdf else MISSING,
            detail=(
                "A current main PDF is attached to the thesis record."
                if main_pdf
                else "Upload the final main PDF before publishing."
            ),
        )
    )

    checklist.append(
        _build_check(
            check_id="adviser_assignment",
            label="Adviser assigned",
            status=READY if advisers else MISSING,
            detail=(
                "At least one adviser is linked to this thesis."
                if advisers
                else "Assign an adviser to this thesis record."
            ),
        )
    )

    if latest_adviser_review is None:
        adviser_status = MISSING
        adviser_detail = "An adviser recommendation has not been recorded yet."
        adviser_decision = None
        adviser_note = None
        adviser_by = None
        adviser_at = None
    else:
        adviser_decision = latest_adviser_review.decision
        adviser_note = latest_adviser_review.comment or None
        adviser_by = latest_adviser_review.reviewer_membership.user.email
        adviser_at = latest_adviser_review.created_at
        if latest_adviser_review.decision == "APPROVED":
            adviser_status = READY
            adviser_detail = "An adviser has recommended this thesis for the next stage."
        elif latest_adviser_review.decision == "CHANGES_REQUESTED":
            adviser_status = BLOCKED
            adviser_detail = "The latest adviser decision requests changes before publishing."
        else:
            adviser_status = BLOCKED
            adviser_detail = "The latest adviser decision does not recommend publishing."

    checklist.append(
        _build_check(
            check_id="adviser_recommendation",
            label="Adviser recommendation",
            status=adviser_status,
            detail=adviser_detail,
        )
    )

    checklist.append(
        _build_check(
            check_id="panel_members",
            label="Panel members listed",
            status=READY if panel_members else MISSING,
            detail=(
                "Panel members are recorded on the thesis metadata."
                if panel_members
                else "Record the defense panel members before publishing."
            ),
        )
    )

    if thesis.panel_approval_status == "APPROVED":
        panel_status = READY
        panel_detail = "Panel approval has been confirmed for publishing."
    elif thesis.panel_approval_status == "REJECTED":
        panel_status = BLOCKED
        panel_detail = "Panel approval was marked as rejected."
    else:
        panel_status = PENDING
        panel_detail = "Record panel approval before publishing this thesis."

    checklist.append(
        _build_check(
            check_id="panel_approval",
            label="Panel approval recorded",
            status=panel_status,
            detail=panel_detail,
        )
    )

    checklist.append(
        _build_check(
            check_id="defense_date",
            label="Defense date recorded",
            status=READY if thesis.defense_date else MISSING,
            detail=(
                "A defense date is stored on the thesis record."
                if thesis.defense_date
                else "Add the defense date before publishing."
            ),
        )
    )

    checklist.append(
        _build_check(
            check_id="rights_license",
            label="Rights and license set",
            status=READY if thesis.rights_license.strip() else MISSING,
            detail=(
                "Rights or license information is ready for repository display."
                if thesis.rights_license.strip()
                else "Provide the repository rights or license statement."
            ),
        )
    )

    if thesis.visibility == "EMBARGOED":
        checklist.append(
            _build_check(
                check_id="embargo",
                label="Embargo date set",
                status=READY if thesis.embargo_until else MISSING,
                detail=(
                    "The embargo end date is recorded."
                    if thesis.embargo_until
                    else "Set an embargo end date for embargoed publication."
                ),
            )
        )

    ready_checks = [check for check in checklist if check["status"] == READY]
    blockers = [
        check["label"]
        for check in checklist
        if check["blocking"] and check["status"] != READY
    ]
    can_publish_now = thesis.status == "APPROVED" and not blockers

    return {
        "can_publish_now": can_publish_now,
        "readiness_score": int(round((len(ready_checks) / len(checklist)) * 100)) if checklist else 0,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "adviser_recommendation_status": adviser_status,
        "adviser_review_decision": adviser_decision,
        "adviser_recommendation_note": adviser_note,
        "adviser_recommendation_by": adviser_by,
        "adviser_recommendation_at": adviser_at,
        "panel_approval_status": thesis.panel_approval_status,
        "panel_approval_note": thesis.panel_approval_note,
        "checklist": checklist,
    }


def get_publication_blockers(thesis: Thesis) -> list[str]:
    readiness = build_publication_readiness(thesis)
    return readiness["blockers"]
