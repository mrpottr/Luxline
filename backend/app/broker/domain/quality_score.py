"""Deterministic listing quality score calculator and recommendation engine."""

from typing import Any, Tuple


class QualityScoreCalculator:
    """Calculates listing quality scores (0-100) and actionable fix suggestions."""

    @classmethod
    def calculate(
        cls,
        title: str,
        description: str,
        price: float,
        photo_count: int,
        has_location: bool,
        has_specs: bool,
        owner_consent: bool,
    ) -> Tuple[int, str, list[str]]:
        score = 0
        suggestions = []

        # 1. Title quality (max 10)
        if title and len(title.strip()) >= 15:
            score += 10
        else:
            suggestions.append("Provide a descriptive title with brand/model or property name (at least 15 chars).")

        # 2. Photos (max 25)
        if photo_count >= 5:
            score += 25
        elif photo_count >= 1:
            score += 10
            suggestions.append("Add at least 5 professional high-resolution photos to improve buyer confidence.")
        else:
            suggestions.append("Upload at least 5 high-resolution photos (0 currently uploaded).")

        # 3. Description depth (max 20)
        desc_len = len(description.strip()) if description else 0
        if desc_len >= 250:
            score += 20
        elif desc_len >= 80:
            score += 10
            suggestions.append("Expand the listing description with architectural highlights or vehicle history (250+ chars).")
        else:
            suggestions.append("Write a detailed luxury description covering provenance and features.")

        # 4. Pricing (max 15)
        if price and price > 0:
            score += 15
        else:
            suggestions.append("Specify a clear asking price and currency.")

        # 5. Location (max 10)
        if has_location:
            score += 10
        else:
            suggestions.append("Add a city and country location.")

        # 6. Specific attributes / specifications (max 10)
        if has_specs:
            score += 10
        else:
            suggestions.append("Fill in vertical specifications (year, dimensions, or technical details).")

        # 7. Owner consent (max 10)
        if owner_consent:
            score += 10
        else:
            suggestions.append("Confirm verified seller/owner representation consent.")

        # Rating tier
        if score >= 80:
            rating = "green"
        elif score >= 50:
            rating = "orange"
        else:
            rating = "red"

        return score, rating, suggestions

