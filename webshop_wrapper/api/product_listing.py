import json

import frappe
from frappe.utils import cint

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
