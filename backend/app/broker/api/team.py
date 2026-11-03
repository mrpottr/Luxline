"""Broker team member management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.broker.api.dependencies import BrokerContext, get_broker_context, require_broker_permission
from backend.app.broker.domain.roles import BrokerPermission, BrokerRole
from backend.app.broker.domain.team_rules import TeamRules
from backend.app.broker.models.member import BrokerMember
from backend.app.broker.repositories.member_repository import BrokerMemberRepository
from backend.app.broker.schemas import BrokerMemberCreate, BrokerMemberOut, BrokerMemberUpdate

router = APIRouter(prefix="/team", tags=["broker-team"])


@router.get("/members", response_model=list[BrokerMemberOut])
def list_team_members(
    context: BrokerContext = Depends(require_broker_permission(BrokerPermission.TEAM_VIEW)),
):
    """List all team members for the authenticated broker organization."""
    repo = BrokerMemberRepository(context.organization_id)
    return repo.list_active_members()


@router.post("/members", response_model=BrokerMemberOut, status_code=status.HTTP_201_CREATED)
def add_team_member(
    payload: BrokerMemberCreate,
    context: BrokerContext = Depends(require_broker_permission(BrokerPermission.TEAM_MANAGE)),
):
    """Add a new member to the broker organization."""
    if not TeamRules.can_manage_member(context.role, payload.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot assign role {payload.role.value} with current privileges",
        )

    repo = BrokerMemberRepository(context.organization_id)
    existing = repo.find_by_user_id(payload.user_id)
    if existing and not existing.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this broker organization",
        )

    member = repo.create(**payload.model_dump())
    return member


@router.patch("/members/{member_id}", response_model=BrokerMemberOut)
def update_team_member(
    member_id: int,
    payload: BrokerMemberUpdate,
    context: BrokerContext = Depends(require_broker_permission(BrokerPermission.TEAM_MANAGE)),
):
    """Update a team member's role or public agent card details."""
    repo = BrokerMemberRepository(context.organization_id)
    member = repo.find_by_id(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")

    if payload.role and not TeamRules.can_manage_member(context.role, payload.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot change member to role {payload.role.value}",
        )

    # Check last owner safety rule
    if member.role == BrokerRole.broker_owner and payload.role and payload.role != BrokerRole.broker_owner:
        owners_count = repo.count(role=BrokerRole.broker_owner, is_active=True)
        if not TeamRules.validate_owner_removal(owners_count):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the only remaining owner of this organization",
            )

    updated = repo.update(member_id, **payload.model_dump(exclude_unset=True))
    return updated


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_member(
    member_id: int,
    context: BrokerContext = Depends(require_broker_permission(BrokerPermission.TEAM_MANAGE)),
):
    """Deactivate and remove a team member from the organization."""
    repo = BrokerMemberRepository(context.organization_id)
    member = repo.find_by_id(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")

    if member.role == BrokerRole.broker_owner:
        owners_count = repo.count(role=BrokerRole.broker_owner, is_active=True)
        if not TeamRules.validate_owner_removal(owners_count):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the only remaining owner of this organization",
            )

    repo.soft_delete(member_id)
    return None

