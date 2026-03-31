import frappe
from frappe import _

ROOT_LABELS = ("Men", "Women")
ROOT_ALIASES = {
	"men": {"men", "mens"},
	"women": {"women", "womens"},
}
MAX_DEPTH = 3


def update_website_context(context):
	context.top_bar_items = build_top_bar_items()
	context.footer_groups = get_footer_groups()
	context.footer_items = [link for group in context.footer_groups for link in group.get("links", [])]
	context.footer_locale = {"language": _("English"), "country": _("India")}

	app_name = get_website_app_name()
	app_logo = get_website_app_logo()

	context.store_brand_name = app_name
	context.store_brand_logo = app_logo

	if app_logo:
		context.banner_image = app_logo
		context.brand_html = None
	else:
		context.banner_image = None
		context.brand_html = app_name


def build_top_bar_items():
	groups = get_website_groups()
	if not groups:
		return []

	children_by_parent = {}
	for group in groups:
		children_by_parent.setdefault(group.parent_item_group or "", []).append(group)

	for children in children_by_parent.values():
		children.sort(key=lambda row: (row.lft or 0, row.name))

	root_groups = get_root_groups(groups)
	items = []
	for root_group in root_groups:
		node = build_node(root_group, children_by_parent, depth=1)
		if node:
			items.append(node)

	return items


def get_website_groups():
	return frappe.get_all(
		"Item Group",
		filters={"route": ["is", "set"]},
		fields=["name", "item_group_name", "parent_item_group", "route", "lft"],
		order_by="lft asc",
	)


def get_root_groups(groups):
	selected = []
	selected_names = set()

	for label in ROOT_LABELS:
		matches = [group for group in groups if is_root_match(group, label)]
		matches.sort(key=lambda group: (route_depth(group.route), group.lft or 0, group.name))
		match = matches[0] if matches else None
		if match and match.name not in selected_names:
			selected.append(match)
			selected_names.add(match.name)

	if selected:
		return selected

	fallback_roots = [group for group in groups if not group.parent_item_group and group.route]
	fallback_roots.sort(key=lambda row: (row.lft or 0, row.name))
	return fallback_roots


def is_root_match(group, label):
	label_key = normalize(group.item_group_name or "")
	name_key = normalize(group.name or "")
	route_key = normalize(group.route or "")
	root_key = normalize(label)
	aliases = ROOT_ALIASES.get(root_key, {root_key})
	return bool({label_key, name_key, route_key}.intersection(aliases))


def route_depth(route):
	if not route:
		return 999
	return route.count("/") + 1


def build_node(group, children_by_parent, depth):
	if not group.route:
		return None

	node = {
		"label": group.item_group_name or group.name,
		"url": f"/{group.route.lstrip('/')}",
		"right": 0,
		"open_in_new_tab": 0,
	}

	if depth >= MAX_DEPTH:
		return node

	children = []
	for child in children_by_parent.get(group.name, []):
		child_node = build_node(child, children_by_parent, depth + 1)
		if child_node:
			children.append(child_node)

	if children:
		node["child_items"] = children

	return node


def normalize(value):
	return "".join(char for char in (value or "").lower().strip() if char.isalnum())


def get_website_app_name():
	return frappe.get_website_settings("app_name") or _("Store")


def get_website_app_logo():
	return frappe.get_website_settings("app_logo")


def get_footer_links():
	return [
		{"label": _("Size Chart"), "url": "/size-chart", "right": 0, "open_in_new_tab": 0},
		{"label": _("Mens Products"), "url": "/men", "right": 0, "open_in_new_tab": 0},
		{"label": _("Womens Products"), "url": "/women", "right": 1, "open_in_new_tab": 0},
		{"label": _("Contact"), "url": "/contact", "right": 1, "open_in_new_tab": 0},
	]


def get_footer_groups():
	return [
		# {
		# 	"title": _("Get to know us"),
		# 	"links": [
		# 		{"label": _("About"), "url": "/about", "open_in_new_tab": 0},
		# 	],
		# },
		{
			"title": _("Connect with us"),
			"links": [
				# {"label": _("Twitter"), "url": "#", "open_in_new_tab": 1},
				{
					"label": _("Instagram"),
					"url": "https://www.instagram.com/thesrmenterprises/",
					"open_in_new_tab": 1,
				},
				# {"label": _("Facebook"), "url": "#", "open_in_new_tab": 1},
			],
		},
		{
			"title": _("Quick Access"),
			"links": [
				{"label": _("Your Account"), "url": "/me", "open_in_new_tab": 0},
				{"label": _("Orders"), "url": "/orders", "open_in_new_tab": 0},
				{"label": _("Addresses"), "url": "/addresses", "open_in_new_tab": 0},
			],
		},
		{
			"title": _("Legal"),
			"links": [
				{"label": _("Privacy Policy"), "url": "/privacy-policy", "open_in_new_tab": 0},
				{
					"label": _("Terms and Conditions"),
					"url": "/terms-and-conditions",
					"open_in_new_tab": 0,
				},
				{"label": _("Cookie Policy"), "url": "/cookie-policy", "open_in_new_tab": 0},
				{"label": _("Shipping & Delivery"), "url": "/shipping-delivery-policy", "open_in_new_tab": 0},
				{
					"label": _("Return, Refund & Cancellation"),
					"url": "/return-refund-cancellation",
					"open_in_new_tab": 0,
				},
				{"label": _("Grievance Redressal"), "url": "/grievance-redressal", "open_in_new_tab": 0},
			],
		},
	]
