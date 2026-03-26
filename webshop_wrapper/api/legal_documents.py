import frappe


def get_latest_published_legal_content(document_type):
	if not document_type:
		return None

	rows = frappe.get_all(
		"Webshop Legal Document",
		filters={"document_type": document_type, "is_published": 1},
		fields=["content"],
		order_by="date desc, modified desc",
		limit=1,
	)

	if not rows:
		return None

	return rows[0].get("content")
