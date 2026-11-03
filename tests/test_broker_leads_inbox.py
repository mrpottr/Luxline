"""Milestone M5 domain and application tests for broker lead workflows."""

import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

from backend.app.broker.application.lead_use_cases import LeadUseCases, TooManyLeadMessages
from backend.app.broker.domain.lead_routing import score_lead, select_assignee
from backend.app.broker.domain.roles import BrokerPermission, BrokerRole
from backend.app.broker.api.lead_dependencies import get_buyer_lead_use_cases, get_lead_use_cases
from backend.app.broker.api.leads import router as leads_router
from backend.app.broker.api.inbox import router as inbox_router


class TestLeadDomainRules(unittest.TestCase):
    def test_assignment_priority_is_listing_rule_round_robin_then_manager(self):
        self.assertEqual(select_assignee(
            listing_agent_id=7, rule_agent_id=8, active_agent_ids=[7, 8],
            assignment_counts={7: 9, 8: 0}, manager_id=9,
        ), 7)
        self.assertEqual(select_assignee(
            listing_agent_id=9, rule_agent_id=8, active_agent_ids=[7, 8],
            active_member_ids=[7, 8, 9], assignment_counts={7: 0, 8: 0}, manager_id=10,
        ), 9)
        self.assertEqual(select_assignee(
            listing_agent_id=None, rule_agent_id=8, active_agent_ids=[7, 8],
            assignment_counts={7: 0, 8: 5}, manager_id=9,
        ), 8)
        self.assertEqual(select_assignee(
            listing_agent_id=None, rule_agent_id=None, active_agent_ids=[8, 7],
            assignment_counts={7: 2, 8: 1}, manager_id=9,
        ), 8)
        self.assertEqual(select_assignee(
            listing_agent_id=None, rule_agent_id=None, active_agent_ids=[],
            assignment_counts={}, manager_id=9,
        ), 9)

    def test_lead_score_is_bounded_and_explainable_from_inquiry_fields(self):
        self.assertEqual(score_lead(has_phone=False, has_account=False, message="Hi"), 35)
        self.assertGreater(score_lead(has_phone=True, has_account=True, message="Interested in viewing the property this weekend."), 35)
        self.assertLessEqual(score_lead(has_phone=True, has_account=True, message="x" * 500), 100)


class TestLeadUseCases(unittest.TestCase):
    def setUp(self):
        self.provider = Mock()
        self.provider.is_broker_approved.return_value = True
        self.provider.get_lead.return_value = SimpleNamespace(
            id=31, assigned_member_id=44, buyer_id=9, buyer_contact_consent=True,
            first_response_at=None, created_at=datetime(2025, 1, 1),
        )
        self.agent = LeadUseCases(
            self.provider, {BrokerPermission.LEAD_VIEW_OWN, BrokerPermission.LEAD_MESSAGE},
            role=BrokerRole.broker_agent, actor_user_id=44, organization_id=101,
        )

    def test_list_imports_inquiries_and_scopes_agents_to_assigned_leads(self):
        self.agent.list_leads(stage="new", limit=20, offset=0, sort="-created_at")
        self.provider.sync_public_inquiries.assert_called_once_with()
        self.provider.list_leads.assert_called_once_with(
            assigned_member_id=44, stage="new", limit=20, offset=0, sort="-created_at",
        )

    def test_every_lead_use_case_requires_permission(self):
        cases = LeadUseCases(self.provider, set(), role=BrokerRole.broker_agent, actor_user_id=44, organization_id=101)
        with self.assertRaises(PermissionError):
            cases.list_leads(stage=None, limit=50, offset=0, sort="-created_at")
        self.provider.sync_public_inquiries.assert_not_called()

    def test_agent_cannot_update_unassigned_lead(self):
        self.provider.get_lead.return_value = SimpleNamespace(assigned_member_id=99)
        self.assertIsNone(self.agent.set_stage(31, "qualified"))
        self.provider.update_stage.assert_not_called()

    def test_invalid_stage_is_rejected(self):
        with self.assertRaises(ValueError):
            self.agent.set_stage(31, "deleted")

    def test_agent_cannot_message_lead_without_account_consent_link(self):
        self.provider.get_lead.return_value.buyer_id = None
        self.assertIsNone(self.agent.send_agent_message(31, "Hello", "message-key-0001"))
        self.provider.add_message.assert_not_called()


