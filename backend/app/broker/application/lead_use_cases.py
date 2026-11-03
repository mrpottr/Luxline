"""Permission-checked application workflows for broker leads and inbox messages."""

from datetime import datetime, timezone
from typing import Any

from backend.app.broker.application.lead_ports import LeadProvider
from backend.app.broker.domain.lead_routing import select_assignee
from backend.app.broker.domain.roles import BrokerPermission
from backend.app.broker.application.ports import RateLimiter


LEAD_STAGES = {"new", "contacted", "qualified", "lost", "closed"}
LEAD_SORTS = {"created_at", "-created_at", "score", "-score"}


class LeadUseCases:
    def __init__(self, provider: LeadProvider, permissions: set[BrokerPermission], *, role: Any, actor_user_id: int, organization_id: int, rate_limiter: RateLimiter | None = None, message_limit: int = 30):
        self.provider = provider
        self.permissions = permissions
        self.role = role
        self.actor_user_id = actor_user_id
        self.organization_id = organization_id
        self.rate_limiter = rate_limiter
        self.message_limit = message_limit

    def _rate_limit_message(self, actor_id: int, scope: str):
        if self.rate_limiter and not self.rate_limiter.consume(
            f"{scope}:{self.organization_id}:{actor_id}", maximum=self.message_limit, window_seconds=60,
        ):
            raise TooManyLeadMessages("Message rate limit exceeded; retry later")

    def _require(self, permission: BrokerPermission):
        if permission not in self.permissions:
            raise PermissionError("Missing required broker permission")
        if not self.provider.is_broker_approved():
            raise PermissionError("An approved broker profile is required to use lead operations")

    def _visible_assignee(self) -> int | None:
        return self.actor_user_id if getattr(self.role, "value", self.role) == "broker_agent" else None

    def list_leads(self, *, stage: str | None, limit: int, offset: int, sort: str):
        permission = BrokerPermission.LEAD_VIEW_OWN if self._visible_assignee() else BrokerPermission.LEAD_VIEW_ALL
        self._require(permission)
        if stage is not None and stage not in LEAD_STAGES:
            raise ValueError("Unsupported lead stage")
        if sort not in LEAD_SORTS:
            raise ValueError("Unsupported lead sort")
        self.provider.sync_public_inquiries()
        return self.provider.list_leads(
            assigned_member_id=self._visible_assignee(), stage=stage, limit=limit, offset=offset, sort=sort,
        )

    def assign(self, lead_id: int, member_id: int):
        self._require(BrokerPermission.LEAD_ASSIGN)
        lead = self.provider.assign_lead(lead_id, member_id)
        if lead:
            self.provider.add_activity(
                lead_id=lead_id, actor_user_id=self.actor_user_id,
                activity_type="assigned", body=f"Lead assigned to member {member_id}",
            )
        return lead

    def set_stage(self, lead_id: int, stage: str):
        permission = BrokerPermission.LEAD_VIEW_OWN if self._visible_assignee() else BrokerPermission.LEAD_VIEW_ALL
        self._require(permission)
        if stage not in LEAD_STAGES:
            raise ValueError("Unsupported lead stage")
        lead = self.provider.get_lead(lead_id)
        if not lead or (self._visible_assignee() and lead.assigned_member_id != self.actor_user_id):
            return None
        updated = self.provider.update_stage(lead_id, stage)
        if updated:
            self.provider.add_activity(
                lead_id=lead_id, actor_user_id=self.actor_user_id,
                activity_type="stage_changed", body=f"Lead stage changed to {stage}",
            )
        return updated

    def set_spam_flag(self, lead_id: int, spam_flag: bool):
        self._require(BrokerPermission.LEAD_VIEW_ALL)
        if not self.provider.get_lead(lead_id):
            return None
        updated = self.provider.update_spam_flag(lead_id, spam_flag)
        if updated:
            self.provider.add_activity(
                lead_id=lead_id, actor_user_id=self.actor_user_id,
                activity_type="spam_flagged" if spam_flag else "spam_cleared",
                body="Lead spam state updated",
            )
        return updated

    def add_activity(self, lead_id: int, *, activity_type: str, body: str, due_at=None, idempotency_key: str):
        self._require(BrokerPermission.LEAD_VIEW_OWN if self._visible_assignee() else BrokerPermission.LEAD_VIEW_ALL)
        if activity_type not in {"note", "task", "reminder"}:
            raise ValueError("Unsupported lead activity type")
        lead = self.provider.get_lead(lead_id)
        if not lead or (self._visible_assignee() and lead.assigned_member_id != self.actor_user_id):
            return None
        return self.provider.add_activity(
            lead_id=lead_id, actor_user_id=self.actor_user_id, activity_type=activity_type,
            body=body, due_at=due_at, idempotency_key=idempotency_key,
        )

    def list_activities(self, lead_id: int, *, limit: int, offset: int):
        self._require(BrokerPermission.LEAD_VIEW_OWN if self._visible_assignee() else BrokerPermission.LEAD_VIEW_ALL)
        lead = self.provider.get_lead(lead_id)
        if not lead or (self._visible_assignee() and lead.assigned_member_id != self.actor_user_id):
            return None
        return self.provider.list_activities(lead_id, limit, offset)

    def list_messages(self, lead_id: int, *, limit: int, offset: int):
        self._require(BrokerPermission.LEAD_VIEW_OWN if self._visible_assignee() else BrokerPermission.LEAD_VIEW_ALL)
        lead = self.provider.get_lead(lead_id)
        if not lead or (self._visible_assignee() and lead.assigned_member_id != self.actor_user_id):
            return None
        return self.provider.list_messages(lead_id, limit, offset)

    def send_agent_message(self, lead_id: int, body: str, idempotency_key: str):
        self._require(BrokerPermission.LEAD_MESSAGE)
        lead = self.provider.get_lead(lead_id)
        if not lead or not lead.buyer_contact_consent or lead.buyer_id is None:
            return None
        if self._visible_assignee() and lead.assigned_member_id != self.actor_user_id:
            return None
        self._rate_limit_message(self.actor_user_id, "agent")
        message = self.provider.add_message(
            lead_id=lead_id, sender_type="agent", sender_user_id=self.actor_user_id,
            body=body, idempotency_key=idempotency_key,
        )
        if lead.first_response_at is None:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            lead.first_response_at = now
            lead.first_response_seconds = max(0, int((now - lead.created_at).total_seconds()))
            self.provider.update_stage(lead_id, "contacted")
        return message

    def list_buyer_leads(self, buyer_id: int, *, limit: int, offset: int):
        if not self.provider.is_broker_approved():
            raise PermissionError("Broker conversations are unavailable")
        return self.provider.list_buyer_leads(buyer_id, limit, offset)

    def list_buyer_messages(self, lead_id: int, buyer_id: int, *, limit: int, offset: int):
        if not self.provider.is_broker_approved():
            raise PermissionError("Broker conversations are unavailable")
        lead = self.provider.get_buyer_lead(lead_id, buyer_id)
        if not lead:
            return None
        return self.provider.list_buyer_messages(lead, limit, offset)

    def send_buyer_message(self, lead_id: int, buyer_id: int, body: str, idempotency_key: str):
        if not self.provider.is_broker_approved():
            raise PermissionError("Broker conversations are unavailable")
        if not self.provider.get_buyer_lead(lead_id, buyer_id):
            return None
        self._rate_limit_message(buyer_id, "buyer")
        lead = self.provider.get_buyer_lead(lead_id, buyer_id)
        return self.provider.add_buyer_message(lead=lead, buyer_id=buyer_id, body=body, idempotency_key=idempotency_key)

    def list_templates(self, *, limit: int, offset: int):
        self._require(BrokerPermission.LEAD_MESSAGE)
        return self.provider.list_templates(limit, offset)

    def create_template(self, *, title: str, body: str, idempotency_key: str):
        self._require(BrokerPermission.LEAD_MESSAGE)
        return self.provider.create_template(
            title=title, body=body, created_by=self.actor_user_id, idempotency_key=idempotency_key,
        )


class TooManyLeadMessages(Exception):
    """Raised when an actor exceeds the broker messaging rate limit."""
