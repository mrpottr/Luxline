"""Mongo persistence for organization-scoped broker trust features."""

import hashlib
import json
from datetime import datetime, timezone

from mongoengine.errors import NotUniqueError

from backend.app.broker.models.lead import BrokerLead
from backend.app.broker.models.listing_extension import BrokerListing
from backend.app.broker.models.member import BrokerMember
from backend.app.broker.models.profile import BrokerProfile, BrokerStatus
from backend.app.broker.models.trust import BrokerAuditLog, BrokerBadge, BrokerModerationCase, BrokerReview
from backend.app.models import AgencyProfile, Listing, ListingStatus, ModerationStatus


class BrokerReviewIntegrityViolation(ValueError):
    """A buyer review violated self-review or duplicate-review protections."""


class BrokerTrustRepository:
    def __init__(self, organization_id: int | None):
        self.organization_id = organization_id

    def _tenant(self, organization_id: int | None = None) -> int:
        tenant = organization_id if organization_id is not None else self.organization_id
        if tenant is None or tenant < 1:
            raise ValueError("A broker organization is required for this trust operation")
        return tenant

    def is_approved(self) -> bool:
        if self.organization_id is None:
            return False
        return bool(BrokerProfile.objects(
            organization_id=self.organization_id, status=BrokerStatus.approved, is_deleted=False,
        ).first())

    def list_reviews(self, *, status: str | None, limit: int, offset: int):
        query = BrokerReview.objects(organization_id=self._tenant(), is_deleted=False)
        if status:
            query = query.filter(status=status)
        return list(query.order_by("-created_at", "-id").skip(offset).limit(limit))

    def public_reviews(self, *, limit: int, offset: int):
        return list(BrokerReview.objects(
            organization_id=self._tenant(), status="published", public_consent=True, is_deleted=False,
        ).order_by("-created_at", "-id").skip(offset).limit(limit))

    def submit_review(self, *, buyer_id: int, lead_id: int, rating: int, body: str,
                      public_consent: bool, idempotency_key: str):
        organization_id = self._tenant()
        prior_key = BrokerReview.objects(
            organization_id=organization_id, buyer_id=buyer_id, idempotency_key=idempotency_key,
        ).first()
        if prior_key:
            request_hash = _payload_hash({
                "lead_id": lead_id, "listing_id": prior_key.listing_id, "rating": rating,
                "body": body, "public_consent": public_consent,
            })
            if prior_key.payload_hash != request_hash:
                raise ValueError("Idempotency-Key was already used with different review details")
            return prior_key

        lead = BrokerLead.objects(
            organization_id=organization_id, id=lead_id, buyer_id=buyer_id,
            stage="closed", buyer_contact_consent=True, is_deleted=False,
        ).first()
        if not lead:
            raise ValueError("A closed, consented buyer lead is required to review this broker")
        listing_extension = BrokerListing.objects(
            organization_id=organization_id, listing_id=lead.listing_id, is_deleted=False,
        ).first()
        listing = Listing.objects(id=lead.listing_id, agency_id=organization_id).first() if listing_extension else None
        if not listing:
            raise ValueError("Reviewed listing was not found in this broker organization")
        request_hash = _payload_hash({
            "lead_id": lead_id, "listing_id": listing.id, "rating": rating,
            "body": body, "public_consent": public_consent,
        })
        agency = AgencyProfile.objects(id=organization_id).first()
        if buyer_id == listing.seller_id or (agency and buyer_id == agency.owner_id):
            self._open_case(
                organization_id=organization_id, case_type="self_review", resource_type="listing",
                resource_id=listing.id, actor_user_id=buyer_id,
                reason="A seller or broker owner attempted to review their own listing.", severity="high",
            )
            raise BrokerReviewIntegrityViolation("Self-reviews are not allowed")

        duplicate = BrokerReview.objects(
            organization_id=organization_id, listing_id=listing.id, buyer_id=buyer_id,
        ).first()
        if duplicate:
            self._open_case(
                organization_id=organization_id, case_type="duplicate_review", resource_type="listing",
                resource_id=listing.id, actor_user_id=buyer_id,
                reason="A buyer attempted to submit more than one review for the same listing.", severity="medium",
            )
            raise BrokerReviewIntegrityViolation("A buyer may review a listing only once")

        review = BrokerReview(
            organization_id=organization_id, lead_id=lead_id, listing_id=listing.id,
            buyer_id=buyer_id, rating=rating, body=body, public_consent=public_consent,
            status="pending", idempotency_key=idempotency_key, payload_hash=request_hash,
        )
        try:
            saved = review.save()
        except NotUniqueError:
            duplicate_key = BrokerReview.objects(
                organization_id=organization_id, buyer_id=buyer_id, idempotency_key=idempotency_key,
            ).first()
            if duplicate_key and duplicate_key.payload_hash == request_hash:
                return duplicate_key
            self._open_case(
                organization_id=organization_id, case_type="duplicate_review", resource_type="listing",
                resource_id=listing.id, actor_user_id=buyer_id,
                reason="Concurrent duplicate review submission was detected.", severity="medium",
            )
            raise BrokerReviewIntegrityViolation("A buyer may review a listing only once") from None
        self.append_audit(
            organization_id=organization_id, actor_user_id=buyer_id, actor_role="buyer",
            action="review_submitted", resource_type="review", resource_id=saved.id,
            after_state={"status": saved.status, "rating": saved.rating},
        )
        return saved

    def reply_to_review(self, *, review_id: int, actor_user_id: int, body: str, source_ip: str | None):
        review = BrokerReview.objects(
            organization_id=self._tenant(), id=review_id, is_deleted=False,
        ).first()
        if not review:
            return None
        if review.status != "published":
            raise ValueError("Only published reviews can receive a broker reply")
        before = {"broker_reply": review.broker_reply}
        review.broker_reply = body
        review.replied_by = actor_user_id
        review.replied_at = _utcnow()
        review.save()
        self.append_audit(
            actor_user_id=actor_user_id, actor_role="broker_member", action="review_replied",
            resource_type="review", resource_id=review_id, source_ip=source_ip,
            before_state=before, after_state={"broker_reply": body},
        )
        return review

    def can_reply_to_review(self, *, review_id: int) -> bool:
        review = BrokerReview.objects(
            organization_id=self._tenant(), id=review_id, is_deleted=False,
        ).first()
        return bool(review and review.status == "published")

    def appeal_review(self, *, review_id: int, actor_user_id: int, reason: str, source_ip: str | None):
        review = BrokerReview.objects(
            organization_id=self._tenant(), id=review_id, is_deleted=False,
        ).first()
        if not review:
            return None
        if review.status not in {"published", "rejected"} or review.appeal_state != "none":
            raise ValueError("This review cannot be appealed in its current state")
        before = {"appeal_state": review.appeal_state}
        review.appeal_state = "submitted"
        review.save()
        case = self._open_case(
            organization_id=self._tenant(), case_type="review_appeal", resource_type="review",
            resource_id=review_id, actor_user_id=actor_user_id, reason=reason, severity="medium",
        )
        self.append_audit(
            actor_user_id=actor_user_id, actor_role="broker_member", action="review_appealed",
            resource_type="review", resource_id=review_id, source_ip=source_ip,
            before_state=before, after_state={"appeal_state": review.appeal_state, "case_id": case.id},
        )
        return review

    def can_appeal_review(self, *, review_id: int) -> bool:
        review = BrokerReview.objects(
            organization_id=self._tenant(), id=review_id, is_deleted=False,
        ).first()
        return bool(review and review.status in {"published", "rejected"} and review.appeal_state == "none")

    def badge_inputs(self) -> dict:
        organization_id = self._tenant()
        profile = BrokerProfile.objects(organization_id=organization_id, is_deleted=False).first()
        extensions = list(BrokerListing.objects(organization_id=organization_id, is_deleted=False))
        listing_ids = [row.listing_id for row in extensions]
        live_ids = set(Listing.objects(
            agency_id=organization_id, id__in=listing_ids, status=ListingStatus.active,
            moderation_status=ModerationStatus.approved,
        ).scalar("id")) if listing_ids else set()
        live_extensions = [row for row in extensions if row.listing_id in live_ids]
        average_quality = (sum(row.quality_score for row in live_extensions) / len(live_extensions)) if live_extensions else 0.0
        agents = []
        for member in BrokerMember.objects(organization_id=organization_id, is_active=True, is_deleted=False):
            leads = list(BrokerLead.objects(
                organization_id=organization_id, assigned_member_id=member.user_id,
                is_deleted=False, first_response_seconds__exists=True,
            ).only("first_response_seconds"))
            response_times = [row.first_response_seconds for row in leads if row.first_response_seconds is not None]
            agents.append({
                "user_id": member.user_id,
                "response_count": len(response_times),
                "average_response_seconds": (sum(response_times) / len(response_times)) if response_times else None,
            })
        return {
            "broker_approved": bool(profile and profile.status == BrokerStatus.approved),
            "live_listing_count": len(live_extensions),
            "average_quality": average_quality,
            "agents": agents,
        }

    def save_badge_evaluations(self, evaluations: list[dict]):
        saved = []
        for payload in evaluations:
            values = dict(payload)
            values["badge_code"] = values.pop("code")
            values["criteria_snapshot"] = values.pop("criteria")
            query = BrokerBadge.objects(
                organization_id=self._tenant(), subject_type=values["subject_type"],
                subject_id=values["subject_id"], badge_code=values["badge_code"], is_deleted=False,
            )
            badge = query.first()
            before_awarded = badge.awarded if badge else None
            if badge is None:
                badge = BrokerBadge(organization_id=self._tenant(), **values)
            else:
                for key, value in values.items():
                    setattr(badge, key, value)
            saved.append(badge.save())
            if before_awarded != badge.awarded:
                self.append_audit(
                    actor_user_id=None, actor_role="system", action="badge_evaluated",
                    resource_type="badge", resource_id=badge.id,
                    before_state={"awarded": before_awarded}, after_state={"awarded": badge.awarded},
                    metadata={"badge_code": badge.badge_code, "explanation": badge.explanation,
                              "rule_version": badge.rule_version},
                )
        return saved

    def append_audit(self, *, actor_user_id: int | None, actor_role: str | None, action: str,
                     resource_type: str, resource_id: int | None = None, source_ip: str | None = None,
                     before_state: dict | None = None, after_state: dict | None = None,
                     metadata: dict | None = None, organization_id: int | None = None):
        tenant = self._tenant(organization_id)
        log = BrokerAuditLog(
            organization_id=tenant, actor_user_id=actor_user_id, actor_role=actor_role,
            action=action, resource_type=resource_type, resource_id=resource_id,
            source_ip=source_ip, before_state=before_state or {}, after_state=after_state or {},
            metadata=metadata or {},
        )
        return log.save()

    def list_audit(self, *, action: str | None, actor_user_id: int | None, limit: int, offset: int):
        query = BrokerAuditLog.objects(organization_id=self._tenant(), is_deleted=False)
        if action:
            query = query.filter(action=action)
        if actor_user_id is not None:
            query = query.filter(actor_user_id=actor_user_id)
        return list(query.order_by("-created_at", "-id").skip(offset).limit(limit))

    def list_moderation_cases(self, *, status: str | None, limit: int, offset: int):
        if self.organization_id != 0:
            raise PermissionError("Platform scope is required for global moderation")
        query = BrokerModerationCase.objects(is_deleted=False)
        if status:
            query = query.filter(status=status)
        return list(query.order_by("-created_at", "-id").skip(offset).limit(limit))

    def resolve_moderation_case(self, *, case_id: int, actor_user_id: int, resolution: str, source_ip: str | None):
        if self.organization_id != 0:
            raise PermissionError("Platform scope is required for global moderation")
        case_query = BrokerModerationCase.objects(id=case_id, is_deleted=False)
        case = case_query.first()
        if not case:
            return None
        before = {"status": case.status, "resolution": case.resolution}
        case.status = "resolved"
        case.resolution = resolution
        case.resolved_by = actor_user_id
        case.resolved_at = _utcnow()
        case.save()
        self.append_audit(
            organization_id=case.organization_id, actor_user_id=actor_user_id,
            actor_role="super_admin", action="moderation_case_resolved",
            resource_type="moderation_case", resource_id=case_id,
            source_ip=source_ip, before_state=before, after_state={"status": case.status, "resolution": resolution},
        )
        return case

    def decide_review(self, *, review_id: int, actor_user_id: int, decision: str, notes: str | None, source_ip: str | None):
        if self.organization_id != 0:
            raise PermissionError("Platform scope is required for global moderation")
        review = BrokerReview.objects(id=review_id, is_deleted=False).first()
        if not review:
            return None
        if review.status != "pending":
            raise ValueError("Only pending reviews can be moderated")
        before = {"status": review.status}
        review.status = "published" if decision == "publish" else "rejected"
        review.save()
        self.append_audit(
            organization_id=review.organization_id, actor_user_id=actor_user_id,
            actor_role="super_admin", action="review_moderated", resource_type="review",
            resource_id=review_id, before_state=before,
            source_ip=source_ip,
            after_state={"status": review.status, "decision_notes": notes or ""},
        )
        return review

    def _open_case(self, *, organization_id: int, case_type: str, resource_type: str,
                   resource_id: int, actor_user_id: int | None, reason: str, severity: str):
        case = BrokerModerationCase(
            organization_id=organization_id, case_type=case_type, resource_type=resource_type,
            resource_id=resource_id, actor_user_id=actor_user_id, reason=reason, severity=severity,
        ).save()
        self.append_audit(
            organization_id=organization_id, actor_user_id=actor_user_id,
            actor_role="buyer" if case_type in {"self_review", "duplicate_review"} else "broker_member",
            action="moderation_case_opened", resource_type="moderation_case", resource_id=case.id,
            after_state={"status": case.status, "case_type": case.case_type},
        )
        return case


def _payload_hash(payload: dict) -> str:
    material = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
