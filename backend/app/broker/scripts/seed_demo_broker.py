"""Seed script for creating a demo broker organization with agents and inventory."""

import sys
from backend.app.db.session import init_db
from backend.app.broker.domain.roles import BrokerRole
from backend.app.broker.models.profile import BrokerProfile, BrokerStatus
from backend.app.broker.models.member import BrokerMember
from backend.app.broker.models.branch import BrokerBranch


def seed_demo_broker(org_id: int = 9999):
    """Seed a sample broker profile, members, and branches."""
    init_db()

    # 1. Profile
    profile = BrokerProfile.objects(organization_id=org_id).first()
    if not profile:
        profile = BrokerProfile(
            organization_id=org_id,
            status=BrokerStatus.approved,
            company_name="Apex Luxury Estates & Marine",
            legal_name="Apex Holdings PLC",
            address="100 Ocean Drive, Colombo 03",
            city="Colombo",
            country="Sri Lanka",
            licences={"LK": "REA-2026-9921", "UAE": "RERA-DXB-4410"},
            about="Premier luxury brokerage specializing in ultra-prime beachfront villas, supercars, and superyachts.",
            contact_email="concierge@apex-luxline.com",
            contact_phone="+94 11 234 5678",
            whatsapp_number="+94 77 123 4567",
            languages=["en", "si", "ar"],
            service_areas=["Colombo", "Galle", "Dubai", "London"],
        )
        profile.save()
        print(f"Created demo BrokerProfile for org {org_id}")
    else:
        print(f"Demo BrokerProfile for org {org_id} already exists")

    # 2. Branch
    branch = BrokerBranch.objects(organization_id=org_id, code="HQ-CMB").first()
    if not branch:
        branch = BrokerBranch(
            organization_id=org_id,
            name="Colombo Flagship",
            code="HQ-CMB",
            address="100 Ocean Drive",
            city="Colombo",
            country="Sri Lanka",
            phone="+94 11 234 5678",
            email="colombo@apex-luxline.com",
        )
        branch.save()
        print(f"Created demo BrokerBranch HQ-CMB for org {org_id}")

    # 3. Members
    sample_members = [
        {"user_id": 9901, "role": BrokerRole.broker_owner, "display_name": "Alexander Sterling", "title": "Managing Principal", "email": "alexander@apex-luxline.com"},
        {"user_id": 9902, "role": BrokerRole.broker_manager, "display_name": "Elena Rostova", "title": "Head of Private Client Desk", "email": "elena@apex-luxline.com"},
        {"user_id": 9903, "role": BrokerRole.broker_agent, "display_name": "Kavinda Perera", "title": "Senior Yacht & Villa Advisor", "email": "kavinda@apex-luxline.com"},
    ]

    for m in sample_members:
        member = BrokerMember.objects(organization_id=org_id, user_id=m["user_id"]).first()
        if not member:
            member = BrokerMember(
                organization_id=org_id,
                branch_id=branch.id if branch else None,
                user_id=m["user_id"],
                role=m["role"],
                display_name=m["display_name"],
                title=m["title"],
                email=m["email"],
                phone="+94 77 000 0000",
                whatsapp="+94 77 000 0000",
            )
            member.save()
            print(f"Created demo member {m['display_name']} ({m['role'].value})")

    print("Demo broker organization seed finished successfully.")


if __name__ == "__main__":
    seed_demo_broker()
