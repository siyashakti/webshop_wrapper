import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder import functions as fn
from frappe.utils import add_days, cint, nowdate
from frappe.utils.data import flt
from decimal import Decimal
from datetime import date, datetime

from webshop.webshop.product_data_engine.query import ProductQuery
from webshop.webshop.shopping_cart.product_info import get_product_info_for_website
from webshop_wrapper.variant_defaults import pick_default_variant_item_code


sitemap = 1
no_cache = 1


WEBSITE_ITEM_FIELDS = [
	"name",
	"item_code",
	"web_item_name",
	"website_image",
	"thumbnail",
	"item_group",
	"has_variants",
	"route",
	"ranking",
	"modified",
]


def get_context(context):
	context.title = _("Store Home")
	context.no_breadcrumbs = 1
	context.full_width = 1
	context.body_class = "product-page store-home"

	homepage = frappe.get_cached_doc("Shoe Store Homepage", "Shoe Store Homepage")
	context.homepage = homepage
	context.slideshow = build_slideshow(homepage)
	context.collections = build_collections(homepage)
	context.top_sellers = []

	if homepage and homepage.show_top_10_best_sellers:
		context.top_sellers = get_top_sellers(limit=10, days=90)

	query_engine = ProductQuery()
	cart_items = query_engine.get_cart_items() if query_engine.settings.enabled else []

	context.top_sellers = decorate_items_for_cards(context.top_sellers, query_engine, cart_items)
	context.collections = [
		{
			"title": collection["title"],
			"item_group": collection["item_group"],
			"item_group_route": collection["item_group_route"],
			"items": decorate_items_for_cards(collection["items"], query_engine, cart_items),
		}
		for collection in context.collections
	]

	context.sections = []
	if context.top_sellers:
		context.sections.append(
			{
				"title": _("Top 10"),
				"item_group_route": "all-products",
				"cta_label": _("Show More"),
				"items": context.top_sellers,
			}
		)

	for collection in context.collections:
		context.sections.append(
			{
				"title": collection["title"],
				"item_group_route": collection["item_group_route"],
				"cta_label": _("Show More"),
				"items": collection["items"],
			}
		)

	context.card_settings = {
		"enabled": cint(query_engine.settings.enabled),
		"enable_wishlist": cint(query_engine.settings.enable_wishlist),
		"show_stock_availability": cint(query_engine.settings.show_stock_availability),
		"allow_items_not_in_stock": cint(query_engine.settings.allow_items_not_in_stock),
		"enable_checkout": cint(query_engine.settings.enable_checkout),
	}

	return context


def build_slideshow(homepage):
	if not homepage or not homepage.slides:
		return None

	values = {
		"show_indicators": 1,
		"show_controls": 1,
		"rounded": 1,
		"slider_name": "Store Home",
	}

	for index, slide in enumerate(homepage.slides[:5], start=1):
		if not (slide.hero_image or slide.heading or slide.subheading):
			continue

		values[f"slide_{index}_image"] = slide.hero_image
		values[f"slide_{index}_title"] = slide.heading
		values[f"slide_{index}_subtitle"] = slide.subheading
		values[f"slide_{index}_primary_action"] = slide.button_link
		values[f"slide_{index}_primary_action_label"] = slide.button_text
		values[f"slide_{index}_content_align"] = "Centre"
		values[f"slide_{index}_theme"] = "Light"

	return values


def build_collections(homepage):
	if not homepage or not homepage.collections:
		return []

	collections = []
	for row in homepage.collections:
		if not row.item_group:
			continue

		items = get_items_for_group(row.item_group, limit=12)
		if not items:
			continue

		collections.append(
			{
				"title": row.section_title or row.item_group,
				"item_group": row.item_group,
				"item_group_route": frappe.db.get_value("Item Group", row.item_group, "route"),
				"items": items,
			}
		)

	return collections


def get_items_for_group(item_group, limit=12):
	if not item_group:
		return []

	direct_items = frappe.get_all(
		"Website Item",
		fields=WEBSITE_ITEM_FIELDS,
		filters={"published": 1, "item_group": item_group},
		order_by="ranking desc, modified desc",
		limit=limit,
	)

	group_item_names = frappe.get_all(
		"Website Item Group",
		filters={"item_group": item_group},
		pluck="parent",
	)

	group_items = []
	if group_item_names:
		group_items = frappe.get_all(
			"Website Item",
			fields=WEBSITE_ITEM_FIELDS,
			filters={"published": 1, "name": ["in", group_item_names]},
			order_by="ranking desc, modified desc",
			limit=limit,
		)

	items = merge_items_by_ranking(direct_items, group_items, limit=limit)
	return normalize_item_images(items)


