import frappe
from frappe.utils import cint

from webshop.webshop.doctype.webshop_settings.webshop_settings import get_shopping_cart_settings
from webshop.webshop.utils.product import get_web_item_qty_in_stock
from webshop.webshop.variant_selector.utils import get_item_variant_price_dict


def get_enabled_variant_codes(template_item_code):
	if not template_item_code:
		return []

	return frappe.get_all(
		"Item",
		filters={"variant_of": template_item_code, "disabled": 0},
		pluck="item_code",
		order_by="item_code asc",
	)


def pick_default_variant_item_code(template_item_code):
	variant_codes = get_enabled_variant_codes(template_item_code)
	if not variant_codes:
		return None

	for variant_code in variant_codes:
		stock_info = get_web_item_qty_in_stock(variant_code, "website_warehouse")
		if (stock_info.stock_qty or 0) > 0:
			return variant_code

	return variant_codes[0]


def get_variant_selection_data(template_item_code):
	default_variant_item_code = pick_default_variant_item_code(template_item_code)
	if not default_variant_item_code:
		return {
			"default_variant_item_code": None,
			"selected_attributes": {},
			"product_info": None,
			"available_qty": 0,
		}

	attributes = frappe.get_all(
		"Item Variant Attribute",
		filters={"parenttype": "Item", "parent": default_variant_item_code},
		fields=["attribute", "attribute_value"],
		order_by="idx asc",
	)
	selected_attributes = {
		row.attribute: row.attribute_value for row in attributes if row.attribute and row.attribute_value
	}

	cart_settings = get_shopping_cart_settings()
	product_info = get_item_variant_price_dict(default_variant_item_code, cart_settings)
	if product_info:
		product_info["is_stock_item"] = frappe.get_cached_value(
			"Item", default_variant_item_code, "is_stock_item"
		)
		product_info["allow_items_not_in_stock"] = cint(cart_settings.allow_items_not_in_stock)

	stock_info = get_web_item_qty_in_stock(default_variant_item_code, "website_warehouse")
	available_qty = stock_info.stock_qty or 0

	return {
		"default_variant_item_code": default_variant_item_code,
		"selected_attributes": selected_attributes,
		"product_info": product_info,
		"available_qty": available_qty,
	}
