"""Broker onboarding, application submission, and public showcase endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.dependencies import get_current_user, require_roles
from backend.app.models import User, UserRole
from backend.app.broker.api.dependencies import BrokerContext, get_broker_context
from backend.app.broker.domain.onboarding import OnboardingRules
from backend.app.broker.models.profile import BrokerProfile, BrokerStatus
from backend.app.broker.repositories.profile_repository import BrokerProfileRepository
from backend.app.broker.schemas import (
    BrokerProfileOut,
    BrokerProfileUpdate,
    BrokerPublicProfileOut,
    BrokerVerificationDecision,
)

router = APIRouter(tags=["broker-onboarding"])


@router.get("/onboarding/profile", response_model=BrokerProfileOut)
def get_my_broker_profile(context: BrokerContext = Depends(get_broker_context)):
    """Return the authenticated organization's broker profile."""
    repo = BrokerProfileRepository(context.organization_id)
    profile = repo.get_profile()
    if not profile:
        profile = repo.create(
            company_name=context.user.first_name + " Brokerage",
            contact_email=context.user.email,
            status=BrokerStatus.draft,
        )
    return profile


@router.post("/onboarding/profile", response_model=BrokerProfileOut)
def update_my_broker_profile(
    payload: BrokerProfileUpdate,
    context: BrokerContext = Depends(get_broker_context),
):
    """Save or update draft details for the broker profile."""
    repo = BrokerProfileRepository(context.organization_id)
    profile = repo.upsert_profile(**payload.model_dump(exclude_unset=True))
    return profile


@router.post("/onboarding/submit", response_model=BrokerProfileOut)
def submit_broker_application(context: BrokerContext = Depends(get_broker_context)):
    """Submit the broker application for administrative review."""
    repo = BrokerProfileRepository(context.organization_id)
    profile = repo.get_profile()
    if not profile:
        raise HTTPException(status_code=404, detail="Broker profile not found")

    if not OnboardingRules.can_transition(profile.status, BrokerStatus.submitted):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit application in status: {profile.status.value}",
        )

    is_valid, missing_fields = OnboardingRules.validate_for_submission(profile)
    if not is_valid:
        raise HTTPException(
            status_code=422,
            detail=f"Application missing required fields: {', '.join(missing_fields)}",
        )

    profile.status = BrokerStatus.submitted
    profile.save()
    return profile


@router.get("/public/brokers", response_model=list[BrokerPublicProfileOut])
def list_public_brokers():
    """List approved brokers for the public directory."""
    profiles = BrokerProfile.objects(status=BrokerStatus.approved, is_deleted=False)
    results = []
    for p in profiles:
        results.append(
            BrokerPublicProfileOut(
                organization_id=p.organization_id,
                company_name=p.company_name,
                logo_url=p.logo_url,
                banner_url=p.banner_url,
                about=p.about,
                website=p.website,
                city=p.city,
                country=p.country,
                languages=p.languages,
                service_areas=p.service_areas,
                whatsapp_number=p.whatsapp_number,
                is_verified=True,
            )
        )
    return results


@router.get("/public/brokers/{organization_id}", response_model=BrokerPublicProfileOut)
def get_public_broker(organization_id: int):
    """View an approved broker's public showcase profile."""
    profile = BrokerProfile.objects(
        organization_id=organization_id,
        status=BrokerStatus.approved,
        is_deleted=False,
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Broker not found or not approved")

    return BrokerPublicProfileOut(
        organization_id=profile.organization_id,
        company_name=profile.company_name,
        logo_url=profile.logo_url,
        banner_url=profile.banner_url,
        about=profile.about,
        website=profile.website,
        city=profile.city,
        country=profile.country,
        languages=profile.languages,
        service_areas=profile.service_areas,
        whatsapp_number=profile.whatsapp_number,
        is_verified=True,
    )


@router.post("/admin/brokers/{organization_id}/review", response_model=BrokerProfileOut)
def admin_review_broker(
    organization_id: int,
    decision_payload: BrokerVerificationDecision,
    admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Platform admin review to approve, reject, or suspend a broker profile."""
    profile = BrokerProfile.objects(organization_id=organization_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Broker profile not found")

    target_map = {
        "approve": BrokerStatus.approved,
        "reject": BrokerStatus.rejected,
        "suspend": BrokerStatus.suspended,
    }
    target_status = target_map.get(decision_payload.decision.lower())
    if not target_status:
        raise HTTPException(status_code=400, detail="Invalid review decision")

    profile.status = target_status
    profile.decision_notes = decision_payload.notes or f"Reviewed by Admin {admin.id}"
    profile.save()
    return profile