class TestLeadApi(unittest.TestCase):
    def setUp(self):
        self.provider = Mock()
        self.provider.is_broker_approved.return_value = True
        self.lead = SimpleNamespace(
            id=31, organization_id=101, inquiry_id=77, listing_id=500, buyer_id=9,
            buyer_name="Buyer", buyer_email="buyer@example.com", buyer_phone=None,
            initial_message="I would like to view this property.", source="listing_inquiry",
            stage="new", score=65, assigned_member_id=44, first_response_at=None,
            first_response_seconds=None, spam_flag=False, created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1), buyer_contact_consent=True,
        )
        self.provider.list_leads.return_value = [self.lead]
        self.provider.get_lead.return_value = self.lead
        self.provider.assign_lead.return_value = self.lead
        self.provider.update_stage.return_value = self.lead
        self.provider.update_spam_flag.return_value = self.lead
        self.provider.add_activity.return_value = SimpleNamespace(
            id=1, organization_id=101, lead_id=31, actor_user_id=10,
            activity_type="note", body="Follow up", due_at=None, completed_at=None,
            created_at=datetime(2025, 1, 1),
        )
        self.provider.list_activities.return_value = []
        self.provider.add_message.return_value = SimpleNamespace(
            id=2, organization_id=101, lead_id=31, sender_type="agent", sender_user_id=10,
            body="Thank you", delivery_status="stored", created_at=datetime(2025, 1, 1),
        )
        self.provider.list_messages.return_value = []
        self.provider.list_templates.return_value = []
        self.provider.list_buyer_leads.return_value = [self.lead]
        self.provider.get_buyer_lead.return_value = self.lead
        self.provider.list_buyer_messages.return_value = []
        self.provider.add_buyer_message.return_value = SimpleNamespace(
            id=4, organization_id=101, lead_id=31, sender_type="buyer", sender_user_id=9,
            body="Could we visit?", delivery_status="stored", created_at=datetime(2025, 1, 1),
        )
        self.provider.create_template.return_value = SimpleNamespace(
            id=3, organization_id=101, title="Welcome", body="Hello {buyer_name}",
            created_by=10, created_at=datetime(2025, 1, 1),
        )
        self.cases = LeadUseCases(
            self.provider, set(BrokerPermission), role=BrokerRole.broker_owner,
            actor_user_id=10, organization_id=101,
        )
        self.app = FastAPI()
        self.app.include_router(leads_router)
        self.app.include_router(inbox_router)
        self.app.dependency_overrides[get_lead_use_cases] = lambda: self.cases
        self.buyer_cases = LeadUseCases(
            self.provider, set(), role="buyer", actor_user_id=9, organization_id=101,
        )
        self.app.dependency_overrides[get_buyer_lead_use_cases] = lambda: self.buyer_cases
        from backend.app.broker.api.inbox import buyer_router
        self.app.include_router(buyer_router)
        self.client = TestClient(self.app)

    def test_list_and_update_lead_pipeline_api(self):
        response = self.client.get("/leads?stage=new&limit=20&sort=-created_at")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["organization_id"], 101)
        self.assertEqual(self.client.patch("/leads/31/stage", json={"stage": "qualified"}).status_code, 200)
        self.assertEqual(self.client.post("/leads/31/assign", json={"member_user_id": 44}).status_code, 200)
        self.assertEqual(self.client.patch("/leads/31/spam", json={"spam_flag": True}).status_code, 200)
        self.assertEqual(self.client.patch("/leads/31/stage", json={"stage": "unknown"}).status_code, 422)

    def test_activities_messages_and_templates_api(self):
        self.assertEqual(self.client.get("/leads/31/activities").status_code, 200)
        self.assertEqual(self.client.post(
            "/leads/31/activities", headers={"Idempotency-Key": "activity-key-001"},
            json={"activity_type": "note", "body": "Call back"},
        ).status_code, 201)
        self.assertEqual(self.client.get("/inbox/31/messages").status_code, 200)
        self.assertEqual(self.client.post(
            "/inbox/31/messages", headers={"Idempotency-Key": "message-key-0001"},
            json={"body": "Thank you"},
        ).status_code, 201)
        self.assertEqual(self.client.get("/inbox/templates").status_code, 200)
        self.assertEqual(self.client.post(
            "/inbox/templates", headers={"Idempotency-Key": "template-key-001"},
            json={"title": "Welcome", "body": "Hello"},
        ).status_code, 201)

    def test_lead_api_rejects_missing_permissions(self):
        self.cases.permissions = set()
        self.assertEqual(self.client.get("/leads").status_code, 403)

    def test_buyer_conversation_requires_the_authenticated_buyer_link(self):
        self.assertEqual(self.client.get("/buyer/inbox?organization_id=101").status_code, 200)
        self.assertEqual(self.client.get("/buyer/inbox/31/messages?organization_id=101").status_code, 200)
        self.assertEqual(self.client.post(
            "/buyer/inbox/31/messages?organization_id=101",
            headers={"Idempotency-Key": "buyer-message-key-1"}, json={"body": "Could we visit?"},
        ).status_code, 201)
        self.provider.get_buyer_lead.return_value = None
        self.assertEqual(self.client.get("/buyer/inbox/32/messages?organization_id=101").status_code, 404)

    def test_message_rate_limit_is_enforced_in_use_case(self):
        limiter = Mock()
        limiter.consume.return_value = False
        cases = LeadUseCases(
            self.provider, {BrokerPermission.LEAD_MESSAGE}, role=BrokerRole.broker_agent,
            actor_user_id=44, organization_id=101, rate_limiter=limiter,
        )
        with self.assertRaises(TooManyLeadMessages):
            cases.send_agent_message(31, "Hello", "message-key-0001")
        self.provider.add_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
