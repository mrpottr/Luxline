"""Monetization endpoints for subscriptions, featured placements, and blog content."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.dependencies import get_current_user, require_roles
from backend.app.models import BlogPost, FeaturedPlacement, Listing, Subscription, SubscriptionStatus, User, UserRole
from backend.app.schemas import BlogPostCreate, BlogPostOut, SubscriptionCreate, SubscriptionOut


router = APIRouter(prefix="/monetization", tags=["monetization"])


@router.post("/subscriptions", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
def create_subscription(
    payload: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.business_account, UserRole.super_admin)),
):
    """Create an active subscription record for an eligible business user."""
    subscription = Subscription(
        business_user_id=current_user.id,
        plan_code=payload.plan_code,
        status=SubscriptionStatus.active,
        starts_at=datetime.utcnow(),
        ends_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@router.get("/subscriptions/me", response_model=list[SubscriptionOut])
def my_subscriptions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List subscriptions owned by the authenticated user."""
    return (
        db.query(Subscription)
        .filter(Subscription.business_user_id == current_user.id)
        .order_by(Subscription.starts_at.desc())
        .all()
    )


@router.post("/listings/{listing_id}/feature", status_code=status.HTTP_201_CREATED)
def feature_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.business_account, UserRole.super_admin)),
):
    """Mark a listing as featured and create placement metadata if needed."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id != current_user.id and current_user.role != UserRole.super_admin:
        raise HTTPException(status_code=403, detail="Not your listing")

    listing.is_featured = True
    placement = db.query(FeaturedPlacement).filter(FeaturedPlacement.listing_id == listing_id).first()
    if not placement:
        placement = FeaturedPlacement(listing_id=listing_id, starts_at=datetime.utcnow(), priority=10)
        db.add(placement)
    db.commit()
    return {"listing_id": listing_id, "featured": True}


@router.post("/blog/posts", response_model=BlogPostOut, status_code=status.HTTP_201_CREATED)
def create_blog_post(
    payload: BlogPostCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Create a blog post as a super-admin operation."""
    post = BlogPost(**payload.model_dump())
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.get("/blog/posts", response_model=list[BlogPostOut])
def list_blog_posts(db: Session = Depends(get_db), include_unpublished: bool = False):
    """List blog posts, optionally including unpublished drafts."""
    query = db.query(BlogPost).order_by(BlogPost.created_at.desc())
    if not include_unpublished:
        query = query.filter(BlogPost.published.is_(True))
    return query.limit(50).all()
