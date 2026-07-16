"""Inventory business logic and helpers."""

from sqlalchemy.orm import Session

from backend.app.models import (
    Listing,
    ListingCategory,
    OutboxEvent,
    RealEstateListing,
    VehicleListing,
    VesselAircraftListing,
    WatchJewelryListing,
    RentalTerms,
)


class InventoryService:
    @staticmethod
    def queue_listing_changed(db: Session, listing: Listing, change_type: str) -> None:
        db.add(
            OutboxEvent(
                aggregate_type="listing",
                aggregate_id=str(listing.id),
                event_type="listing.changed",
                payload={
                    "listing_id": listing.id,
                    "change_type": change_type,
                    "category": listing.category.value,
                    "status": listing.status.value,
                    "moderation_status": listing.moderation_status.value,
                },
            )
        )

    @staticmethod
    def upsert_listing_details(db: Session, listing: Listing, details: dict | None = None) -> None:
        """Persist category-specific metadata in CTI subtype tables."""
        data = {**(listing.attributes or {}), **(details or {})}

        if listing.category == ListingCategory.real_estate:
            row = listing.real_estate_details or RealEstateListing(listing_id=listing.id)
            row.area_value = data.get("area_value") or data.get("square_meters") or listing.square_footage
            row.area_unit = data.get("area_unit") or ("sqft" if listing.square_footage else None)
            row.acreage = data.get("acreage")
            row.bedrooms = data.get("bedrooms", listing.bedrooms)
            row.bathrooms = data.get("bathrooms", listing.bathrooms)
            row.property_type_id = data.get("property_type_id")
            listing.square_footage = row.area_value
            listing.bedrooms = row.bedrooms
            listing.bathrooms = row.bathrooms
            db.add(row)
            return

        if listing.category in {ListingCategory.car, ListingCategory.hypercar}:
            row = listing.vehicle_details or VehicleListing(listing_id=listing.id)
            row.make_id = data.get("make_id")
            row.model_id = data.get("model_id")
            row.make = data.get("make", listing.make)
            row.model = data.get("model", listing.model)
            row.year = data.get("year", listing.year)
            row.mileage_value = data.get("mileage_value", listing.mileage)
            row.mileage_unit = data.get("mileage_unit", "mi" if listing.mileage else None)
            row.vin_ciphertext = data.get("vin_ciphertext") or data.get("vin")
            row.steering_side = data.get("steering_side") or data.get("drive_side")
            listing.make = row.make
            listing.model = row.model
            listing.year = row.year
            listing.mileage = row.mileage_value
            db.add(row)
            return

        if listing.category in {ListingCategory.yacht, ListingCategory.jet}:
            row = listing.vessel_aircraft_details or VesselAircraftListing(listing_id=listing.id)
            row.asset_type = listing.category.value
            row.builder_id = data.get("builder_id")
            row.builder = data.get("builder") or listing.make
            row.year = data.get("year", listing.year)
            row.length_value = data.get("length_value") or data.get("length")
            row.length_unit = data.get("length_unit")
            row.cabins = data.get("cabins")
            row.engine_hours = data.get("engine_hours")
            listing.make = row.builder
            listing.year = row.year
            listing.attributes = {
                **(listing.attributes or {}),
                "length_value": row.length_value,
                "length_unit": row.length_unit,
            }
            db.add(row)
            return

        if listing.category in {ListingCategory.watch, ListingCategory.jewelry}:
            row = listing.watch_jewelry_details or WatchJewelryListing(listing_id=listing.id)
            row.asset_type = listing.category.value
            row.brand_id = data.get("brand_id")
            row.brand = data.get("brand") or listing.make
            row.reference_number = data.get("reference_number") or listing.model
            row.case_material_id = data.get("case_material_id")
            row.movement_id = data.get("movement_id")
            row.case_material = data.get("case_material")
            row.movement = data.get("movement")
            listing.make = row.brand
            listing.model = row.reference_number
            db.add(row)
            return

        if listing.category == ListingCategory.rental:
            row = listing.rental_terms or RentalTerms(listing_id=listing.id)
            row.min_nights = data.get("min_nights")
            row.availability_calendar_id = data.get("availability_calendar_id")
            row.pricing_tiers = data.get("pricing_tiers", {})
            db.add(row)
            return
