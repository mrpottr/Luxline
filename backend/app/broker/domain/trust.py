"""Framework-free broker review integrity and badge rules."""

from dataclasses import dataclass


BADGE_RULE_VERSION = 1


@dataclass(frozen=True)
class BadgeEvaluation:
    code: str
    awarded: bool
    explanation: str
    criteria: dict


def validate_review(*, rating: int, body: str, public_consent: bool) -> dict:
    if type(rating) is not int or not 1 <= rating <= 5:
        raise ValueError("Review rating must be an integer from 1 to 5")
    normalized_body = body.strip()
    if len(normalized_body) < 10 or len(normalized_body) > 3000:
        raise ValueError("Review text must contain between 10 and 3000 characters")
    if public_consent is not True:
        raise ValueError("Explicit consent is required to publish a review")
    return {"rating": rating, "body": normalized_body, "public_consent": True}


def evaluate_organization_badges(*, broker_approved: bool, live_listing_count: int, average_quality: float) -> list[BadgeEvaluation]:
    verified = broker_approved is True
    quality = live_listing_count >= 5 and average_quality >= 85
    return [
        BadgeEvaluation(
            code="verified_seller", awarded=verified,
            explanation="Broker verification is approved." if verified else "Complete platform broker verification to earn this badge.",
            criteria={"broker_approved": bool(broker_approved)},
        ),
        BadgeEvaluation(
            code="quality_lister", awarded=quality,
            explanation=("At least five live listings average a quality score of 85 or higher." if quality
                         else f"Needs five live listings averaging 85 quality; current: {live_listing_count} listings, {average_quality:.1f} average."),
            criteria={"live_listing_count": live_listing_count, "average_quality": round(average_quality, 2),
                      "required_live_listings": 5, "required_average_quality": 85},
        ),
    ]


def evaluate_responsive_agent(*, response_count: int, average_response_seconds: float | None) -> BadgeEvaluation:
    awarded = response_count >= 5 and average_response_seconds is not None and average_response_seconds <= 3600
    if awarded:
        explanation = "At least five buyer leads received a first response within an average of one hour."
    elif response_count < 5:
        explanation = f"Needs five first responses; current: {response_count}."
    elif average_response_seconds is None:
        explanation = "First response times are not available yet."
    else:
        explanation = f"Average first response must be within one hour; current: {average_response_seconds / 60:.0f} minutes."
    return BadgeEvaluation(
        code="responsive_agent", awarded=awarded, explanation=explanation,
        criteria={"response_count": response_count,
                  "average_response_seconds": round(average_response_seconds, 2) if average_response_seconds is not None else None,
                  "required_responses": 5, "maximum_average_response_seconds": 3600},
    )
