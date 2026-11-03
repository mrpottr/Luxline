"""MongoEngine analytics adapter sourcing only this broker's existing records."""

from datetime import date, datetime, time

from backend.app.broker.models.analytics import BrokerAnalyticsEvent
from backend.app.broker.models.lead import BrokerLead, BrokerMessage
from backend.app.broker.models.listing_extension import BrokerListing
from backend.app.broker.models.profile import BrokerProfile, BrokerStatus
from backend.app.broker.repositories.analytics_repository import BrokerAnalyticsRepository
from backend.app.models import Listing, ListingStatus, ModerationStatus, PhoneRevealEvent


class MongoAnalyticsProvider:
    def __init__(self, organization_id: int):
        self.organization_id = organization_id
        self.repository = BrokerAnalyticsRepository(organization_id)

    def is_broker_approved(self) -> bool:
        return bool(BrokerProfile.objects(
            organization_id=self.organization_id, status=BrokerStatus.approved, is_deleted=False,
        ).first())

    def is_public_listing_eligible(self, listing_id: int) -> bool:
        listing = Listing.objects(
            id=listing_id, status=ListingStatus.active,
            moderation_status=ModerationStatus.approved,
        ).only("id").first()
        extension = BrokerListing.objects(listing_id=listing_id, is_deleted=False).first()
        if not listing or not extension:
            return False
        return bool(BrokerProfile.objects(
            organization_id=extension.organization_id,
            status=BrokerStatus.approved,
            is_deleted=False,
        ).first())

    def record_public_listing_event(self, listing_id: int, event_type: str) -> bool:
        """Record public events only for a live listing owned by an approved broker."""
        if not self.is_public_listing_eligible(listing_id):
            return False
        extension = BrokerListing.objects(listing_id=listing_id, is_deleted=False).first()
        if not extension:
            return False
        organization_provider = self if self.organization_id == extension.organization_id else MongoAnalyticsProvider(extension.organization_id)
        if not organization_provider.is_broker_approved():
            return False
        organization_provider.repository.record_listing_event(
            listing_id=listing_id,
            event_type=event_type,
            occurred_at=datetime.utcnow(),
        )
        return True

    def capture_source_events(self, *, start: date, end: date) -> None:
        start_at = datetime.combine(start, time.min)
        end_at = datetime.combine(end, time.max)
        leads = list(BrokerLead.objects(
            organization_id=self.organization_id, is_deleted=False,
            created_at__gte=start_at, created_at__lte=end_at,
        ).no_dereference().limit(100_001))
        if len(leads) > 100_000:
            raise ValueError("Analytics source exceeds 100,000 leads; narrow the date range")
        for lead in leads:
            self.repository.record_source_event(
                source_type="lead", source_id=lead.id, event_type="lead_created",
                listing_id=lead.listing_id, agent_user_id=lead.assigned_member_id,
                occurred_at=lead.created_at, response_seconds=lead.first_response_seconds,
                lead_stage=lead.stage,
            )

        messages = list(BrokerMessage.objects(
            organization_id=self.organization_id, sender_type="agent", is_deleted=False,
            created_at__gte=start_at, created_at__lte=end_at,
        ).no_dereference().limit(100_001))
        if len(messages) > 100_000:
            raise ValueError("Analytics source exceeds 100,000 replies; narrow the date range")
        lead_ids = {message.lead_id for message in messages}
        listing_by_lead = {
            lead.id: lead.listing_id for lead in BrokerLead.objects(
                organization_id=self.organization_id, id__in=list(lead_ids), is_deleted=False,
            ).only("id", "listing_id")
        }
        for message in messages:
            listing_id = listing_by_lead.get(message.lead_id)
            if listing_id is not None:
                self.repository.record_source_event(
                    source_type="message", source_id=message.id, event_type="broker_reply",
                    listing_id=listing_id, agent_user_id=message.sender_user_id,
                    occurred_at=message.created_at,
                )

        listing_ids = list(BrokerListing.objects(
            organization_id=self.organization_id, is_deleted=False,
        ).scalar("listing_id"))
        if listing_ids:
            views = BrokerAnalyticsEvent.objects(
                organization_id=self.organization_id, event_type__in=("listing_view", "listing_impression"),
                listing_id__in=listing_ids, occurred_at__gte=start_at, occurred_at__lte=end_at,
                is_deleted=False,
            ).no_dereference()
            if views.count() > 100_000:
                raise ValueError("Analytics source exceeds 100,000 listing views; narrow the date range")
            for view in views.limit(100_000):
                self.repository.record_source_event(
                    source_type=view.source_type, source_id=view.source_id,
                    event_type=view.event_type, listing_id=view.listing_id,
                    agent_user_id=self._assigned_agent(view.listing_id), occurred_at=view.occurred_at,
                )
            reveals = PhoneRevealEvent.objects(
                listing_id__in=listing_ids, created_at__gte=start_at, created_at__lte=end_at,
            ).no_dereference()
            if reveals.count() > 100_000:
                raise ValueError("Analytics source exceeds 100,000 phone reveals; narrow the date range")
            for reveal in reveals.limit(100_000):
                self.repository.record_source_event(
                    source_type="phone_reveal", source_id=reveal.id, event_type="phone_reveal",
                    listing_id=reveal.listing_id, agent_user_id=None, occurred_at=reveal.created_at,
                )

    def _assigned_agent(self, listing_id: int) -> int | None:
        extension = BrokerListing.objects(
            organization_id=self.organization_id, listing_id=listing_id, is_deleted=False,
        ).only("assigned_agent_id").first()
        return extension.assigned_agent_id if extension else None

    def list_events(self, *, start: date, end: date, listing_id: int | None, agent_id: int | None):
        return self.repository.list_events(start=start, end=end, listing_id=listing_id, agent_id=agent_id)

    def save_daily_rollups(self, rollups: list[dict]):
        self.repository.save_rollups(rollups)

    def list_daily_rollups(self, *, start: date, end: date, listing_id: int | None, agent_id: int | None):
        return self.repository.list_rollups(start=start, end=end, listing_id=listing_id, agent_id=agent_id)
