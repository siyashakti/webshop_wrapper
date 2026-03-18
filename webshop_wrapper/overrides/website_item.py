import frappe

from webshop.webshop.doctype.website_item.website_item import WebsiteItem


class WebshopWrapperWebsiteItem(WebsiteItem):
	website = frappe._dict(
		page_title_field="web_item_name",
		condition_field="published",
		template="webshop_wrapper/templates/generators/item/item.html",
		no_cache=1,
	)
