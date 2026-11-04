"""Listing eligibility, category price floors, and publishing rules."""

from typing import Mapping, Tuple


class ListingRules:
    """Business validation rules for listing eligibility and publishing."""

    @classmethod
    def get_price_floor(
        cls,
        category: str,
        currency: str,
        price_floors: Mapping[str, Mapping[str, float]] | None = None,
    ) -> float | None:
        return (price_floors or {}).get(category.lower(), {}).get(currency.upper())

    @classmethod
    def validate_publish_eligibility(
        cls,
        is_approved_broker: bool,
        has_active_plan: bool,
        valid_region_licence: bool,
        owner_consent: bool,
        category: str,
        currency: str,
        price: float,
        quality_score: int,
        media_count: int,
        minimum_media_count: int,
        price_floors: Mapping[str, Mapping[str, float]],
        commission_terms: str | None = None,
        require_commission_terms: bool = False,
        owner_name: str | None = None,
        owner_mandate_reference: str | None = None,
        require_owner_mandate: bool = False,
    ) -> Tuple[bool, list[str]]:
        reasons = []

        if not is_approved_broker:
            reasons.append("Brokerage must be in approved status to publish listings.")

        if not has_active_plan:
            reasons.append("An active broker plan is required to publish listings.")

        if not valid_region_licence:
            reasons.append("A valid broker licence for the listing region is required.")

        if not owner_consent:
            reasons.append("Owner representation consent must be verified.")

        if require_commission_terms and not (commission_terms or "").strip():
            reasons.append("The agreed commission terms must be recorded before publishing.")

        if require_owner_mandate and not (owner_name or "").strip():
            reasons.append("The property owner's name must be recorded before publishing.")
        if require_owner_mandate and not (owner_mandate_reference or "").strip():
            reasons.append("The owner's representation mandate reference must be recorded before publishing.")
        if require_owner_mandate and not owner_consent:
            reasons.append("Owner consent must be confirmed for a property-broker listing.")

        price_floor = cls.get_price_floor(category, currency, price_floors)
        if price_floor is not None and price < price_floor:
            reasons.append(
                f"Asking price ({currency} {price:,.0f}) is below the configured threshold for {category} ({currency} {price_floor:,.0f})."
            )

        if quality_score < 50:
            reasons.append(f"Listing quality score ({quality_score}) must be at least 50 (Orange or Green) to publish.")

        if media_count < minimum_media_count:
            reasons.append(f"At least {minimum_media_count} listing media items are required.")

        return len(reasons) == 0, reasons

