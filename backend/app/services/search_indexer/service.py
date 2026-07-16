"""PostgreSQL-based search service."""

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from backend.app.models import Listing, ListingCategory, ListingStatus, ModerationStatus


class SearchService:
    @staticmethod
    def search_listings(
        db: Session,
        q: str | None = None,
        category: ListingCategory | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        year: int | None = None,
        make: str | None = None,
        model: str | None = None,
        condition: str | None = None,
        bedrooms: int | None = None,
        map_bbox: tuple[float, float, float, float] | None = None,
        limit: int = 25,
        offset: int = 0,
    ):
        conditions = [Listing.status == ListingStatus.active, Listing.moderation_status == ModerationStatus.approved]

        if q:
            # PostgreSQL FTS
            tsquery = func.plainto_tsquery('english', q)
            vector = func.to_tsvector('english', 
                func.concat_ws(' ', 
                    Listing.title, 
                    Listing.description, 
                    Listing.location_city, 
                    Listing.location_country,
                    Listing.make, 
                    Listing.model
                )
            )
            conditions.append(vector.op('@@')(tsquery))

        if category:
            if category == ListingCategory.car:
                conditions.append(Listing.category.in_([ListingCategory.car, ListingCategory.hypercar]))
            else:
                conditions.append(Listing.category == category)
        if min_price is not None:
            conditions.append(Listing.price >= min_price)
        if max_price is not None:
            conditions.append(Listing.price <= max_price)
        if year is not None:
            conditions.append(Listing.year == year)
        if make:
            conditions.append(Listing.make.ilike(f"%{make}%"))
        if model:
            conditions.append(Listing.model.ilike(f"%{model}%"))
        if condition:
            conditions.append(Listing.condition.ilike(f"%{condition}%"))
        if bedrooms is not None:
            conditions.append(Listing.bedrooms == bedrooms)
        if map_bbox:
            min_lng, min_lat, max_lng, max_lat = map_bbox
            conditions.append(Listing.longitude.between(min_lng, max_lng))
            conditions.append(Listing.latitude.between(min_lat, max_lat))

        query = (
            db.query(Listing)
            .filter(and_(*conditions))
            .order_by(Listing.is_featured.desc(), Listing.published_at.desc(), Listing.created_at.desc())
        )
        total = query.count()
        results = query.offset(offset).limit(limit).all()
        return total, results

    @staticmethod
    def get_autocomplete_suggestions(db: Session, q: str, limit: int = 10):
        wildcard = f"%{q}%"
        rows = (
            db.query(Listing.make, Listing.model, Listing.location_city)
            .filter(
                or_(
                    Listing.make.ilike(wildcard),
                    Listing.model.ilike(wildcard),
                    Listing.location_city.ilike(wildcard),
                )
            )
            .limit(20)
            .all()
        )
        suggestions = sorted(
            {
                value
                for row in rows
                for value in [row[0], row[1], row[2]]
                if value and q.lower() in value.lower()
            }
        )
        return suggestions[:limit]

    @staticmethod
    def get_facets(db: Session, category: ListingCategory | None = None):
        conditions = [Listing.status == ListingStatus.active, Listing.moderation_status == ModerationStatus.approved]
        if category:
            conditions.append(Listing.category == category)

        category_counts = (
            db.query(Listing.category, func.count(Listing.id))
            .filter(and_(*conditions))
            .group_by(Listing.category)
            .all()
        )
        make_counts = (
            db.query(Listing.make, func.count(Listing.id))
            .filter(and_(*conditions), Listing.make.is_not(None))
            .group_by(Listing.make)
            .order_by(func.count(Listing.id).desc())
            .limit(20)
            .all()
        )
        condition_counts = (
            db.query(Listing.condition, func.count(Listing.id))
            .filter(and_(*conditions), Listing.condition.is_not(None))
            .group_by(Listing.condition)
            .all()
        )
        return {
            "category": [{"value": row[0], "count": row[1]} for row in category_counts],
            "make": [{"value": row[0], "count": row[1]} for row in make_counts],
            "condition": [{"value": row[0], "count": row[1]} for row in condition_counts],
        }
