"""CSV Bulk import service for broker inventory."""

import csv
import io
import math
from typing import Any, Mapping

from backend.app.broker.domain.listing_rules import ListingRules


class BulkImportService:
    REQUIRED_COLUMNS = {"title", "category", "price", "currency", "location_country", "location_city"}

    @staticmethod
    def parse_rows(csv_text: str) -> list[dict[str, str]]:
        reader = csv.DictReader(io.StringIO(csv_text.strip()))
        return [dict(row) for row in reader]

    @classmethod
    def validate_csv(
        cls,
        csv_text: str,
        *,
        price_floors: Mapping[str, Mapping[str, float]] | None = None,
        maximum_rows: int = 500,
        allowed_categories: set[str] | None = None,
    ) -> dict[str, Any]:
        """Parse and dry-run validate CSV content before persisting."""
        reader = csv.DictReader(io.StringIO(csv_text.strip()))
        headers = set(reader.fieldnames or [])

        missing_headers = cls.REQUIRED_COLUMNS - headers
        if missing_headers:
            return {
                "is_valid": False,
                "error": f"Missing required CSV columns: {', '.join(missing_headers)}",
                "total_rows": 0,
                "valid_rows": 0,
                "invalid_rows": 0,
                "row_reports": [],
            }

        parsed_rows = cls.parse_rows(csv_text)
        if len(parsed_rows) > maximum_rows:
            return {
                "is_valid": False,
                "error": f"CSV exceeds the maximum of {maximum_rows} rows",
                "total_rows": len(parsed_rows),
                "valid_rows": 0,
                "invalid_rows": len(parsed_rows),
                "row_reports": [],
            }

        row_reports = []
        valid_count = 0
        invalid_count = 0

        for idx, row in enumerate(reader, start=1):
            row_errors = []
            category = (row.get("category") or "").strip().lower()
            title = (row.get("title") or "").strip()

            if not title:
                row_errors.append("Title cannot be empty")

            if allowed_categories is not None and category not in allowed_categories:
                row_errors.append("Unsupported listing category")

            try:
                price = float(row.get("price") or 0)
                if not math.isfinite(price) or price <= 0:
                    row_errors.append("Price must be a finite amount greater than zero")
                currency = (row.get("currency") or "").strip().upper()
                if len(currency) != 3 or not currency.isalpha():
                    row_errors.append("Currency must be a three-letter ISO code")
                if not (row.get("location_country") or "").strip() or not (row.get("location_city") or "").strip():
                    row_errors.append("Country and city are required")
                price_floor = ListingRules.get_price_floor(category, currency, price_floors)
                if price_floor is not None and price < price_floor:
                    row_errors.append(f"Price {currency} {price:,.0f} below configured minimum {currency} {price_floor:,.0f} for {category}")
            except ValueError:
                row_errors.append("Invalid numeric price")

            is_row_valid = len(row_errors) == 0
            if is_row_valid:
                valid_count += 1
            else:
                invalid_count += 1

            row_reports.append({
                "row_index": idx,
                "title": title or "Untitled",
                "category": category,
                "is_valid": is_row_valid,
                "errors": row_errors,
            })

        if not row_reports:
            return {
                "is_valid": False,
                "error": "CSV must contain at least one listing row",
                "total_rows": 0,
                "valid_rows": 0,
                "invalid_rows": 0,
                "row_reports": [],
            }

        return {
            "is_valid": invalid_count == 0,
            "total_rows": len(row_reports),
            "valid_rows": valid_count,
            "invalid_rows": invalid_count,
            "row_reports": row_reports,
        }

