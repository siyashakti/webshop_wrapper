import frappe
from frappe import _

from webshop_wrapper.api.legal_documents import get_latest_published_legal_content

sitemap = 1
no_cache = 1


def get_context(context):
	context.title = _("Cookie Policy")
	context.no_breadcrumbs = 1

	content = get_latest_published_legal_content("Cookie Policy")
	if content:
		context.content = content
	else:
		frappe.local.response["http_status_code"] = 404
		context.content = _("<p>Cookie Policy is not available yet.</p>")

	return context
