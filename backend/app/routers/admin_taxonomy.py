"""Super-admin taxonomy management for brands, models, builders, and materials."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.db.session import Session, get_db
from backend.app.dependencies import require_roles
from backend.app.models import AuditLog, TaxonomyTerm, User, UserRole
from backend.app.schemas import TaxonomyTermCreate, TaxonomyTermOut, TaxonomyTermUpdate
from backend.app.utils import slugify


router = APIRouter(prefix="/admin/taxonomy", tags=["admin-taxonomy"])


@router.get("", response_model=list[TaxonomyTermOut])
def list_taxonomy_terms(
    taxonomy: str | None = Query(default=None),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """List taxonomy terms used by faceted listing metadata."""
    query = TaxonomyTerm.objects
    if taxonomy:
        query = query.filter(taxonomy=taxonomy.strip().lower())
    if not include_inactive:
        query = query.filter(is_active=True)
    return list(query.order_by("taxonomy", "name").limit(500))


@router.post("", response_model=TaxonomyTermOut, status_code=status.HTTP_201_CREATED)
def create_taxonomy_term(
    payload: TaxonomyTermCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Create a taxonomy term and audit the change."""
    taxonomy = payload.taxonomy.strip().lower()
    slug = payload.slug or slugify(payload.name)
    existing = TaxonomyTerm.objects(
        taxonomy=taxonomy,
        parent_id=payload.parent_id,
        slug=slug,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Taxonomy term already exists")

    term = TaxonomyTerm(
        taxonomy=taxonomy,
        parent_id=payload.parent_id,
        name=payload.name.strip(),
        slug=slug,
        metadata_json=payload.metadata_json,
        is_active=payload.is_active,
    )
    db.add(term)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            event_type="taxonomy.created",
            details={"term_id": term.id, "taxonomy": taxonomy, "name": term.name},
        )
    )
    db.commit()
    db.refresh(term)
    return term


@router.patch("/{term_id}", response_model=TaxonomyTermOut)
def update_taxonomy_term(
    term_id: int,
    payload: TaxonomyTermUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Update or deactivate a taxonomy term."""
    term = TaxonomyTerm.objects(id=term_id).first()
    if not term:
        raise HTTPException(status_code=404, detail="Taxonomy term not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if key == "slug" and value:
            value = slugify(value)
        setattr(term, key, value)

    db.add(term)
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            event_type="taxonomy.updated",
            details={"term_id": term.id, "updates": updates},
        )
    )
    db.commit()
    db.refresh(term)
    return term

