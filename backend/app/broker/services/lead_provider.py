"""MongoEngine adapter for tenant-scoped broker lead and inbox workflows."""

from mongoengine.errors import NotUniqueError

from backend.app.broker.domain.lead_routing import score_lead, select_assignee
from backend.app.broker.domain.roles import BrokerRole
from backend.app.broker.models.lead import BrokerLead, BrokerMessage, BrokerReplyTemplate
from backend.app.broker.models.listing_extension import BrokerListing
from backend.app.broker.models.member import BrokerMember
from backend.app.broker.models.profile import BrokerProfile, BrokerStatus
from backend.app.broker.repositories.lead_repository import BrokerLeadRepository, BrokerTemplateRepository
from backend.app.models import Inquiry, Listing


class MongoLeadProvider:
    def __init__(self, organization_id: int):
        self.organization_id = organization_id
        self.leads = BrokerLeadRepository(organization_id)
        self.templates = BrokerTemplateRepository(organization_id)

    def is_broker_approved(self) -> bool:
        return bool(BrokerProfile.objects(
            organization_id=self.organization_id, status=BrokerStatus.approved, is_deleted=False,
        ).first())

    def sync_public_inquiries(self) -> None:
        """Import existing seller-directed inquiries without changing their legacy API."""
        extensions = BrokerListing.objects(organization_id=self.organization_id, is_deleted=False)
        assignments = {row.listing_id: row.assigned_agent_id for row in extensions}
        listing_ids = list(assignments)
        if not listing_ids:
            return
        members = list(BrokerMember.objects(
            organization_id=self.organization_id, is_active=True, is_deleted=False,
        ))
        agents = [member.user_id for member in members if member.role == BrokerRole.broker_agent]
        active_assignees = [member.user_id for member in members if member.role != BrokerRole.broker_viewer]
        managers = [member.user_id for member in members if member.role in {BrokerRole.broker_manager, BrokerRole.broker_owner}]
        counts = self.leads.assignment_counts(agents)
        for inquiry in Inquiry.objects(listing_id__in=listing_ids).order_by("created_at"):
            existing_lead = self.leads.find_by_inquiry(inquiry.id)
            if existing_lead:
                self._ensure_initial_message(existing_lead, inquiry)
                continue
            listing_agent = assignments.get(inquiry.listing_id)
            assignee = select_assignee(
                listing_agent_id=listing_agent,
                rule_agent_id=None,
                active_agent_ids=agents,
                active_member_ids=active_assignees,
                assignment_counts=counts,
                manager_id=min(managers) if managers else None,
            )
            lead = BrokerLead(
                organization_id=self.organization_id,
                inquiry_id=inquiry.id,
                listing_id=inquiry.listing_id,
                buyer_id=inquiry.buyer_id,
                buyer_name=inquiry.name,
                buyer_email=inquiry.email,
                buyer_phone=inquiry.phone,
                initial_message=inquiry.message,
                score=score_lead(
                    has_phone=bool(inquiry.phone),
                    has_account=inquiry.buyer_id is not None,
                    message=inquiry.message,
                ),
                stage="contacted" if inquiry.status == "replied" else "new",
                assigned_member_id=assignee,
                first_response_at=inquiry.replied_at,
                first_response_seconds=(
                    max(0, int((inquiry.replied_at - inquiry.created_at).total_seconds()))
                    if inquiry.replied_at and inquiry.created_at else None
                ),
                buyer_contact_consent=True,
            )
            try:
                lead.save()
                self._ensure_initial_message(lead, inquiry)
                if assignee in counts:
                    counts[assignee] += 1
            except NotUniqueError:
                # Another broker request imported the same legacy inquiry concurrently.
                continue

    @staticmethod
    def _ensure_initial_message(lead: BrokerLead, inquiry: Inquiry) -> None:
        if BrokerMessage.objects(
            organization_id=lead.organization_id, source_inquiry_id=inquiry.id,
        ).first():
            return
        try:
            BrokerMessage(
                organization_id=lead.organization_id,
                lead_id=lead.id,
                sender_type="buyer",
                sender_user_id=inquiry.buyer_id,
                body=inquiry.message,
                source_inquiry_id=inquiry.id,
                idempotency_actor_id=inquiry.buyer_id or 0,
                idempotency_key=f"source-inquiry-{inquiry.id}",
                payload_hash=_payload_hash({"lead_id": lead.id, "message": inquiry.message}),
            ).save()
        except NotUniqueError:
            # Concurrent inbox refreshes may both materialize the same inquiry.
            return

    def list_leads(self, *, assigned_member_id, stage, limit, offset, sort):
        return self.leads.list_visible(
            assigned_member_id=assigned_member_id, stage=stage, limit=limit, offset=offset, sort=sort,
        )

    def get_lead(self, lead_id: int):
        return self.leads.find_by_id(lead_id)

    def assign_lead(self, lead_id: int, member_id: int):
        member = BrokerMember.objects(
            organization_id=self.organization_id, user_id=member_id, is_active=True, is_deleted=False,
        ).first()
        if not member or member.role == BrokerRole.broker_viewer:
            raise ValueError("Assigned member must be an active broker owner, manager, or agent")
        return self.leads.update(lead_id, assigned_member_id=member_id)

    def update_stage(self, lead_id: int, stage: str):
        return self.leads.update(lead_id, stage=stage)

    def update_spam_flag(self, lead_id: int, spam_flag: bool):
        return self.leads.update(lead_id, spam_flag=spam_flag)

    def add_activity(self, **kwargs):
        return self.leads.add_activity(**kwargs)

    def list_activities(self, lead_id: int, limit: int, offset: int):
        return self.leads.list_activities(lead_id, limit, offset)

    def add_message(self, **kwargs):
        lead = self.leads.find_by_id(kwargs["lead_id"])
        if not lead:
            return None
        message = self.leads.add_message(lead=lead, **{key: value for key, value in kwargs.items() if key != "lead_id"})
        if kwargs["sender_type"] == "agent" and lead.first_response_at is None:
            lead.first_response_at = message.created_at
            lead.first_response_seconds = max(0, int((message.created_at - lead.created_at).total_seconds()))
            lead.save()
        return message

    def list_messages(self, lead_id: int, limit: int, offset: int):
        return self.leads.list_messages(lead_id, limit, offset)

    def list_buyer_leads(self, buyer_id: int, limit: int, offset: int):
        return self.leads.find_buyer_leads(buyer_id, limit, offset)

    def get_buyer_lead(self, lead_id: int, buyer_id: int):
        return self.leads.find_buyer_lead(lead_id, buyer_id)

    def list_buyer_messages(self, lead: BrokerLead, limit: int, offset: int):
        return list(BrokerMessage.objects(
            organization_id=lead.organization_id, lead_id=lead.id, is_deleted=False,
        ).order_by("created_at").skip(offset).limit(limit))

    def add_buyer_message(self, *, lead: BrokerLead, buyer_id: int, body: str, idempotency_key: str):
        return self.leads.add_message(
            lead=lead, sender_type="buyer", sender_user_id=buyer_id, body=body, idempotency_key=idempotency_key,
        )

    def list_templates(self, limit: int, offset: int):
        return self.templates.list_templates(limit, offset)

    def create_template(self, *, title: str, body: str, created_by: int, idempotency_key: str):
        return self.templates.create_template(
            title=title, body=body, created_by=created_by, idempotency_key=idempotency_key,
        )


def _payload_hash(payload: dict) -> str:
    import hashlib
    import json
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
