"""Permission-checked broker billing and promotion operations."""

from datetime import datetime
from typing import Any

from backend.app.broker.application.monetization_ports import MonetizationProvider, PaymentProvider
from backend.app.broker.domain.monetization import calculate_promotion_cost, has_entitlement, payload_hash
from backend.app.broker.domain.roles import BrokerPermission


class BrokerPlanAlreadyExists(ValueError):
    """A global broker plan code must be unique."""


class BrokerPlanIdempotencyConflict(ValueError):
    """A plan create key was reused with a different configuration."""


class MonetizationUseCases:
    def __init__(self, provider: MonetizationProvider, payment: PaymentProvider, permissions: set[BrokerPermission], *, organization_id: int, actor_user_id: int, role: Any, source_ip: str | None = None):
        self.provider = provider
        self.payment = payment
        self.permissions = permissions
        self.organization_id = organization_id
        self.actor_user_id = actor_user_id
        self.role = role
        self.source_ip = source_ip

    def _require(self, permission: BrokerPermission) -> None:
        if permission not in self.permissions:
            raise PermissionError("Missing required broker billing or promotion permission")
        if not self.provider.is_broker_approved():
            raise PermissionError("An approved broker profile is required for billing operations")

    def list_plans(self, *, limit: int, offset: int, sort: str):
        self._require(BrokerPermission.PROMOTION_VIEW)
        return self.provider.get_active_plans(limit=limit, offset=offset, sort=sort)

    def current_subscription(self):
        self._require(BrokerPermission.BILLING_MANAGE)
        return self.provider.get_active_subscription()

    def subscribe(self, *, plan_code: str, idempotency_key: str):
        self._require(BrokerPermission.BILLING_MANAGE)
        plan = self.provider.get_plan(plan_code)
        if not plan or not plan.is_active:
            raise ValueError("Selected broker plan is unavailable")
        digest = payload_hash({"plan_code": plan.code, "version": plan.version})
        reference = self.payment.charge(
            organization_id=self.organization_id,
            amount=plan.price_amount,
            currency=plan.currency,
            idempotency_key=idempotency_key,
        )
        return self.provider.subscribe_transaction(
            plan=plan, payment_reference=reference, idempotency_key=idempotency_key,
            payload_digest=digest, actor_user_id=self.actor_user_id, source_ip=self.source_ip,
        )

    def wallet(self, *, limit: int, offset: int):
        self._require(BrokerPermission.BILLING_MANAGE)
        return {"balance": self.provider.get_wallet_balance(), "ledger": self.provider.list_ledger(limit=limit, offset=offset)}

    def promotion_balance(self):
        self._require(BrokerPermission.PROMOTION_VIEW)
        return self.provider.get_wallet_balance()

    def purchase_credit_pack(self, *, plan_code: str, pack_code: str, idempotency_key: str):
        self._require(BrokerPermission.BILLING_MANAGE)
        plan = self.provider.get_plan(plan_code)
        if not plan or not plan.is_active:
            raise ValueError("Selected credit package is unavailable")
        package = next((row for row in plan.credit_packs if row.get("code") == pack_code), None)
        if not package:
            raise ValueError("Selected credit package is unavailable")
        digest = payload_hash({"plan_code": plan.code, "pack_code": pack_code, "credits": package["credits"]})
        reference = self.payment.charge(
            organization_id=self.organization_id,
            amount=str(package["price_amount"]),
            currency=package["currency"],
            idempotency_key=idempotency_key,
        )
        return self.provider.purchase_credits_transaction(
            package=package, payment_reference=reference, actor_user_id=self.actor_user_id,
            source_ip=self.source_ip, idempotency_key=idempotency_key, payload_digest=digest,
        )

    def list_promotions(self, *, status: str | None, limit: int, offset: int):
        self._require(BrokerPermission.PROMOTION_VIEW)
        if status and status not in {"scheduled", "active", "paused", "cancelled", "expired", "failed"}:
            raise ValueError("Unsupported promotion status")
        return self.provider.list_promotions(status=status, limit=limit, offset=offset)

    def estimate_promotion(self, *, listing_id: int, scope: str, location_code: str, placement_type: str, starts_at: datetime, ends_at: datetime) -> int:
        self._require(BrokerPermission.PROMOTION_MANAGE)
        context = self.provider.get_promotion_context(
            listing_id=listing_id, actor_user_id=self.actor_user_id,
            restrict_to_assigned_agent=self._is_agent(),
        )
        self._validate_promotion_context(context, scope, location_code)
        return calculate_promotion_cost(
            promotion_prices=context["promotion_prices"], scope=scope,
            placement_type=placement_type, starts_at=starts_at, ends_at=ends_at,
        )

    def create_promotion(self, *, payload: dict[str, Any], idempotency_key: str):
        cost = self.estimate_promotion(**payload)
        digest = payload_hash(payload)
        return self.provider.create_promotion_transaction(
            payload=payload, cost=cost, actor_user_id=self.actor_user_id,
            source_ip=self.source_ip, idempotency_key=idempotency_key, payload_digest=digest,
        )

    def _validate_promotion_context(self, context: dict[str, Any] | None, scope: str, location_code: str) -> None:
        if not context:
            raise ValueError("Listing not found in this broker organization")
        if not context["is_live"] or not context["moderation_approved"]:
            raise ValueError("Only live, moderation-approved listings can be promoted")
        if not context["is_approved_broker"] or not context["has_active_plan"]:
            raise ValueError("An approved broker with an active plan is required")
        if not context["owner_consent"] or not context["valid_region_licence"]:
            raise ValueError("Owner consent and a valid regional licence are required")
        if not location_code.strip():
            raise ValueError("Promotion geography is required")
        listing_geography = context.get("listing_geography", {})
        expected_location = listing_geography.get(scope)
        if not expected_location or str(expected_location).strip().casefold() != location_code.strip().casefold():
            raise ValueError("Promotion geography must match the moderated listing location")
        if not has_entitlement(context["entitlements"], "promotions_enabled"):
            raise ValueError("The active broker plan does not include promotions")

    def _is_agent(self) -> bool:
        return getattr(self.role, "value", self.role) == "broker_agent"


class AdminPlanUseCases:
    def __init__(self, repository, *, actor_role: Any):
        self.repository = repository
        self.actor_role = actor_role

    def _require_admin(self):
        if getattr(self.actor_role, "value", self.actor_role) != "super_admin":
            raise PermissionError("Platform administrator access is required")

    def list_plans(self, *, is_active: bool | None, limit: int, offset: int, sort: str):
        self._require_admin()
        return self.repository.list_all_plans(is_active=is_active, limit=limit, offset=offset, sort=sort)

    def create_plan(self, *, payload: dict[str, Any], idempotency_key: str):
        self._require_admin()
        digest = payload_hash(payload)
        repeated = self.repository.get_plan_by_create_key(idempotency_key)
        if repeated:
            if repeated.create_payload_hash != digest:
                raise BrokerPlanIdempotencyConflict("Idempotency key was reused with different plan details")
            return repeated
        if self.repository.get_plan(payload["code"]):
            raise BrokerPlanAlreadyExists("A broker plan with this code already exists")
        return self.repository.save_plan(payload=payload, idempotency_key=idempotency_key, payload_digest=digest)

    def update_plan(self, *, payload: dict[str, Any], code: str):
        self._require_admin()
        if not self.repository.get_plan(code):
            raise LookupError("Broker plan was not found")
        return self.repository.save_plan(payload=payload, code=code)
