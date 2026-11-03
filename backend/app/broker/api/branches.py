"""Broker branch office management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.broker.api.dependencies import BrokerContext, require_broker_permission
from backend.app.broker.domain.roles import BrokerPermission
from backend.app.broker.repositories.branch_repository import BrokerBranchRepository
from backend.app.broker.schemas import BrokerBranchCreate, BrokerBranchOut, BrokerBranchUpdate

router = APIRouter(prefix="/branches", tags=["broker-branches"])


@router.get("", response_model=list[BrokerBranchOut])
def list_branches(
    context: BrokerContext = Depends(require_broker_permission(BrokerPermission.ORG_VIEW)),
):
    """List all registered branch offices for this broker organization."""
    repo = BrokerBranchRepository(context.organization_id)
    return repo.find_all(order_by="name")


@router.post("", response_model=BrokerBranchOut, status_code=status.HTTP_201_CREATED)
def create_branch(
    payload: BrokerBranchCreate,
    context: BrokerContext = Depends(require_broker_permission(BrokerPermission.BRANCH_MANAGE)),
):
    """Add a new regional branch office."""
    repo = BrokerBranchRepository(context.organization_id)
    existing = repo.find_by_code(payload.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Branch with code {payload.code.upper()} already exists",
        )

    branch = repo.create(**payload.model_dump())
    return branch


@router.patch("/{branch_id}", response_model=BrokerBranchOut)
def update_branch(
    branch_id: int,
    payload: BrokerBranchUpdate,
    context: BrokerContext = Depends(require_broker_permission(BrokerPermission.BRANCH_MANAGE)),
):
    """Update branch office details."""
    repo = BrokerBranchRepository(context.organization_id)
    branch = repo.find_by_id(branch_id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch office not found")

    updated = repo.update(branch_id, **payload.model_dump(exclude_unset=True))
    return updated


@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_branch(
    branch_id: int,
    context: BrokerContext = Depends(require_broker_permission(BrokerPermission.BRANCH_MANAGE)),
):
    """Delete a branch office."""
    repo = BrokerBranchRepository(context.organization_id)
    branch = repo.find_by_id(branch_id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch office not found")

    repo.soft_delete(branch_id)
    return None

