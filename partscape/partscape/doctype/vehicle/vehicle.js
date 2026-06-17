frappe.ui.form.on("Vehicle", {
	refresh(frm) {
		// Variant should belong to the selected Vehicle Model.
		frm.set_query("variant", () => {
			return {
				filters: frm.doc.model ? { model: frm.doc.model } : {},
			};
		});
	},

	variant(frm) {
		if (!frm.doc.variant) {
			frm.set_value("engine_code", "");
			frm.set_value("transmission", "");
			return;
		}

		frappe.db.get_value(
			"Vehicle Engine Variant",
			frm.doc.variant,
			["engine_code", "transmission"],
			(r) => {
				if (r) {
					frm.set_value("engine_code", r.engine_code || "");
					frm.set_value("transmission", r.transmission || "");
				}
			}
		);
	},
});
