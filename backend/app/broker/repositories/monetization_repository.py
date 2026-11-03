"""Tenant-scoped broker monetization storage and Mongo transaction boundary."""

from datetime import datetime, timedelta, timezone
from typing import Any, Type

from mongoengine import Document
from mongoengine.connection import get_connection
from mongoengine.connection import get_db
from pymongo import ReturnDocument
from pymongo.errors import OperationFailure, ConfigurationError

from backend.app.broker.domain.monetization import validate_plan
from backend.app.broker.models.listing_extension import BrokerListing
from backend.app.broker.models.monetization import (
    BrokerCreditAccount,
    BrokerCreditLedger,
    BrokerPlan,
    BrokerPromotion,
    BrokerSubscription,
)
from backend.app.broker.models.profile import BrokerProfile, BrokerStatus
from backend.app.models import (
    AgencyProfile,
    Listing,
    ListingStatus,
    ModerationStatus,
    Subscription,
    SubscriptionStatus,
)


class InsufficientBrokerCredits(ValueError):
    """The tenant wallet cannot cover a requested promotion."""


class MonetizationIdempotencyConflict(ValueError):
    """An idempotency key was reused with a different request body."""


class BrokerMonetizationRepository:
    def __init__(self, organization_id: int):
        self.organization_id = organization_id

    @staticmethod
    def _global_plans():
        return BrokerPlan.objects(organization_id=0, is_deleted=False)

    def is_broker_approved(self) -> bool:
        return bool(BrokerProfile.objects(
            organization_id=self.organization_id, status=BrokerStatus.approved, is_deleted=False,
        ).first())

    def list_active_plans(self, *, limit: int, offset: int, sort: str) -> list[BrokerPlan]:
        return list(self._global_plans().filter(is_active=True).order_by(sort).skip(offset).limit(limit))

    def get_plan(self, code: str) -> BrokerPlan | None:
        return self._global_plans().filter(code=code).first()

    def get_plan_by_create_key(self, idempotency_key: str) -> BrokerPlan | None:
        return self._global_plans().filter(create_idempotency_key=idempotency_key).first()

    def list_all_plans(self, *, is_active: bool | None, limit: int, offset: int, sort: str) -> list[BrokerPlan]:
        BrokerPlan.ensure_indexes()
        query = self._global_plans()
        if is_active is not None:
            query = query.filter(is_active=is_active)
        return list(query.order_by(sort).skip(offset).limit(limit))

    def save_plan(self, *, payload: dict[str, Any], code: str | None = None, idempotency_key: str | None = None, payload_digest: str | None = None) -> BrokerPlan:
        normalized = validate_plan(**{
            key: value for key, value in payload.items()
            if key != "is_active"
        })
        normalized["is_active"] = bool(payload.get("is_active", True))
        BrokerPlan.ensure_indexes()
        plan = self._global_plans().filter(code=code or normalized["code"]).first()
        if plan is None:
            plan_data = {"organization_id": 0, **normalized}
            if idempotency_key is not None:
                plan_data["create_idempotency_key"] = idempotency_key
                plan_data["create_payload_hash"] = payload_digest
            plan = BrokerPlan(**plan_data)
        else:
            for key, value in normalized.items():
                setattr(plan, key, value)
            plan.version += 1
        return plan.save()

    def active_subscription(self) -> BrokerSubscription | None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return BrokerSubscription.objects(
            organization_id=self.organization_id, status="active", is_deleted=False,
            starts_at__lte=now, ends_at__gt=now,
        ).order_by("-ends_at").first()

    def wallet_balance(self) -> int:
        wallet = BrokerCreditAccount.objects(
            organization_id=self.organization_id, is_deleted=False,
        ).first()
        return wallet.balance if wallet else 0

    def list_ledger(self, *, limit: int, offset: int) -> list[BrokerCreditLedger]:
        return list(BrokerCreditLedger.objects(
            organization_id=self.organization_id, is_deleted=False,
        ).order_by("-created_at", "-id").skip(offset).limit(limit))

    def list_promotions(self, *, status: str | None, limit: int, offset: int) -> list[BrokerPromotion]:
        filters = {"organization_id": self.organization_id, "is_deleted": False}
        if status:
            filters["status"] = status
        return list(BrokerPromotion.objects(**filters).order_by("-created_at", "-id").skip(offset).limit(limit))

    def promotion_context(self, *, listing_id: int, actor_user_id: int, restrict_to_assigned_agent: bool) -> dict[str, Any] | None:
        extension_query = BrokerListing.objects(
            organization_id=self.organization_id, listing_id=listing_id, is_deleted=False,
        )
        if restrict_to_assigned_agent:
            extension_query = extension_query.filter(assigned_agent_id=actor_user_id)
        extension = extension_query.first()
        agency = AgencyProfile.objects(id=self.organization_id).first()
        listing = Listing.objects(id=listing_id, agency_id=self.organization_id).first() if extension else None
        if not extension or not listing:
            return None
        profile = BrokerProfile.objects(
            organization_id=self.organization_id, is_deleted=False,
        ).first()
        subscription = self.active_subscription()
        existing_subscriptions = Subscription.objects(
            business_user_id=agency.owner_id if agency else -1,
            status=SubscriptionStatus.active,
        )
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        legacy_active = any(
            (not row.starts_at or row.starts_at <= now) and (not row.ends_at or row.ends_at > now)
            for row in existing_subscriptions
        )
        plan = self.get_plan(subscription.plan_code) if subscription else None
        return {
            "is_live": listing.status == ListingStatus.active,
            "moderation_approved": listing.moderation_status == ModerationStatus.approved,
            "is_approved_broker": bool(profile and profile.status == BrokerStatus.approved),
            "has_active_plan": bool(subscription or legacy_active),
            "entitlements": subscription.entitlements_snapshot if subscription else (plan.entitlements if plan else {}),
            "promotion_prices": plan.promotion_prices if plan else self._default_promotion_prices(),
            "listing_geography": {
                "city": listing.location_city,
                "country": listing.location_country,
                "locality": (listing.attributes or {}).get("locality"),
                "province": (listing.attributes or {}).get("province"),
            },
            "owner_consent": extension.owner_consent,
            "valid_region_licence": bool(profile and any(
                str(region).casefold() == str(listing.location_country or "").casefold() and bool(value)
                for region, value in profile.licences.items()
            )),
        }

    @staticmethod
    def _default_promotion_prices() -> dict:
        # Empty config deliberately makes paid promotion unavailable until an admin sets prices.
        return {}

    def create_promotion_transaction(self, *, payload: dict[str, Any], cost: int, actor_user_id: int, idempotency_key: str, payload_digest: str) -> BrokerPromotion:
        self._ensure_indexes()
        payload = dict(payload)
        for field in ("starts_at", "ends_at"):
            value = payload[field]
            if value.tzinfo is not None:
                payload[field] = value.astimezone(timezone.utc).replace(tzinfo=None)
        collection = BrokerPromotion._get_collection()
        existing = collection.find_one({
            "organization_id": self.organization_id, "idempotency_key": idempotency_key,
            "is_deleted": False,
        })
        if existing:
            if existing.get("payload_hash") != payload_digest:
                raise MonetizationIdempotencyConflict("Idempotency key was reused with different promotion details")
            return BrokerPromotion._from_son(existing)

        try:
            with self._session() as session:
                with session.start_transaction():
                    existing = collection.find_one({
                        "organization_id": self.organization_id, "idempotency_key": idempotency_key,
                        "is_deleted": False,
                    }, session=session)
                    if existing:
                        if existing.get("payload_hash") != payload_digest:
                            raise MonetizationIdempotencyConflict("Idempotency key was reused with different promotion details")
                        return BrokerPromotion._from_son(existing)
                    balance = self._change_wallet_balance(-cost, session=session)
                    promotion_id = self._next_id(BrokerPromotion, session=session)
                    promotion = BrokerPromotion(
                        organization_id=self.organization_id, id=promotion_id,
                        **payload, credits_spent=cost,
                        status=("scheduled" if payload["starts_at"] > datetime.now(timezone.utc).replace(tzinfo=None) else "active"),
                        idempotency_key=idempotency_key,
                        payload_hash=payload_digest,
                    )
                    raw_promotion = promotion.to_mongo()
                    collection.insert_one(raw_promotion, session=session)
                    self._insert_ledger(
                        session=session, entry_type="promotion_spend", amount=-cost,
                        balance_after=balance, actor_user_id=actor_user_id,
                        promotion_id=promotion_id, reference=None,
                        idempotency_key=idempotency_key, payload_digest=payload_digest,
                    )
            return promotion
        except (OperationFailure, ConfigurationError) as error:
            existing = collection.find_one({
                "organization_id": self.organization_id, "idempotency_key": idempotency_key,
                "is_deleted": False,
            })
            if existing:
                if existing.get("payload_hash") != payload_digest:
                    raise MonetizationIdempotencyConflict("Idempotency key was reused with different promotion details") from error
                return BrokerPromotion._from_son(existing)
            raise RuntimeError("Broker credit operations require MongoDB replica-set transaction support") from error

    def purchase_credits_transaction(self, *, package: dict[str, Any], payment_reference: str, actor_user_id: int, idempotency_key: str, payload_digest: str) -> BrokerCreditLedger:
        self._ensure_indexes()
        ledger_collection = BrokerCreditLedger._get_collection()
        existing = ledger_collection.find_one({
            "organization_id": self.organization_id, "idempotency_key": idempotency_key,
            "is_deleted": False,
        })
        if existing:
            self._assert_same_payload(existing, payload_digest)
            return BrokerCreditLedger._from_son(existing)
        try:
            with self._session() as session:
                with session.start_transaction():
                    existing = ledger_collection.find_one({
                        "organization_id": self.organization_id, "idempotency_key": idempotency_key,
                        "is_deleted": False,
                    }, session=session)
                    if existing:
                        self._assert_same_payload(existing, payload_digest)
                        return BrokerCreditLedger._from_son(existing)
                    balance = self._change_wallet_balance(int(package["credits"]), session=session)
                    entry = self._insert_ledger(
                        session=session, entry_type="credit_purchase", amount=int(package["credits"]),
                        balance_after=balance, actor_user_id=actor_user_id, promotion_id=None,
                        reference=payment_reference, idempotency_key=idempotency_key,
                        payload_digest=payload_digest,
                    )
            return entry
        except (OperationFailure, ConfigurationError) as error:
            existing = ledger_collection.find_one({
                "organization_id": self.organization_id, "idempotency_key": idempotency_key,
                "is_deleted": False,
            })
            if existing:
                self._assert_same_payload(existing, payload_digest)
                return BrokerCreditLedger._from_son(existing)
            raise RuntimeError("Broker credit operations require MongoDB replica-set transaction support") from error

    def subscribe_transaction(self, *, plan: BrokerPlan, payment_reference: str, idempotency_key: str, payload_digest: str) -> BrokerSubscription:
        self._ensure_indexes()
        collection = BrokerSubscription._get_collection()
        existing = collection.find_one({
            "organization_id": self.organization_id, "idempotency_key": idempotency_key,
            "is_deleted": False,
        })
        if existing:
            self._assert_same_payload(existing, payload_digest)
            return BrokerSubscription._from_son(existing)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        try:
            with self._session() as session:
                with session.start_transaction():
                    existing = collection.find_one({
                        "organization_id": self.organization_id, "idempotency_key": idempotency_key,
                        "is_deleted": False,
                    }, session=session)
                    if existing:
                        self._assert_same_payload(existing, payload_digest)
                        return BrokerSubscription._from_son(existing)
                    collection.update_many(
                        {"organization_id": self.organization_id, "status": "active", "ends_at": {"$gt": now}},
                        {"$set": {"status": "superseded", "ends_at": now}},
                        session=session,
                    )
                    subscription = BrokerSubscription(
                        organization_id=self.organization_id,
                        id=self._next_id(BrokerSubscription, session=session),
                        plan_code=plan.code, status="active", starts_at=now,
                        ends_at=now + timedelta(days=plan.billing_period_days),
                        plan_version=plan.version, listing_limit_snapshot=plan.listing_limit,
                        entitlements_snapshot=dict(plan.entitlements),
                        payment_reference=payment_reference, idempotency_key=idempotency_key,
                        idempotency_payload_hash=payload_digest,
                    )
                    collection.insert_one(subscription.to_mongo(), session=session)
            return subscription
        except (OperationFailure, ConfigurationError) as error:
            existing = collection.find_one({
                "organization_id": self.organization_id, "idempotency_key": idempotency_key,
                "is_deleted": False,
            })
            if existing:
                self._assert_same_payload(existing, payload_digest)
                return BrokerSubscription._from_son(existing)
            raise RuntimeError("Broker subscription operations require MongoDB replica-set transaction support") from error

    def _change_wallet_balance(self, amount: int, *, session) -> int:
        account_collection = BrokerCreditAccount._get_collection()
        account = BrokerCreditAccount(organization_id=self.organization_id, id=self.organization_id)
        account_raw = account.to_mongo()
        # Avoid update-path conflicts with the matching $inc and $set operators.
        account_raw.pop("balance", None)
        account_raw.pop("updated_at", None)
        account_collection.update_one(
            {"_id": self.organization_id}, {"$setOnInsert": account_raw},
            upsert=True, session=session,
        )
        filters: dict[str, Any] = {"_id": self.organization_id}
        if amount < 0:
            filters["balance"] = {"$gte": -amount}
        updated = account_collection.find_one_and_update(
            filters,
            {"$inc": {"balance": amount}, "$set": {"updated_at": datetime.now(timezone.utc).replace(tzinfo=None)}},
            return_document=ReturnDocument.AFTER, session=session,
        )
        if not updated:
            raise InsufficientBrokerCredits("The broker wallet does not have enough credits")
        return int(updated["balance"])

    def _insert_ledger(self, *, session, entry_type: str, amount: int, balance_after: int, actor_user_id: int, promotion_id: int | None, reference: str | None, idempotency_key: str, payload_digest: str) -> BrokerCreditLedger:
        entry = BrokerCreditLedger(
            organization_id=self.organization_id, id=self._next_id(BrokerCreditLedger, session=session),
            entry_type=entry_type, amount=amount, balance_after=balance_after,
            actor_user_id=actor_user_id, promotion_id=promotion_id, reference=reference,
            idempotency_key=idempotency_key, payload_hash=payload_digest,
        )
        BrokerCreditLedger._get_collection().insert_one(entry.to_mongo(), session=session)
        return entry

    @staticmethod
    def _next_id(model: Type[Document], *, session) -> int:
        sequence_id = f"{model._get_collection_name()}.id"
        counters = BrokerCreditAccount._fields["id"].collection_name
        collection = get_db(alias="default")[counters]
        collection.update_one(
            {"_id": sequence_id}, {"$setOnInsert": {"next": 0}}, upsert=True, session=session,
        )
        counter = collection.find_one_and_update(
            {"_id": sequence_id}, {"$inc": {"next": 1}},
            return_document=ReturnDocument.AFTER, session=session,
        )
        return int(counter["next"])

    def _session(self):
        return get_connection(alias="default").start_session()

    @staticmethod
    def _ensure_indexes():
        for model in (BrokerCreditAccount, BrokerCreditLedger, BrokerPromotion, BrokerSubscription, BrokerPlan):
            model.ensure_indexes()

    @staticmethod
    def _assert_same_payload(row: dict, payload_digest: str) -> None:
        if row.get("payload_hash", row.get("idempotency_payload_hash")) != payload_digest:
            raise MonetizationIdempotencyConflict("Idempotency key was reused with different billing details")
