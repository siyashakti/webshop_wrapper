import unittest

import frappe

from webshop.webshop.doctype.webshop_settings.test_webshop_settings import (
	setup_webshop_settings,
)
from webshop_wrapper.api.product_listing import WrapperProductQuery


class TestWrapperProductQuery(unittest.TestCase):
	"""Test attribute filtering with WrapperProductQuery."""

	@classmethod
	def setUpClass(cls):
		setup_webshop_settings(
			{
				"products_per_page": 4,
				"enable_attribute_filters": 1,
				"filter_attributes": [{"attribute": "Size"}, {"attribute": "Colour"}],
				"company": "_Test Company",
				"enabled": 1,
				"default_customer_group": "_Test Customer Group",
				"price_list": "_Test Price List India",
			}
		)
		frappe.local.shopping_cart_settings = None

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

	def test_single_attribute_filter_returns_matching_templates(self):
		"""Test that filtering by a single attribute returns matching templates."""
		engine = WrapperProductQuery()
		result = engine.query(
			attributes={"Colour": ["Red"]},
			fields={},
			search_term=None,
			start=0,
			item_group=None,
		)
		items = result.get("items")

		self.assertGreater(len(items), 0, "Should return templates with Red variants")
		for item in items:
			self.assertTrue(item.has_variants, f"Item {item.item_code} should be a template")

	def test_multiple_attribute_filters_intersection(self):
		"""Test that multiple attribute filters return only templates with variants matching ALL attributes."""
		engine = WrapperProductQuery()
		result = engine.query(
			attributes={"Colour": ["Red"], "Size": ["Large"]},
			fields={},
			search_term=None,
			start=0,
			item_group=None,
		)
		items = result.get("items")

		self.assertGreater(len(items), 0, "Should return templates with Red+Large variants")
		for item in items:
			self.assertTrue(item.has_variants, f"Item {item.item_code} should be a template")

	def test_non_existent_attribute_value_returns_empty(self):
		"""Test that a non-matching attribute filter returns empty results."""
		engine = WrapperProductQuery()
		result = engine.query(
			attributes={"Colour": ["NonExistent"]},
			fields={},
			search_term=None,
			start=0,
			item_group=None,
		)
		items = result.get("items")
		self.assertEqual(len(items), 0)

	def test_empty_attributes_returns_all_published(self):
		"""Test that empty attributes dict returns all published items."""
		engine = WrapperProductQuery()
		result = engine.query(
			attributes={},
			fields={},
			search_term=None,
			start=0,
			item_group=None,
		)
		items = result.get("items")
		self.assertGreater(len(items), 0)

	def test_multiple_values_for_same_attribute(self):
		"""Test that selecting multiple values for one attribute uses OR logic."""
		engine = WrapperProductQuery()
		result = engine.query(
			attributes={"Colour": ["Red", "Blue"]},
			fields={},
			search_term=None,
			start=0,
			item_group=None,
		)
		items = result.get("items")
		self.assertGreater(len(items), 0, "Should return templates with Red OR Blue variants")
