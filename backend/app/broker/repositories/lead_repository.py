"""Organization-scoped persistence for broker leads and their supporting records."""

import hashlib
import json
import uuid

from mongoengine.errors import NotUniqueError

from backend.app.broker.models.lead import BrokerLead, BrokerLeadActivity, BrokerMessage, BrokerReplyTemplate
from backend.app.broker.repositories.base_repository import BaseTenantRepository


class BrokerLeadRepository(BaseTenantRepository[BrokerLead]):
    def __init__(self, organization_id: int):
        super().__init__(BrokerLead, organization_id)

    def find_by_inquiry(self, inquiry_id: int) -> BrokerLead | None:
        return self._scoped_query(inquiry_id=inquiry_id).first()

    def list_visible(self, *, assigned_member_id: int | None, stage: str | None, limit: int, offset: int, sort: str):
        filters = {}
        if assigned_member_id is not None:
            filters["assigned_member_id"] = assigned_member_id
        if stage:
            filters["stage"] = stage
        return list(self._scoped_query(**filters).order_by(sort).skip(offset).limit(limit))

    def assignment_counts(self, member_ids: list[int]) -> dict[int, int]:
        return {member_id: self._scoped_query(assigned_member_id=member_id).count() for member_id in member_ids}

    def add_activity(self, *, lead_id: int, actor_user_id: int, activity_type: str, body: str, due_at=None, idempotency_key: str | None = None):
        lead = self.find_by_id(lead_id)
        if not lead:
            return None
        key = idempotency_key or uuid.uuid4().hex
        payload_hash = _payload_hash({"lead_id": lead_id, "activity_type": activity_type, "body": body, "due_at": due_at})
        existing = BrokerLeadActivity.objects(
            organization_id=self.organization_id, idempotency_actor_id=actor_user_id, idempotency_key=key,
        ).first()
        if existing:
            if existing.payload_hash != payload_hash:
                raise ValueError("Idempotency-Key was already used with a different activity payload")
            return existing
        activity = BrokerLeadActivity(
            organization_id=self.organization_id, lead_id=lead_id, actor_user_id=actor_user_id,
            activity_type=activity_type, body=body, due_at=due_at,
            idempotency_actor_id=actor_user_id, idempotency_key=key, payload_hash=payload_hash,
        )
        try:
            return activity.save()
        except NotUniqueError:
            existing = BrokerLeadActivity.objects(
                organization_id=self.organization_id, idempotency_actor_id=actor_user_id, idempotency_key=key,
            ).first()
            if existing and existing.payload_hash == payload_hash:
                return existing
            raise ValueError("Idempotency-Key was already used with a different activity payload")

    def list_activities(self, lead_id: int, limit: int = 100, offset: int = 0):
        if not self.find_by_id(lead_id):
            return None
        return list(BrokerLeadActivity.objects(
            organization_id=self.organization_id, lead_id=lead_id, is_deleted=False,
        ).order_by("-created_at").skip(offset).limit(limit))

    def add_message(self, *, lead: BrokerLead, sender_type: str, sender_user_id: int | None, body: str, idempotency_key: str):
        if lead.organization_id != self.organization_id or not self.find_by_id(lead.id):
            raise PermissionError("Cannot attach a message outside the repository organization")
        actor_id = sender_user_id or 0
        payload_hash = _payload_hash({"lead_id": lead.id, "sender_type": sender_type, "body": body})
        existing = BrokerMessage.objects(
            organization_id=self.organization_id, idempotency_actor_id=actor_id, idempotency_key=idempotency_key,
        ).first()
        if existing:
            if existing.payload_hash != payload_hash:
                raise ValueError("Idempotency-Key was already used with a different message payload")
            return existing
        message = BrokerMessage(
            organization_id=self.organization_id, lead_id=lead.id, sender_type=sender_type,
            sender_user_id=sender_user_id, body=body, idempotency_actor_id=actor_id,
            idempotency_key=idempotency_key, payload_hash=payload_hash,
        )
        try:
            return message.save()
        except NotUniqueError:
            existing = BrokerMessage.objects(
                organization_id=self.organization_id, idempotency_actor_id=actor_id, idempotency_key=idempotency_key,
            ).first()
            if existing and existing.payload_hash == payload_hash:
                return existing
            raise ValueError("Idempotency-Key was already used with a different message payload")

    def list_messages(self, lead_id: int, limit: int = 100, offset: int = 0):
        if not self.find_by_id(lead_id):
            return None
        return list(BrokerMessage.objects(
            organization_id=self.organization_id, lead_id=lead_id, is_deleted=False,
        ).order_by("created_at").skip(offset).limit(limit))

    def find_buyer_leads(self, buyer_id: int, limit: int = 100, offset: int = 0):
        return list(self._scoped_query(
            buyer_id=buyer_id, buyer_contact_consent=True,
        ).order_by("-created_at").skip(offset).limit(limit))

    def find_buyer_lead(self, lead_id: int, buyer_id: int) -> BrokerLead | None:
        return self._scoped_query(
            id=lead_id, buyer_id=buyer_id, buyer_contact_consent=True,
        ).first()


class BrokerTemplateRepository(BaseTenantRepository[BrokerReplyTemplate]):
    def __init__(self, organization_id: int):
        super().__init__(BrokerReplyTemplate, organization_id)

    def list_templates(self, limit: int = 100, offset: int = 0):
        return self.find_all(limit=limit, offset=offset, order_by="title")

    def create_template(self, *, title: str, body: str, created_by: int, idempotency_key: str):
        payload_hash = _payload_hash({"title": title, "body": body})
        existing = self._scoped_query(idempotency_actor_id=created_by, idempotency_key=idempotency_key).first()
        if existing:
            if existing.payload_hash != payload_hash:
                raise ValueError("Idempotency-Key was already used with a different template payload")
            return existing
        try:
            return self.create(
                title=title, body=body, created_by=created_by, idempotency_actor_id=created_by,
                idempotency_key=idempotency_key, payload_hash=payload_hash,
            )
        except NotUniqueError:
            existing = self._scoped_query(idempotency_actor_id=created_by, idempotency_key=idempotency_key).first()
            if existing and existing.payload_hash == payload_hash:
                return existing
            raise ValueError("Idempotency-Key was already used with a different template payload")


def _payload_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
