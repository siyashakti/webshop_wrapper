(() => {
	const CHIP_THRESHOLD = 8;

	class InlineVariantSelector {
		constructor($root) {
			this.$root = $root;
			this.itemCode = $root.data("template-item-code");
			this.hasVariants = cint($root.data("has-variants")) === 1;
			this.enableVariants = cint($root.data("enable-variants")) === 1;
			this.showPrice = cint($root.data("show-price")) === 1;
			this.showStock = cint($root.data("show-stock")) === 1;
			this.allowOutOfStock = cint($root.data("allow-out-of-stock")) === 1;
			this.uom = $root.data("uom") || "";

			this.$controls = $root.find('[data-role="variant-controls"]');
			this.$feedback = $root.find('[data-role="variant-feedback"]');
			this.$priceSlot = $root.find('[data-role="price-slot"]');
			this.$stockSlot = $root.find('[data-role="stock-slot"]');
			this.$addBtn = $root.find(".btn-add-to-cart");
			this.$viewBtn = $root.find(".btn-view-in-cart");
			this.$qtyInput = $root.find('[data-role="qty-input"]');

			this.attributeData = [];
			this.selected = {};
			this.validOptions = {};
			this.exactVariant = "";
			this.selectedProductInfo = null;
			this.selectedStockQty = 0;

			if (!this.hasVariants || !this.enableVariants || !this.$controls.length) {
				this.bindCommonActions();
				return;
			}

			this.init();
		}

		async init() {
			this.disableAddButton();
			this.setFeedback("{{ _('Loading variants...') }}", "warn");

			try {
				this.attributeData = await this.getAttributesAndValues();
				this.attributeData.forEach((attr) => {
					this.validOptions[attr.attribute] = new Set(attr.values || []);
				});
				this.renderControls();
				this.setFeedback("{{ _('Select options to enable add to cart.') }}", "");
			} catch (e) {
				this.setFeedback("{{ _('Could not load variants. Please refresh and try again.') }}", "error");
			}

			this.bindCommonActions();
		}

		renderControls() {
			this.$controls.empty();

			(this.attributeData || []).forEach((attr) => {
				const values = attr.values || [];
				const selectedValue = this.selected[attr.attribute] || "";
				const group = document.createElement("div");
				group.className = "wsw-variant-group";
				group.setAttribute("data-attribute", attr.attribute);

				const selectedLabel = selectedValue ? frappe.utils.escape_html(selectedValue) : "";
				group.innerHTML = `
					<div class="wsw-variant-label">
						<span>${frappe.utils.escape_html(attr.attribute)}</span>
						<span class="wsw-variant-value" data-role="selected-value">${selectedLabel}</span>
					</div>
				`;

				if (values.length > CHIP_THRESHOLD) {
					const select = document.createElement("select");
					select.className = "wsw-variant-select";
					select.setAttribute("data-role", "variant-select");
					select.setAttribute("data-attribute", attr.attribute);
					select.innerHTML = `
						<option value="">${__("Select {0}", [attr.attribute])}</option>
					`;

					values.forEach((value) => {
						const option = document.createElement("option");
						option.value = value;
						option.textContent = value;
						if (selectedValue === value) option.selected = true;
						if (!this.isOptionValid(attr.attribute, value)) option.disabled = true;
						select.appendChild(option);
					});

					group.appendChild(select);
				} else {
					const chips = document.createElement("div");
					chips.className = "wsw-chip-row";
					values.forEach((value) => {
						const button = document.createElement("button");
						button.type = "button";
						button.className = "wsw-variant-chip";
						button.textContent = value;
						button.setAttribute("data-role", "variant-chip");
						button.setAttribute("data-attribute", attr.attribute);
						button.setAttribute("data-value", value);
						if (selectedValue === value) button.classList.add("active");
						if (!this.isOptionValid(attr.attribute, value)) button.disabled = true;
						chips.appendChild(button);
					});
					group.appendChild(chips);
				}

				this.$controls.append(group);
			});
		}

		bindCommonActions() {
			this.$root.on("click", '[data-role="variant-chip"]', (e) => {
				const $btn = $(e.currentTarget);
				if ($btn.prop("disabled")) return;
				const attribute = $btn.data("attribute");
				const value = $btn.data("value");
				if (!attribute || !value) return;

				if (this.selected[attribute] === value) {
					delete this.selected[attribute];
				} else {
					this.selected[attribute] = value;
				}
				this.onSelectionChange();
			});

			this.$root.on("change", '[data-role="variant-select"]', (e) => {
				const $select = $(e.currentTarget);
				const attribute = $select.data("attribute");
				const value = $select.val();
				if (!attribute) return;

				if (!value) {
					delete this.selected[attribute];
				} else {
					this.selected[attribute] = value;
				}
				this.onSelectionChange();
			});

			this.$root.on("click", ".btn-add-to-cart", (e) => {
				const $btn = $(e.currentTarget);
				if ($btn.prop("disabled")) return;
				const itemCode = $btn.data("item-code");
				if (!itemCode) return;
				const qty = this.getSelectedQty();

				$btn.prop("disabled", true).addClass("wsw-add-spin");
				webshop.webshop.shopping_cart.update_cart({
					item_code: itemCode,
					qty,
					callback: (r) => {
						$btn.prop("disabled", false).removeClass("wsw-add-spin");
						if (r.message) {
							this.$addBtn.addClass("hidden");
							this.$viewBtn.removeClass("hidden");
						}
					},
				});
			});

			this.$root.on("click", '[data-role="qty-minus"]', () => {
				if (!this.$qtyInput.length) return;
				const qty = Math.max(1, this.getSelectedQty() - 1);
				this.$qtyInput.val(qty);
			});

			this.$root.on("click", '[data-role="qty-plus"]', () => {
				if (!this.$qtyInput.length) return;
				const qty = this.getSelectedQty() + 1;
				this.$qtyInput.val(qty);
			});

			this.$root.on("input change", '[data-role="qty-input"]', () => {
				if (!this.$qtyInput.length) return;
				const qty = this.getSelectedQty();
				this.$qtyInput.val(qty);
			});

			this.$root.on("click", ".offer-details", (e) => {
				e.preventDefault();
				const $btn = $(e.currentTarget);
				$btn.prop("disabled", true);

				const dialog = new frappe.ui.Dialog({
					title: __($btn.data("offer-title")),
					fields: [
						{ fieldname: "offer_details", fieldtype: "HTML" },
						{ fieldname: "section_break", fieldtype: "Section Break" },
					],
				});

				frappe.call({
					method: "webshop.webshop.doctype.website_offer.website_offer.get_offer_details",
					args: { offer_id: $btn.data("offer-id") },
					callback: (value) => {
						dialog.set_value("offer_details", value.message);
						dialog.show();
						$btn.prop("disabled", false);
					},
				});
			});

			this.$root.on("click", ".like-action-item-fp", (e) => {
				const $btn = $(e.currentTarget);
				$btn.removeClass("like-animate");
				webshop.webshop.wishlist.wishlist_action($btn);
			});
		}

		async onSelectionChange() {
			if (!this.hasVariants || !this.enableVariants) return;

			if (!Object.keys(this.selected).length) {
				this.resetSelectionState();
				this.renderControls();
				this.setFeedback("{{ _('Select options to enable add to cart.') }}", "");
				return;
			}

			this.disableAddButton();
			this.setFeedback("{{ _('Finding matching variant...') }}", "warn");

			try {
				const data = await this.getNextAttributeAndValues(this.selected);
				this.validOptions = {};
				Object.keys(data.valid_options_for_attributes || {}).forEach((attribute) => {
					this.validOptions[attribute] = new Set(data.valid_options_for_attributes[attribute] || []);
				});

				this.exactVariant = "";
				this.selectedProductInfo = data.product_info || null;
				this.selectedStockQty = data && data.available_qty ? Number(data.available_qty) : 0;

				if (Array.isArray(data.exact_match) && data.exact_match.length === 1) {
					this.exactVariant = data.exact_match[0];
					this.enableAddButton(this.exactVariant, data);
					this.setFeedback(__('{0} selected', [this.exactVariant]), "valid");
				} else if (data.filtered_items_count === 0) {
					this.setFeedback("{{ _('No variant matches this combination.') }}", "error");
				} else {
					this.setFeedback(__('{0} variants match. Refine selection.', [data.filtered_items_count]), "warn");
				}

				this.renderPriceAndStock(data);
				this.clearInvalidSelectedValues();
				this.renderControls();
			} catch (e) {
				this.disableAddButton();
				this.setFeedback("{{ _('Could not validate variant selection right now.') }}", "error");
			}
		}

		clearInvalidSelectedValues() {
			Object.keys(this.selected).forEach((attribute) => {
				const allowed = this.validOptions[attribute];
				if (allowed && !allowed.has(this.selected[attribute])) {
					delete this.selected[attribute];
				}
			});
		}

		resetSelectionState() {
			this.exactVariant = "";
			this.selectedProductInfo = null;
			this.selectedStockQty = 0;
			this.attributeData.forEach((attr) => {
				this.validOptions[attr.attribute] = new Set(attr.values || []);
			});
			this.disableAddButton();
			this.renderPriceAndStock(null);
		}

		renderPriceAndStock(variantData) {
			if (this.showPrice) {
				if (this.selectedProductInfo && this.selectedProductInfo.price) {
					const price = this.selectedProductInfo.price;
					const salesPrice = frappe.utils.escape_html(price.formatted_price_sales_uom || "");
					const mrp = frappe.utils.escape_html(price.formatted_mrp || "");
					const discount = frappe.utils.escape_html(
						price.formatted_discount_percent || price.formatted_discount_rate || ""
					);
					const basePrice = frappe.utils.escape_html(price.formatted_price || "");

					this.$priceSlot.html(`
						<div class="product-price" itemprop="offers" itemscope itemtype="https://schema.org/AggregateOffer">
							<span itemprop="highPrice" content="${salesPrice}">${salesPrice}</span>
							${
								mrp
									? `<small itemprop="highPrice" class="formatted-price"><s>MRP ${mrp}</s></small>`
									: ""
							}
							${discount ? `<small class="ml-1 formatted-price in-green">-${discount}</small>` : ""}
							${
								basePrice
									? `<small class="formatted-price ml-2">(${basePrice} / ${frappe.utils.escape_html(this.uom)})</small>`
									: ""
							}
						</div>
					`);
				} else {
					this.$priceSlot.html(`<div class="wsw-muted-meta">${__("Select a variant to see live price")}</div>`);
				}
			}

			if (this.showStock) {
				if (!this.exactVariant) {
					this.$stockSlot.empty();
					return;
				}

				const availableQty = variantData && variantData.available_qty ? Number(variantData.available_qty) : 0;
				this.selectedStockQty = availableQty;
				if (availableQty > 0) {
					this.$stockSlot.html(
						`<span class="in-green has-stock"><span class="wsw-check-icon">&#10003;</span>${__("In Stock")} (${frappe.utils.escape_html(String(availableQty))})</span>`
					);
				} else if (this.allowOutOfStock) {
					this.$stockSlot.html(
						`<span class="no-stock out-of-stock" style="color: var(--primary-color);">${__("Available on backorder")}</span>`
					);
				} else {
					this.$stockSlot.html(`<span class="no-stock out-of-stock">${__("Out of stock")}</span>`);
				}
			}
		}

			disableAddButton() {
			this.$addBtn.prop("disabled", true);
			this.$addBtn.removeClass("hidden");
			this.$addBtn.removeData("item-code");
			this.$addBtn.attr("data-item-code", "");
			this.$viewBtn.addClass("hidden");
		}

		enableAddButton(itemCode, data) {
			const isStockItem = this.selectedProductInfo ? cint(this.selectedProductInfo.is_stock_item) === 1 : true;
			const availableQty = data && data.available_qty ? Number(data.available_qty) : 0;
			this.selectedStockQty = availableQty;
			const hasStock = availableQty > 0;
			const canAdd = !!itemCode && (!isStockItem || this.allowOutOfStock || hasStock);

			this.$addBtn.attr("data-item-code", itemCode);
			this.$addBtn.data("item-code", itemCode);
			this.$addBtn.prop("disabled", !canAdd);

			if (!canAdd) {
				this.setFeedback("{{ _('Selected variant is out of stock.') }}", "error");
			}
		}

		setFeedback(message, stateClass) {
			this.$feedback.removeClass("valid warn error");
			if (stateClass) this.$feedback.addClass(stateClass);
			this.$feedback.text(message || "");
		}

		isOptionValid(attribute, value) {
			const validSet = this.validOptions[attribute];
			if (!validSet) return true;
			return validSet.has(value);
		}

		getSelectedQty() {
			if (!this.$qtyInput.length) return 1;
			const currentQty = Number.parseInt(this.$qtyInput.val(), 10) || 1;
			if (this.selectedStockQty > 0 && currentQty > this.selectedStockQty && !this.allowOutOfStock) {
				return this.selectedStockQty;
			}
			return Math.max(1, currentQty);
		}

		getAttributesAndValues() {
			return this.call("webshop.webshop.variant_selector.utils.get_attributes_and_values", {
				item_code: this.itemCode,
			});
		}

		getNextAttributeAndValues(selectedAttributes) {
			return this.call("webshop_wrapper.api.variant_selector.get_next_attribute_and_values", {
				item_code: this.itemCode,
				selected_attributes: selectedAttributes,
			});
		}

		call(method, args) {
			return new Promise((resolve, reject) => {
				frappe
					.call(method, args)
					.then((r) => resolve(r.message))
					.fail(reject);
			});
		}
	}

	function cint(value) {
		return Number.parseInt(value, 10) || 0;
	}

	frappe.ready(() => {
		const $root = $(".wsw-product-details");
		if (!$root.length) return;
		new InlineVariantSelector($root);
	});
})();