def merge_items_by_ranking(primary, secondary, limit=12):
	items = []
	seen = set()

	for item in primary + secondary:
		if item.name in seen:
			continue
		seen.add(item.name)
		items.append(item)

	items.sort(key=lambda x: (x.get("ranking") or 0, x.get("modified") or ""), reverse=True)
	return items[:limit]


def normalize_item_images(items):
	for item in items:
		if not item.get("website_image") and item.get("thumbnail"):
			item["website_image"] = item.get("thumbnail")
	return items


def decorate_items_for_cards(items, query_engine, cart_items):
	if not items:
		return []

	decorated = []
	for source_item in items:
		item = frappe._dict(source_item)
		item.wished = False
		item.formatted_price = ""
		item.formatted_mrp = ""
		item.discount = ""
		item.in_stock = 0

		listing_item_code = item.item_code
		if item.get("has_variants"):
			default_variant_item_code = pick_default_variant_item_code(item.item_code)
			if default_variant_item_code:
				listing_item_code = default_variant_item_code
				item.item_code = default_variant_item_code
				item.has_variants = 0

		product_info = get_product_info_for_website(listing_item_code, skip_quotation_creation=True).get(
			"product_info"
		)

		if product_info and product_info.get("price"):
			price = product_info["price"]
			item.formatted_price = price.get("formatted_price")
			item.formatted_mrp = price.get("formatted_mrp")
			if price.get("discount_percent"):
				item.discount_percent = flt(price.get("discount_percent"))
			item.discount = price.get("formatted_discount_percent") or price.get("formatted_discount_rate")

		if query_engine.settings.show_stock_availability:
			item.in_stock = cint(product_info.get("in_stock")) if product_info else 0
			if product_info and product_info.get("on_backorder"):
				item.on_backorder = 1

		item.in_cart = listing_item_code in cart_items

		if frappe.session.user != "Guest" and frappe.db.exists(
			"Wishlist Item", {"item_code": listing_item_code, "parent": frappe.session.user}
		):
			item.wished = True

		decorated.append(make_json_safe_item(dict(item)))

	return decorated


def make_json_safe_item(item):
	json_safe = {}
	for key, value in item.items():
		if isinstance(value, (datetime, date)):
			json_safe[key] = value.isoformat()
		elif isinstance(value, Decimal):
			json_safe[key] = float(value)
		else:
			json_safe[key] = value

	return json_safe


def get_top_sellers(limit=10, days=90):
	from_date = add_days(nowdate(), -days)

	sales_invoice_item = frappe.qb.DocType("Sales Invoice Item")
	sales_invoice = frappe.qb.DocType("Sales Invoice")
	website_item = frappe.qb.DocType("Website Item")

	query = (
		frappe.qb.from_(sales_invoice_item)
		.join(sales_invoice)
		.on(sales_invoice_item.parent == sales_invoice.name)
		.join(website_item)
		.on(website_item.item_code == sales_invoice_item.item_code)
		.select(
			website_item.name,
			website_item.item_code,
			website_item.web_item_name,
			website_item.website_image,
			website_item.thumbnail,
			website_item.item_group,
			website_item.has_variants,
			website_item.route,
			website_item.ranking,
			website_item.modified,
			fn.Sum(sales_invoice_item.qty).as_("sold_qty"),
		)
		.where(sales_invoice.docstatus == 1)
		.where(sales_invoice.is_return == 0)
		.where(sales_invoice.posting_date >= from_date)
		.where(website_item.published == 1)
		.groupby(
			website_item.name,
			website_item.item_code,
			website_item.web_item_name,
			website_item.website_image,
			website_item.thumbnail,
			website_item.item_group,
			website_item.has_variants,
			website_item.route,
			website_item.ranking,
			website_item.modified,
		)
		.orderby(fn.Sum(sales_invoice_item.qty), order=Order.desc)
		.orderby(website_item.ranking, order=Order.desc)
		.limit(limit)
	)

	items = query.run(as_dict=True)
	if not items:
		items = frappe.get_all(
			"Website Item",
			fields=WEBSITE_ITEM_FIELDS,
			filters={"published": 1},
			order_by="ranking desc, modified desc",
			limit=limit,
		)

	return normalize_item_images(items)
