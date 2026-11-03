"""Base repository enforcing absolute tenant isolation on all queries."""

from typing import Generic, Type, TypeVar
from mongoengine import Document, QuerySet

T = TypeVar("T", bound=Document)


class BaseTenantRepository(Generic[T]):
    """Generic repository providing tenant-scoped data access.

    Every operation strictly requires and filters on `organization_id`.
    A broker organization can never access or modify another organization's records.
    """

    def __init__(self, model_class: Type[T], organization_id: int):
        self.model_class = model_class
        self.organization_id = organization_id

    def _scoped_query(self, include_deleted: bool = False, **kwargs) -> QuerySet:
        query = self.model_class.objects(organization_id=self.organization_id, **kwargs)
        if not include_deleted and hasattr(self.model_class, "is_deleted"):
            query = query.filter(is_deleted=False)
        return query

    def find_by_id(self, item_id: int, include_deleted: bool = False) -> T | None:
        """Find an entity by ID strictly within the current tenant."""
        return self._scoped_query(include_deleted=include_deleted, id=item_id).first()

    def find_all(self, limit: int = 100, offset: int = 0, order_by: str = "-created_at", **kwargs) -> list[T]:
        """Find multiple entities filtered by tenant and optional criteria."""
        return list(
            self._scoped_query(**kwargs)
            .order_by(order_by)
            .skip(offset)
            .limit(limit)
        )

    def count(self, **kwargs) -> int:
        """Count matching records within the tenant."""
        return self._scoped_query(**kwargs).count()

    def create(self, **kwargs) -> T:
        """Create a new entity, forcefully setting organization_id."""
        kwargs["organization_id"] = self.organization_id
        instance = self.model_class(**kwargs)
        instance.save()
        return instance

    def update(self, item_id: int, **kwargs) -> T | None:
        """Update an existing entity within tenant scope."""
        # Never allow overriding organization_id
        kwargs.pop("organization_id", None)
        instance = self.find_by_id(item_id)
        if not instance:
            return None
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        instance.save()
        return instance

    def soft_delete(self, item_id: int) -> bool:
        """Mark an entity as deleted within tenant scope."""
        instance = self.find_by_id(item_id)
        if not instance:
            return False
        if hasattr(instance, "is_deleted"):
            instance.is_deleted = True
            instance.save()
            return True
        instance.delete()
        return True
