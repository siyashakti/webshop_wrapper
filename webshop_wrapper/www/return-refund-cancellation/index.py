import frappe
from frappe import _

from webshop_wrapper.api.legal_documents import get_latest_published_legal_content

sitemap = 1
no_cache = 1


def get_context(context):
	context.title = _("Return, Refund and Cancellation")
	context.no_breadcrumbs = 1

	content = get_latest_published_legal_content("Return, Refund & Cancellation")
	if content:
		context.content = content
	else:
		frappe.local.response["http_status_code"] = 404
		context.content = _("<p>Return, Refund and Cancellation policy is not available yet.</p>")

	return context
