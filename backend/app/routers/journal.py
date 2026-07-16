"""Public Journal CMS endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models import BlogPost
from backend.app.schemas import BlogPostOut


router = APIRouter(prefix="/journal", tags=["journal"])


@router.get("/posts", response_model=list[BlogPostOut])
def list_journal_posts(db: Session = Depends(get_db)):
    """List published Journal posts."""
    return db.query(BlogPost).filter(BlogPost.published.is_(True)).order_by(BlogPost.created_at.desc()).limit(50).all()


@router.get("/posts/{slug}", response_model=BlogPostOut)
def get_journal_post(slug: str, db: Session = Depends(get_db)):
    """Read a published Journal post by slug."""
    post = db.query(BlogPost).filter(BlogPost.slug == slug, BlogPost.published.is_(True)).first()
    if not post:
        raise HTTPException(status_code=404, detail="Journal post not found")
    return post

