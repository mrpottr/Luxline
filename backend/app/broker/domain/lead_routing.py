"""Pure lead assignment rules for broker organizations."""

from collections.abc import Iterable


def select_assignee(
    *,
    listing_agent_id: int | None,
    rule_agent_id: int | None,
    active_agent_ids: Iterable[int],
    active_member_ids: Iterable[int] | None = None,
    assignment_counts: dict[int, int],
    manager_id: int | None,
) -> int | None:
    """Apply listing, explicit rule, least-loaded round-robin, then manager order."""
    active = set(active_agent_ids)
    active_members = set(active_member_ids) if active_member_ids is not None else active
    if listing_agent_id in active_members:
        return listing_agent_id
    if rule_agent_id in active:
        return rule_agent_id
    if active:
        return min(active, key=lambda user_id: (assignment_counts.get(user_id, 0), user_id))
    return manager_id


def score_lead(*, has_phone: bool, has_account: bool, message: str) -> int:
    """Return a stable, explainable 0–100 inquiry score from submitted fields."""
    score = 35 + (20 if has_phone else 0) + (15 if has_account else 0)
    message_length = len(message.strip())
    if message_length >= 80:
        score += 20
    elif message_length >= 25:
        score += 10
    return min(score, 100)
