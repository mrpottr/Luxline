"""Agency profile and team management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.dependencies import get_current_user, require_roles
from backend.app.models import AgencyProfile, AgencyTeamMember, User, UserRole
from backend.app.schemas import (
    AgencyProfileOut,
    AgencyProfileUpsert,
    AgencyTeamMemberCreate,
    AgencyTeamMemberOut,
)


router = APIRouter(prefix="/agencies", tags=["agencies"])


@router.get("", response_model=list[AgencyProfileOut])
def list_agencies(db: Session = Depends(get_db)):
    """Return all public agency profiles."""
    return db.query(AgencyProfile).order_by(AgencyProfile.id.asc()).limit(100).all()


@router.post("/me/profile", response_model=AgencyProfileOut, status_code=status.HTTP_201_CREATED)
def create_or_update_profile(
    payload: AgencyProfileUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.business_account)),
):
    """Create or update the authenticated business user's agency profile.

    This endpoint behaves as an upsert:
    - Creates a new profile if one does not exist for the current owner.
    - Updates the existing profile fields when a profile is already present.
    """
    profile = db.query(AgencyProfile).filter(AgencyProfile.owner_id == current_user.id).first()
    if not profile:
        profile = AgencyProfile(owner_id=current_user.id, **payload.model_dump())
        db.add(profile)
    else:
        for key, value in payload.model_dump().items():
            setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/me/profile", response_model=AgencyProfileOut)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.business_account)),
):
    """Return the authenticated business user's own agency profile.

    Raises:
        HTTPException: 404 if the user has not created an agency profile yet.
    """
    profile = db.query(AgencyProfile).filter(AgencyProfile.owner_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Agency profile not found")
    return profile


@router.post("/me/team", response_model=AgencyTeamMemberOut, status_code=status.HTTP_201_CREATED)
def add_team_member(
    payload: AgencyTeamMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.business_account)),
):
    """Add a new team member to the authenticated business user's agency profile.

    A profile must exist before team members can be attached to it.

    Raises:
        HTTPException: 404 if the agency profile for the current user is missing.
    """
    profile = db.query(AgencyProfile).filter(AgencyProfile.owner_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Agency profile not found")

    member = AgencyTeamMember(
        agency_id=profile.id,
        agency_owner_id=current_user.id,
        full_name=payload.full_name,
        title=payload.title,
        email=payload.email,
        phone=payload.phone,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.get("/{agency_id}", response_model=AgencyProfileOut)
def get_public_agency_profile(agency_id: int, db: Session = Depends(get_db)):
    """Return a public agency profile by agency identifier.

    This endpoint supports public profile lookups from listing and agency views.

    Raises:
        HTTPException: 404 if the requested agency profile does not exist.
    """
    profile = db.query(AgencyProfile).filter(AgencyProfile.id == agency_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Agency profile not found")
    return profile
