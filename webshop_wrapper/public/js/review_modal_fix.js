(() => {
	function patchWriteReview() {
		const scope = $(".page_content");
		if (!scope.length) return;

		scope.off("click", ".wsw-btn-write-review");
		scope.on("click", ".wsw-btn-write-review", (e) => {
			e.preventDefault();
			e.stopImmediatePropagation();
			const btn = $(e.currentTarget);

			const dialog = new frappe.ui.Dialog({
				title: __("Write a Review"),
				fields: [
					{ fieldname: "title", fieldtype: "Data", label: __("Headline"), reqd: 1 },
					{ fieldname: "rating", fieldtype: "Rating", label: __("Overall Rating"), reqd: 1 },
					{ fieldtype: "Section Break" },
					{ fieldname: "comment", fieldtype: "Small Text", label: __("Your Review") },
				],
				primary_action() {
					const data = dialog.get_values();
					if (!data) return;

					frappe.call({
						method: "webshop.webshop.doctype.item_review.item_review.add_item_review",
						args: {
							web_item: btn.data("web-item"),
							title: data.title,
							rating: data.rating,
							comment: data.comment,
						},
						freeze: true,
						freeze_message: __("Submitting Review ..."),
						callback: (r) => {
							if (!r.exc) {
								dialog.hide();
								frappe.msgprint({
									message: __("Thank you for the review"),
									title: __("Review Submitted"),
									indicator: "green",
								});
								window.location.reload();
							}
						},
					});
				},
				primary_action_label: __("Submit"),
			});

			dialog.show();
			return false;
		});
	}

	frappe.ready(() => {
		patchWriteReview();
		$(document).on("click", '[data-role="wsw-tab"]', () => {
			setTimeout(patchWriteReview, 0);
		});
	});
})();
