import frappe
from frappe import _


ROOT_LABELS = ("Men", "Women")
MAX_DEPTH = 3


def update_website_context(context):
	context.top_bar_items = build_top_bar_items()
	context.footer_items = get_footer_links()

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
	)


def get_root_groups(groups):
	selected = []
	selected_names = set()

	for label in ROOT_LABELS:
		match = next((group for group in groups if is_root_match(group, label)), None)
		if match and match.name not in selected_names:
			selected.append(match)
			selected_names.add(match.name)

	if selected:
		return selected

	fallback_roots = [group for group in groups if not group.parent_item_group and group.route]
	fallback_roots.sort(key=lambda row: (row.lft or 0, row.name))
	return fallback_roots


def is_root_match(group, label):
	label_key = normalize(group.item_group_name or group.name)
	name_key = normalize(group.name or "")
	route_key = normalize((group.route or "").split("/")[0])
	root_key = normalize(label)
	return root_key in {label_key, name_key, route_key}


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
