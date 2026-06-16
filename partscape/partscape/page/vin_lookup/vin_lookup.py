"""
PartScape — VIN Lookup Page Controller

Provides backend methods for the VIN Lookup desk page:
  • decode_vin_page(vin)           → calls the central VIN decoder
  • get_vehicle_models(make, model, year) → fuzzy-match Vehicle Model docs
  • search_part_catalog(keyword, filters)   → keyword search across Part Catalog
"""

import frappe
from frappe import _


@frappe.whitelist()
def decode_vin_page(vin: str, force_refresh: bool = False) -> dict:
	"""Whitelist wrapper that delegates to the central VIN decoder."""
	from partscape.api.vin_decoder import decode_vin
	return decode_vin(vin, force_refresh=force_refresh)


@frappe.whitelist()
def get_vehicle_models(make: str | None = None, model: str | None = None, year: int | None = None) -> list:
	"""
	Return Vehicle Model records that fuzzy-match the decoded VIN info.
	Searches by make (exact), model name (like), and optional year range.
	"""
	filters = {}
	or_filters = {}

	if make:
		filters["make"] = make

	if model:
		# Allow partial match on model_name or exact model_code
		or_filters["model_name"] = ["like", f"%{model}%"]
		or_filters["model_code"] = ["like", f"%{model}%"]

	if year:
		# Year must fall within the model's production range
		# We use raw SQL via frappe.qb for the range logic
		VehicleModel = frappe.qb.DocType("Vehicle Model")
		query = (
			frappe.qb.from_(VehicleModel)
			.select(
				VehicleModel.name,
				VehicleModel.model_name,
				VehicleModel.make,
				VehicleModel.model_code,
				VehicleModel.body_type,
				VehicleModel.year_start,
				VehicleModel.year_end,
				VehicleModel.steering_position,
				VehicleModel.primary_market,
			)
			.where(
				(VehicleModel.year_start <= year)
				& ((VehicleModel.year_end >= year) | (VehicleModel.year_end.isnull()) | (VehicleModel.year_end == 0))
			)
			.limit(50)
		)

		if make:
			query = query.where(VehicleModel.make == make)

		if model:
			query = query.where(
				(VehicleModel.model_name.like(f"%{model}%"))
				| (VehicleModel.model_code.like(f"%{model}%"))
			)

		return query.run(as_dict=True)

	# No year filter — fall back to standard get_all with make / model filters
	results = frappe.get_all(
		"Vehicle Model",
		filters=filters,
		or_filters=or_filters if or_filters else None,
		fields=[
			"name",
			"model_name",
			"make",
			"model_code",
			"body_type",
			"year_start",
			"year_end",
			"steering_position",
			"primary_market",
		],
		limit_page_length=50,
	)
	return results


@frappe.whitelist()
def search_part_catalog(keyword: str = "", filters: dict | None = None) -> list:
	"""
	Keyword search across Part Catalog.
	Searches part_number, part_name, description, brand, and category.
	"""
	if filters is None:
		filters = {}

	# Always restrict to active parts
	filters["is_active"] = 1

	or_filters = {}
	if keyword:
		kw = f"%{keyword}%"
		or_filters = {
			"part_number": ["like", kw],
			"part_name": ["like", kw],
			"description": ["like", kw],
			"brand": ["like", kw],
		}

	results = frappe.get_all(
		"Part Catalog",
		filters=filters,
		or_filters=or_filters if or_filters else None,
		fields=[
			"name",
			"part_number",
			"part_name",
			"brand",
			"category",
			"description",
			"estimated_cost_usd",
			"is_oem",
			"oem_make",
			"steering_position",
			"market_restriction",
		],
		limit_page_length=100,
		order_by="brand asc, part_number asc",
	)
	return results
