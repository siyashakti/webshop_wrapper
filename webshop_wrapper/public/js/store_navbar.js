frappe.ready(() => {
	if (window.matchMedia("(max-width: 991.98px)").matches) {
		return;
	}

	$(".navbar .dropdown-toggle").on("click", (event) => {
		const $target = $(event.currentTarget);
		const href = $target.attr("href");

		if (href && href !== "#") {
			event.preventDefault();
			event.stopPropagation();
			window.location.href = href;
			return;
		}

		event.preventDefault();
	});
});
