"""Dependency wiring for platform administrators managing broker plans."""

from fastapi import Depends

from backend.app.broker.api.dependencies import get_admin_plan_use_cases
from backend.app.broker.application.monetization_use_cases import AdminPlanUseCases


def get_broker_plan_admin_use_cases(
    cases: AdminPlanUseCases = Depends(get_admin_plan_use_cases),
) -> AdminPlanUseCases:
    return cases
