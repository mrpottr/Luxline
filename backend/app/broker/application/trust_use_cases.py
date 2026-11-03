"""Permission-checked broker trust and platform moderation workflows."""

from datetime import datetime, timezone
from typing import Any

from backend.app.broker.application.trust_ports import TrustProvider
from backend.app.broker.domain.roles import BrokerPermission
from backend.app.broker.domain.trust import (
    BADGE_RULE_VERSION,
    evaluate_organization_badges,
    evaluate_responsive_agent,
    validate_review,
)


REVIEW_STATUSES = {"pending", "published", "rejected"}
MODERATION_STATUSES = {"open", "resolved"}


class BrokerTrustUseCases:
    def __init__(self, provider: TrustProvider, permissions: set[BrokerPermission], *, organization_id: int,
                 actor_user_id: int, role: Any, source_ip: str | None = None):
        self.provider = provider
        self.permissions = permissions
        self.organization_id = organization_id
        self.actor_user_id = actor_user_id
        self.role = role
        self.source_ip = source_ip

    def _require(self, permission: BrokerPermission):
        if permission not in self.permissions:
            raise PermissionError("Missing required broker trust permission")
        if not self.provider.is_approved():
            raise PermissionError("An approved broker profile is required for trust operations")

    def reply(self, *, review_id: int, body: str):
        self._require(BrokerPermission.REVIEWS_MANAGE)
        normalized = body.strip()
        if not normalized or len(normalized) > 2000:
            raise ValueError("Review replies must contain between 1 and 2000 characters")
        if not self.provider.can_reply_to_review(review_id=review_id):
            raise ValueError("Only published reviews can receive a broker reply")
        return self.provider.reply_to_review(
            review_id=review_id, actor_user_id=self.actor_user_id,
            body=normalized, source_ip=self.source_ip,
        )

    def appeal(self, *, review_id: int, reason: str):
        self._require(BrokerPermission.REVIEWS_MANAGE)
        normalized = reason.strip()
        if not normalized or len(normalized) > 1000:
            raise ValueError("Appeal reason must contain between 1 and 1000 characters")
        if not self.provider.can_appeal_review(review_id=review_id):
            raise ValueError("This review cannot be appealed in its current state")
        return self.provider.appeal_review(
            review_id=review_id, actor_user_id=self.actor_user_id,
            reason=normalized, source_ip=self.source_ip,
        )

    def _evaluate_badges(self):
        data = self.provider.badge_inputs()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        evaluations = [
            {"subject_type": "organization", "subject_id": self.organization_id,
             "rule_version": BADGE_RULE_VERSION, "evaluated_at": now, **item.__dict__}
            for item in evaluate_organization_badges(
                broker_approved=data["broker_approved"],
                live_listing_count=data["live_listing_count"],
                average_quality=data["average_quality"],
            )
        ]
        evaluations.extend(
            {"subject_type": "member", "subject_id": item["user_id"],
             "rule_version": BADGE_RULE_VERSION, "evaluated_at": now,
             **evaluate_responsive_agent(
                 response_count=item["response_count"],
                 average_response_seconds=item["average_response_seconds"],
             ).__dict__}
            for item in data["agents"]
        )
        return self.provider.save_badge_evaluations(evaluations)

    def list_reviews(self, *, status: str | None, limit: int, offset: int):
        self._require(BrokerPermission.REVIEWS_MANAGE)
        if status and status not in REVIEW_STATUSES:
            raise ValueError("Unsupported review status")
        return self.provider.list_reviews(status=status, limit=limit, offset=offset)

    def list_badges(self):
        self._require(BrokerPermission.ANALYTICS_VIEW)
        return self._evaluate_badges()

    def audit(self, *, action: str | None, actor_user_id: int | None, limit: int, offset: int):
        self._require(BrokerPermission.AUDIT_VIEW)
        if action and len(action) > 64:
            raise ValueError("Audit action filter is too long")
        return self.provider.list_audit(
            action=action, actor_user_id=actor_user_id, limit=limit, offset=offset,
        )

    def record_data_export(self, *, dimension: str, date_from: str, date_to: str):
        self._require(BrokerPermission.ANALYTICS_VIEW)
        self.provider.append_audit(
            actor_user_id=self.actor_user_id, actor_role=getattr(self.role, "value", self.role),
            action="analytics_exported", resource_type="analytics_export", source_ip=self.source_ip,
            metadata={"dimension": dimension, "date_from": date_from, "date_to": date_to},
        )


class BuyerReviewUseCases:
    def __init__(self, provider: TrustProvider, *, organization_id: int, buyer_user_id: int):
        self.provider = provider
        self.organization_id = organization_id
        self.buyer_user_id = buyer_user_id

    def submit(self, *, lead_id: int, rating: int, body: str, public_consent: bool, idempotency_key: str):
        if not self.provider.is_approved():
            raise PermissionError("Broker reviews are unavailable")
        payload = validate_review(rating=rating, body=body, public_consent=public_consent)
        return self.provider.submit_review(
            buyer_id=self.buyer_user_id, lead_id=lead_id, idempotency_key=idempotency_key, **payload,
        )


class PublicTrustUseCases:
    def __init__(self, provider: TrustProvider):
        self.provider = provider

    def reviews(self, *, limit: int, offset: int):
        if not self.provider.is_approved():
            return []
        return self.provider.public_reviews(limit=limit, offset=offset)


class AdminTrustUseCases:
    def __init__(self, provider: TrustProvider, *, actor_user_id: int, actor_role: Any, source_ip: str | None = None):
        self.provider = provider
        self.actor_user_id = actor_user_id
        self.actor_role = actor_role
        self.source_ip = source_ip

    def _require_admin(self):
        if getattr(self.actor_role, "value", self.actor_role) != "super_admin":
            raise PermissionError("Platform administrator access is required")

    def list_cases(self, *, status: str | None, limit: int, offset: int):
        self._require_admin()
        if status and status not in MODERATION_STATUSES:
            raise ValueError("Unsupported moderation case status")
        return self.provider.list_moderation_cases(status=status, limit=limit, offset=offset)

    def resolve_case(self, *, case_id: int, resolution: str):
        self._require_admin()
        normalized = resolution.strip()
        if not normalized or len(normalized) > 1000:
            raise ValueError("Resolution must contain between 1 and 1000 characters")
        return self.provider.resolve_moderation_case(
            case_id=case_id, actor_user_id=self.actor_user_id, resolution=normalized,
            source_ip=self.source_ip,
        )

    def decide_review(self, *, review_id: int, decision: str, notes: str | None):
        self._require_admin()
        if decision not in {"publish", "reject"}:
            raise ValueError("Review decision must be publish or reject")
        return self.provider.decide_review(
            review_id=review_id, actor_user_id=self.actor_user_id,
            decision=decision, notes=notes, source_ip=self.source_ip,
        )
