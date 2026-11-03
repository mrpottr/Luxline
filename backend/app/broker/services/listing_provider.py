"""MongoEngine adapter for broker listing operations."""

import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from backend.app.broker.domain.quality_score import QualityScoreCalculator
from backend.app.broker.models.listing_extension import BrokerListing
from backend.app.broker.models.listing_revision import BrokerListingRevision
from backend.app.broker.repositories.listing_revision_repository import BrokerListingRevisionRepository
from backend.app.broker.models.branch import BrokerBranch
from backend.app.broker.models.member import BrokerMember
from backend.app.broker.models.profile import BrokerProfile, BrokerStatus
from backend.app.broker.repositories.listing_repository import BrokerListingRepository
from backend.app.models import (
    AgencyProfile, Listing, ListingCategory, ListingMedia, ListingStatus,
    ModerationStatus, Subscription, SubscriptionStatus,
)
from backend.app.utils import slugify


class MongoListingProvider:
    """Concrete persistence adapter. All broker extension reads are tenant scoped."""

    def __init__(self, organization_id: int):
        self.organization_id = organization_id
        self.repository = BrokerListingRepository(organization_id)
        self.revision_repository = BrokerListingRevisionRepository(organization_id)

    def _validate_assignment(self, assigned_agent_id: int | None, branch_id: int | None) -> None:
        if assigned_agent_id is not None:
            member = BrokerMember.objects(
                organization_id=self.organization_id,
                user_id=assigned_agent_id,
                is_active=True,
                is_deleted=False,
            ).first()
            owner = assigned_agent_id == self.organization_id or AgencyProfile.objects(
                id=self.organization_id,
                owner_id=assigned_agent_id,
            ).first()
            if not member and not owner:
                raise ValueError("Assigned agent must be an active member of this organization")
        if branch_id is not None and not BrokerBranch.objects(
            organization_id=self.organization_id,
            id=branch_id,
            is_deleted=False,
        ).first():
            raise ValueError("Branch must belong to this organization")

    @staticmethod
    def _view(extension: BrokerListing, listing: Listing | None = None) -> dict[str, Any]:
        listing = listing or Listing.objects(id=extension.listing_id, agency_id=extension.organization_id).first()
        media = list(ListingMedia.objects(listing_id=extension.listing_id).order_by("sort_order")) if listing else []
        details = {item.get("url"): item for item in extension.media_items}
        media_items = [
            {
                "url": item.url,
                "media_type": details.get(item.url, {}).get("media_type", item.media_type),
                "sort_order": item.sort_order,
                "alt_text": details.get(item.url, {}).get("alt_text", ""),
                "moderation_state": details.get(item.url, {}).get("moderation_state", "pending"),
            }
            for item in media
        ]
        return {
            "id": extension.id,
            "organization_id": extension.organization_id,
            "listing_id": extension.listing_id,
            "title": listing.title if listing else "",
            "description": listing.description if listing else "",
            "category": listing.category.value if listing else "",
            "price": listing.price if listing else 0,
            "currency": listing.currency if listing else "",
            "location_country": listing.location_country if listing else "",
            "location_city": listing.location_city if listing else "",
            "location_address": listing.location_address if listing else None,
            "status": listing.status.value if listing else "archived",
            "moderation_status": listing.moderation_status.value if listing else "pending",
            "assigned_agent_id": extension.assigned_agent_id,
            "branch_id": extension.branch_id,
            "owner_consent": extension.owner_consent,
            "quality_score": extension.quality_score,
            "quality_rating": extension.quality_rating,
            "quality_suggestions": extension.quality_suggestions,
            "urgent_flag": extension.urgent_flag,
            "photos": [item.url for item in media if item.media_type == "image"],
            "media": media_items,
            "created_at": extension.created_at,
            "updated_at": extension.updated_at,
        }

    def list_listings(self, *, filters: dict[str, Any], limit: int, offset: int, sort: str) -> list[dict[str, Any]]:
        return [self._view(item) for item in self.repository.list_filtered(filters=filters, limit=limit, offset=offset, sort=sort)]

    def is_broker_approved(self) -> bool:
        return bool(BrokerProfile.objects(
            organization_id=self.organization_id,
            status=BrokerStatus.approved,
            is_deleted=False,
        ).first())

    @staticmethod
    def list_categories() -> list[str]:
        return [category.value for category in ListingCategory]

    def create_listing(self, *, payload: dict[str, Any], user_id: int, idempotency_key: str) -> dict[str, Any]:
        existing = self.repository.find_by_idempotency_key(idempotency_key)
        if existing:
            payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
            if existing.idempotency_payload_hash != payload_hash:
                raise ValueError("Idempotency-Key was already used with a different listing payload")
            return self._view(existing)
        assigned_agent_id = payload.get("assigned_agent_id") or user_id
        self._validate_assignment(assigned_agent_id, payload.get("branch_id"))
        title = payload["title"]
        listing = Listing(
            seller_id=user_id,
            agency_id=self.organization_id,
            title=title,
            slug=f"{slugify(title)}-{uuid.uuid4().hex[:8]}",
            description=payload.get("description") or "",
            category=ListingCategory(payload["category"].lower()),
            status=ListingStatus.draft,
            moderation_status=ModerationStatus.pending,
            price=payload["price"],
            currency=payload["currency"],
            location_country=payload["location_country"],
            location_city=payload["location_city"],
            location_address=payload.get("location_address"),
            attributes=payload.get("attributes") or {},
        ).save()
        media_items = payload.get("media") or [
            {"url": url, "media_type": "image", "sort_order": order, "alt_text": ""}
            for order, url in enumerate(payload.get("photos") or [])
        ]
        try:
            for item in media_items:
                ListingMedia(
                    listing_id=listing.id,
                    media_type=item["media_type"],
                    url=item["url"],
                    sort_order=item["sort_order"],
                ).save()
            score, rating, suggestions = QualityScoreCalculator.calculate(
                title=title,
                description=payload.get("description") or "",
                price=payload["price"],
                photo_count=len(media_items),
                has_location=bool(payload.get("location_city") and payload.get("location_country")),
                has_specs=bool(payload.get("attributes")),
                owner_consent=payload.get("owner_consent", False),
            )
            payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
            extension = self.repository.create(
                listing_id=listing.id,
                assigned_agent_id=assigned_agent_id,
                branch_id=payload.get("branch_id"),
                owner_consent=payload.get("owner_consent", False),
                quality_score=score,
                quality_rating=rating,
                quality_suggestions=suggestions,
                media_items=[{**item, "moderation_state": "pending"} for item in media_items],
                urgent_flag=payload.get("urgent_flag", False),
                idempotency_key=idempotency_key,
                idempotency_payload_hash=payload_hash,
            )
        except Exception:
            ListingMedia.objects(listing_id=listing.id).delete()
            listing.delete()
            raise
        return self._view(extension, listing)

    def update_listing(self, *, listing_id: int, changes: dict[str, Any], actor_user_id: int, restrict_to_assigned_agent: bool) -> dict[str, Any] | None:
        extension = self.repository.find_listing(listing_id, actor_user_id if restrict_to_assigned_agent else None)
        listing = Listing.objects(id=listing_id, agency_id=self.organization_id).first() if extension else None
        if not extension or not listing:
            return None
        self._validate_assignment(changes.get("assigned_agent_id"), changes.get("branch_id"))
        BrokerListingRevision(
            organization_id=self.organization_id,
            listing_id=listing_id,
            version=extension.version,
            actor_user_id=actor_user_id,
            snapshot={
                "title": listing.title,
                "description": listing.description,
                "price": listing.price,
                "currency": listing.currency,
                "location_country": listing.location_country,
                "location_city": listing.location_city,
                "assigned_agent_id": extension.assigned_agent_id,
                "branch_id": extension.branch_id,
                "owner_consent": extension.owner_consent,
                "urgent_flag": extension.urgent_flag,
                "quality_score": extension.quality_score,
                "quality_rating": extension.quality_rating,
                "media": self._view(extension, listing)["media"],
            },
        ).save()
        for field in ("title", "description", "price", "currency", "location_country", "location_city", "location_address", "attributes"):
            if field in changes and changes[field] is not None:
                setattr(listing, field, changes[field])
        if "title" in changes and changes["title"]:
            listing.slug = f"{slugify(changes['title'])}-{uuid.uuid4().hex[:8]}"
        listing.save()
        for field in ("assigned_agent_id", "branch_id", "owner_consent", "urgent_flag"):
            if field in changes and changes[field] is not None:
                setattr(extension, field, changes[field])
        if changes.get("media") is not None:
            requested = list(changes["media"])
            existing_media = list(ListingMedia.objects(listing_id=listing.id).order_by("sort_order", "id"))
            existing_urls = {item.url for item in existing_media}
            requested_urls = {item["url"] for item in requested}
            for index, item in enumerate(requested):
                match = ListingMedia.objects(listing_id=listing.id, url=item["url"]).first()
                if match:
                    match.media_type = item["media_type"]
                    match.sort_order = index
                    match.save()
                else:
                    ListingMedia(
                        listing_id=listing.id,
                        media_type=item["media_type"],
                        url=item["url"],
                        sort_order=index,
                    ).save()
            # Legacy ListingMedia has no soft-delete field. Retain omitted media so a
            # broker edit cannot silently remove public inventory media.
            for item in existing_media:
                if item.url not in requested_urls:
                    item.sort_order = len(requested) + item.sort_order
                    item.save()
            requested.extend({
                "url": item.url,
                "media_type": item.media_type,
                "sort_order": len(requested) + index,
                "alt_text": "",
            } for index, item in enumerate(item for item in existing_media if item.url not in requested_urls))
            extension.media_items = [{**item, "moderation_state": "pending"} for item in requested]
        elif changes.get("photos") is not None:
            existing_media = list(ListingMedia.objects(listing_id=listing.id).order_by("sort_order", "id"))
            unused = list(existing_media)
            for index, url in enumerate(changes["photos"]):
                match = next((item for item in unused if item.url == url), None)
                if match:
                    unused.remove(match)
                    match.sort_order = index
                    match.save()
                else:
                    ListingMedia(listing_id=listing.id, media_type="image", url=url, sort_order=index).save()
            for index, item in enumerate(unused, start=len(changes["photos"])):
                item.sort_order = index
                item.save()
            extension.media_items = [
                {"url": item.url, "media_type": item.media_type, "sort_order": item.sort_order, "alt_text": "", "moderation_state": "pending"}
                for item in ListingMedia.objects(listing_id=listing.id).order_by("sort_order")
            ]
        score, rating, suggestions = QualityScoreCalculator.calculate(
            title=listing.title,
            description=listing.description or "",
            price=listing.price,
            photo_count=ListingMedia.objects(listing_id=listing.id).count(),
            has_location=bool(listing.location_city and listing.location_country),
            has_specs=bool(listing.attributes),
            owner_consent=extension.owner_consent,
        )
        extension.quality_score, extension.quality_rating, extension.quality_suggestions = score, rating, suggestions
        extension.version += 1
        extension.save()
        return self._view(extension, listing)

    def set_listing_status(self, *, listing_id: int, status: str, actor_user_id: int, restrict_to_assigned_agent: bool) -> dict[str, Any] | None:
        extension = self.repository.find_listing(listing_id, actor_user_id if restrict_to_assigned_agent else None)
        listing = Listing.objects(id=listing_id, agency_id=self.organization_id).first() if extension else None
        if not extension or not listing:
            return None
        if status == "archived":
            listing.status = ListingStatus.draft
            listing.save()
            extension.is_deleted = True
            extension.save()
        else:
            listing.status = ListingStatus(status)
            listing.save()
        return self._view(extension, listing)

    def get_publish_context(self, *, listing_id: int, actor_user_id: int, restrict_to_assigned_agent: bool) -> dict[str, Any] | None:
        extension = self.repository.find_listing(listing_id, actor_user_id if restrict_to_assigned_agent else None)
        listing = Listing.objects(id=listing_id, agency_id=self.organization_id).first() if extension else None
        if not extension or not listing:
            return None
        profile = BrokerProfile.objects(organization_id=self.organization_id, is_deleted=False).first()
        agency = AgencyProfile.objects(id=self.organization_id).first()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        subscriptions = Subscription.objects(
            business_user_id=agency.owner_id if agency else -1,
            status=SubscriptionStatus.active,
        )
        active_plan = any(
            (not subscription.starts_at or subscription.starts_at <= now)
            and (not subscription.ends_at or subscription.ends_at > now)
            for subscription in subscriptions
        )
        licences = profile.licences if profile else {}
        return {
            "is_approved_broker": bool(profile and profile.status == BrokerStatus.approved),
            "has_active_plan": active_plan,
            "valid_region_licence": any(
                str(region).casefold() == str(listing.location_country or "").casefold() and bool(value)
                for region, value in licences.items()
            ),
            "owner_consent": extension.owner_consent,
            "category": listing.category.value,
            "price": listing.price,
            "currency": listing.currency,
            "quality_score": extension.quality_score,
            "media_count": ListingMedia.objects(listing_id=listing.id).count(),
        }

    def list_revisions(self, *, listing_id: int, actor_user_id: int, restrict_to_assigned_agent: bool, limit: int):
        extension = self.repository.find_listing(listing_id, actor_user_id if restrict_to_assigned_agent else None)
        if not extension:
            return None
        return self.revision_repository.list_for_listing(listing_id, limit=limit)
