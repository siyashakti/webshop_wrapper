import frappe
from frappe.utils import cint

from webshop.webshop.variant_selector.utils import get_item_variant_price_dict
from webshop.webshop.variant_selector.item_variants_cache import ItemVariantsCacheManager
from webshop.webshop.doctype.webshop_settings.webshop_settings import get_shopping_cart_settings
from webshop.webshop.utils.product import get_web_item_qty_in_stock
from webshop_wrapper.variant_defaults import get_variant_selection_data


@frappe.whitelist(allow_guest=True)
def get_default_variant_selection(item_code):
	return get_variant_selection_data(item_code)


@frappe.whitelist(allow_guest=True)
def get_next_attribute_and_values(item_code, selected_attributes):
	"""Variant resolution with stock fallback to template Website Item warehouse."""
	selected_attributes = frappe.parse_json(selected_attributes)
	selected_attributes = {
		attribute: str(value)
		for attribute, value in (selected_attributes or {}).items()
		if attribute is not None and value is not None and str(value) != ""
	}

	item_cache = ItemVariantsCacheManager(item_code)
	item_variants_data = item_cache.get_item_variants_data()

	attributes = _get_item_attributes(item_code)
	attribute_list = [a.attribute for a in attributes]
	filtered_items = _get_items_with_selected_attributes(item_code, selected_attributes)

	next_attribute = None
	for attribute in attribute_list:
		if attribute not in selected_attributes:
			next_attribute = attribute
			break

	valid_options_for_attributes = frappe._dict()
	for attribute in attribute_list:
		valid_options_for_attributes[attribute] = set()
		selected_attribute = selected_attributes.get(attribute)
		if selected_attribute:
			valid_options_for_attributes[attribute].add(selected_attribute)

	for variant_row in item_variants_data:
		variant_item_code, attribute, attribute_value = variant_row
		if (
			variant_item_code in filtered_items
			and attribute not in selected_attributes
			and attribute in attribute_list
		):
			valid_options_for_attributes[attribute].add(attribute_value)

	optional_attributes = item_cache.get_optional_attributes()
	exact_match = []
	if len(selected_attributes.keys()) >= (len(attribute_list) - len(optional_attributes)):
		item_attribute_value_map = item_cache.get_item_attribute_value_map()
		for variant_item_code, attr_dict in item_attribute_value_map.items():
			if variant_item_code in filtered_items and set(attr_dict.keys()) == set(
				selected_attributes.keys()
			):
				exact_match.append(variant_item_code)

	filtered_items_count = len(filtered_items)

	if exact_match:
		cart_settings = get_shopping_cart_settings()
		product_info = get_item_variant_price_dict(exact_match[0], cart_settings)
		if product_info:
			product_info["is_stock_item"] = frappe.get_cached_value("Item", exact_match[0], "is_stock_item")
			product_info["allow_items_not_in_stock"] = cint(cart_settings.allow_items_not_in_stock)
	else:
		product_info = None

	product_id = ""
	if exact_match and len(exact_match) == 1:
		product_id = exact_match[0]
	elif filtered_items_count == 1:
		product_id = list(filtered_items)[0]

	available_qty = 0.0
	if product_id:
		stock_info = get_web_item_qty_in_stock(product_id, "website_warehouse")
		available_qty = stock_info.stock_qty or 0.0

	return {
		"next_attribute": next_attribute,
		"valid_options_for_attributes": valid_options_for_attributes,
		"filtered_items_count": filtered_items_count,
		"filtered_items": list(filtered_items) if filtered_items_count < 10 else [],
		"exact_match": exact_match,
		"product_info": product_info,
		"available_qty": available_qty,
	}


def _get_items_with_selected_attributes(item_code, selected_attributes):
	item_cache = ItemVariantsCacheManager(item_code)
	attribute_value_item_map = item_cache.get_attribute_value_item_map()
	item_attribute_value_map = item_cache.get_item_attribute_value_map()

	selected_item_sets = []
	for attribute, value in selected_attributes.items():
		filtered_items = attribute_value_item_map.get((attribute, value), [])
		selected_item_sets.append(set(filtered_items))

	if not selected_item_sets:
		return set(item_attribute_value_map.keys())

	return set.intersection(*selected_item_sets)


def _get_item_attributes(item_code):
	attributes = frappe.db.get_all(
		"Item Variant Attribute",
		fields=["attribute"],
		filters={"parenttype": "Item", "parent": item_code},
		order_by="idx asc",
	)

	optional_attributes = ItemVariantsCacheManager(item_code).get_optional_attributes()
	for attribute in attributes:
		if attribute.attribute in optional_attributes:
			attribute.optional = True

	return attributes
