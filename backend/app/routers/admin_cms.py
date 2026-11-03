"""Super-admin CMS authoring endpoints for Journal content."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.db.session import Session, get_db
from backend.app.dependencies import require_roles
from backend.app.models import AuditLog, BlogPost, User, UserRole
from backend.app.schemas import BlogPostCreate, BlogPostOut


router = APIRouter(prefix="/admin/cms", tags=["admin-cms"])


@router.get("/posts", response_model=list[BlogPostOut])
def list_cms_posts(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """List all Journal posts, including drafts."""
    return list(BlogPost.objects.order_by("-created_at").limit(100))


@router.post("/posts", response_model=BlogPostOut, status_code=status.HTTP_201_CREATED)
def create_cms_post(
    payload: BlogPostCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Create a Journal post from the admin CMS surface."""
    existing = BlogPost.objects(slug=payload.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="Post slug already exists")
    post = BlogPost(**payload.model_dump())
    db.add(post)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            event_type="cms.post_created",
            details={"post_id": post.id, "slug": post.slug, "published": post.published},
        )
    )
    db.commit()
    db.refresh(post)
    return post


@router.patch("/posts/{post_id}", response_model=BlogPostOut)
def update_cms_post(
    post_id: int,
    payload: BlogPostCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Replace editable Journal post fields."""
    post = BlogPost.objects(id=post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    for key, value in payload.model_dump().items():
        setattr(post, key, value)
    db.add(post)
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            event_type="cms.post_updated",
            details={"post_id": post.id, "slug": post.slug, "published": post.published},
        )
    )
    db.commit()
    db.refresh(post)
    return post

