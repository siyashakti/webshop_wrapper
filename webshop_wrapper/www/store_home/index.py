import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder import functions as fn
from frappe.utils import add_days, nowdate


sitemap = 1
no_cache = 1


WEBSITE_ITEM_FIELDS = [
	"name",
	"item_code",
	"web_item_name",
	"website_image",
	"thumbnail",
	"item_group",
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
