import json

import frappe
from frappe.utils import cint, flt

from webshop.webshop.doctype.override_doctype.item_group import get_child_groups_for_website
from webshop.webshop.product_data_engine.filters import ProductFiltersBuilder
from webshop.webshop.product_data_engine.query import ProductQuery
from webshop.webshop.shopping_cart.product_info import get_product_info_for_website
from webshop_wrapper.variant_defaults import pick_default_variant_item_code


@frappe.whitelist(allow_guest=True)
def get_product_filter_data(query_args=None):
	if isinstance(query_args, str):
		query_args = json.loads(query_args)

	query_args = frappe._dict(query_args or {})

	if query_args:
		search = query_args.get("search")
		field_filters = query_args.get("field_filters", {})
		attribute_filters = query_args.get("attribute_filters", {})
		start = cint(query_args.start) if query_args.get("start") else 0
		item_group = query_args.get("item_group")
		from_filters = query_args.get("from_filters")
	else:
		search, attribute_filters, item_group, from_filters = None, None, None, None
		field_filters = {}
		start = 0

	if from_filters:
		start = 0

	sub_categories = []
	if item_group:
		sub_categories = get_child_groups_for_website(item_group, immediate=True)

	engine = WrapperProductQuery()

	try:
		result = engine.query(
			attribute_filters,
			field_filters,
			search_term=search,
			start=start,
			item_group=item_group,
		)
	except Exception:
		frappe.log_error("Product query with filter failed")
		return {"exc": "Something went wrong!"}

	filters = {}
	discounts = result["discounts"]

	if discounts:
		filter_engine = ProductFiltersBuilder()
		filters["discount_filters"] = filter_engine.get_discount_filters(discounts)

	return {
		"items": result["items"] or [],
		"filters": filters,
		"settings": engine.settings,
		"sub_categories": sub_categories,
		"items_count": result["items_count"],
	}


class WrapperProductQuery(ProductQuery):
	def add_display_details(self, result, discount_list, cart_items):
		for item in result:
			listing_item_code = item.item_code
			if item.get("has_variants"):
				default_variant = pick_default_variant_item_code(item.item_code)
				if default_variant:
					listing_item_code = default_variant
					item.item_code = default_variant
					item.has_variants = 0

			product_info = get_product_info_for_website(listing_item_code, skip_quotation_creation=True).get(
				"product_info"
			)

			if product_info and product_info.get("price"):
				self.get_price_discount_info(item, product_info["price"], discount_list)

			if self.settings.show_stock_availability:
				self.get_stock_availability(item)

			item.in_cart = listing_item_code in cart_items

			item.wished = False
			if frappe.db.exists(
				"Wishlist Item", {"item_code": listing_item_code, "parent": frappe.session.user}
			):
				item.wished = True

		return result, discount_list

	def query_items_with_attributes(self, attributes, start=0):
		"""Override to fix attribute filtering.

		Logic:
		1. For each attribute filter, find ALL items matching that attribute in Item Variant Attribute.
		2. For each matched item, resolve to display item: IFNULL(variant_of, item_code).
		   - Variant items resolve to their parent template.
		   - Standalone/template items resolve to themselves.
		3. Get unique display items per attribute filter.
		4. Intersect display items across different attributes (AND logic).
		5. Filter to only display items that have a published Website Item.
		"""
		published_display_items = set(
			frappe.db.get_all("Website Item", filters={"published": 1}, pluck="item_code")
		)

		if not published_display_items:
			return [], 0

		matching_display_sets = []
		for attribute, values in attributes.items():
			if not isinstance(values, list):
				values = [values]
			if not values:
				continue

			wheres = []
			query_values = []
			for value in values:
				wheres.append("(iva.attribute = %s AND iva.attribute_value = %s)")
				query_values += [attribute, value]

			attribute_query = " OR ".join(wheres)

			query = """
				SELECT DISTINCT IFNULL(i.variant_of, iva.parent)
				FROM `tabItem Variant Attribute` iva
				JOIN `tabItem` i ON i.item_code = iva.parent
				WHERE ({attribute_query})
			""".format(attribute_query=attribute_query)

			result = frappe.db.sql(query, query_values)
			display_items = {r[0] for r in result}
			matching_display_sets.append(display_items)

		if matching_display_sets:
			valid_item_codes = set.intersection(*matching_display_sets)
		else:
			valid_item_codes = set()

		valid_item_codes &= published_display_items

		if not valid_item_codes:
			return [], 0

		self.filters.append(["item_code", "in", list(valid_item_codes)])

		return self.query_items(start=start)

	def filter_results_by_discount(self, fields, result):
		"""Override to fix pagination bug where slice result was not assigned back."""
		if fields and fields.get("discount"):
			discount_percent = frappe.utils.flt(fields["discount"][0])
			result = [
				row
				for row in result
				if row.get("discount_percent") and row.discount_percent <= discount_percent
			]

		if self.filter_with_discount:
			result = result[: self.page_length]

		return result
