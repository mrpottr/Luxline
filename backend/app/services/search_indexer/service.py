"""MongoDB-backed search service."""

from mongoengine import Q

from backend.app.db.session import Session
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
        queryset = Listing.objects(
            status=ListingStatus.active,
            moderation_status=ModerationStatus.approved,
        )

        if q:
            queryset = queryset.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(location_city__icontains=q)
                | Q(location_country__icontains=q)
                | Q(make__icontains=q)
                | Q(model__icontains=q)
            )

        if category:
            if category == ListingCategory.car:
                queryset = queryset.filter(category__in=[ListingCategory.car, ListingCategory.hypercar])
            else:
                queryset = queryset.filter(category=category)
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)
        if year is not None:
            queryset = queryset.filter(year=year)
        if make:
            queryset = queryset.filter(make__icontains=make)
        if model:
            queryset = queryset.filter(model__icontains=model)
        if condition:
            queryset = queryset.filter(condition__icontains=condition)
        if bedrooms is not None:
            queryset = queryset.filter(bedrooms=bedrooms)
        if map_bbox:
            min_lng, min_lat, max_lng, max_lat = map_bbox
            queryset = queryset.filter(longitude__gte=min_lng, longitude__lte=max_lng)
            queryset = queryset.filter(latitude__gte=min_lat, latitude__lte=max_lat)

        ordered = queryset.order_by("-is_featured", "-published_at", "-created_at")
        total = ordered.count()
        results = list(ordered.skip(offset).limit(limit))
        return total, results

    @staticmethod
    def get_autocomplete_suggestions(db: Session, q: str, limit: int = 10):
        rows = (
            Listing.objects(
                Q(make__icontains=q) | Q(model__icontains=q) | Q(location_city__icontains=q)
            )
            .only("make", "model", "location_city")
            .limit(20)
        )
        suggestions = sorted(
            {
                value
                for row in rows
                for value in [row.make, row.model, row.location_city]
                if value and q.lower() in value.lower()
            }
        )
        return suggestions[:limit]

    @staticmethod
    def get_facets(db: Session, category: ListingCategory | None = None):
        queryset = Listing.objects(
            status=ListingStatus.active,
            moderation_status=ModerationStatus.approved,
        )
        if category:
            queryset = queryset.filter(category=category)

        def _counts(field_name: str, max_items: int | None = None) -> list[dict]:
            frequencies = queryset.item_frequencies(field_name)
            items = [
                (getattr(value, "value", value), count)
                for value, count in frequencies.items()
                if value is not None
            ]
            items.sort(key=lambda item: item[1], reverse=True)
            if max_items is not None:
                items = items[:max_items]
            return [{"value": value, "count": count} for value, count in items]

        return {
            "category": _counts("category"),
            "make": _counts("make", 20),
            "condition": _counts("condition"),
        }
