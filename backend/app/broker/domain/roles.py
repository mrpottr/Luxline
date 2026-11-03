"""Pure domain roles and permissions for the Broker module.

Independent of framework or database models.
"""

from enum import Enum


class BrokerRole(str, Enum):
    """Organization-scoped broker roles."""
    broker_owner = "broker_owner"
    broker_manager = "broker_manager"
    broker_agent = "broker_agent"
    broker_viewer = "broker_viewer"


class BrokerPermission(str, Enum):
    """Granular broker permissions."""
    # Organization & Settings
    ORG_VIEW = "broker:org:view"
    ORG_EDIT = "broker:org:edit"
    BILLING_MANAGE = "broker:billing:manage"

    # Team & Branches
    TEAM_VIEW = "broker:team:view"
    TEAM_MANAGE = "broker:team:manage"
    BRANCH_MANAGE = "broker:branch:manage"

    # Listings
    LISTING_VIEW_ALL = "broker:listing:view_all"
    LISTING_VIEW_OWN = "broker:listing:view_own"
    LISTING_CREATE = "broker:listing:create"
    LISTING_EDIT = "broker:listing:edit"
    LISTING_PUBLISH = "broker:listing:publish"
    LISTING_DELETE = "broker:listing:delete"

    # Leads & Inbox
    LEAD_VIEW_ALL = "broker:lead:view_all"
    LEAD_VIEW_OWN = "broker:lead:view_own"
    LEAD_ASSIGN = "broker:lead:assign"
    LEAD_MESSAGE = "broker:lead:message"

    # Promotions & Credits
    PROMOTION_VIEW = "broker:promotion:view"
    PROMOTION_MANAGE = "broker:promotion:manage"

    # Analytics
    ANALYTICS_VIEW = "broker:analytics:view"

    # Trust & Compliance
    REVIEWS_MANAGE = "broker:reviews:manage"
    AUDIT_VIEW = "broker:audit:view"


# Role-to-permission mapping
ROLE_PERMISSIONS: dict[BrokerRole, set[BrokerPermission]] = {
    BrokerRole.broker_owner: {
        perm for perm in BrokerPermission
    },
    BrokerRole.broker_manager: {
        BrokerPermission.ORG_VIEW,
        BrokerPermission.TEAM_VIEW,
        BrokerPermission.LISTING_VIEW_ALL,
        BrokerPermission.LISTING_VIEW_OWN,
        BrokerPermission.LISTING_CREATE,
        BrokerPermission.LISTING_EDIT,
        BrokerPermission.LISTING_PUBLISH,
        BrokerPermission.LEAD_VIEW_ALL,
        BrokerPermission.LEAD_VIEW_OWN,
        BrokerPermission.LEAD_ASSIGN,
        BrokerPermission.LEAD_MESSAGE,
        BrokerPermission.PROMOTION_VIEW,
        BrokerPermission.PROMOTION_MANAGE,
        BrokerPermission.ANALYTICS_VIEW,
        BrokerPermission.REVIEWS_MANAGE,
        BrokerPermission.AUDIT_VIEW,
    },
    BrokerRole.broker_agent: {
        BrokerPermission.ORG_VIEW,
        BrokerPermission.TEAM_VIEW,
        BrokerPermission.LISTING_VIEW_OWN,
        BrokerPermission.LISTING_CREATE,
        BrokerPermission.LISTING_EDIT,
        BrokerPermission.LEAD_VIEW_OWN,
        BrokerPermission.LEAD_MESSAGE,
        BrokerPermission.ANALYTICS_VIEW,
    },
    BrokerRole.broker_viewer: {
        BrokerPermission.ORG_VIEW,
        BrokerPermission.ANALYTICS_VIEW,
    },
}


def role_has_permission(role: BrokerRole, permission: BrokerPermission) -> bool:
    """Return True if the specified broker role carries the permission."""
    return permission in ROLE_PERMISSIONS.get(role, set())
