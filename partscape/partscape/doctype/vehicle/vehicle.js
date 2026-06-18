frappe.require('/assets/partscape/js/partscape_utils.js');

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

		frappe.dom.freeze(__('Fetching engine variant details...'));
		frappe.db.get_value(
			"Vehicle Engine Variant",
			frm.doc.variant,
			["engine_code", "transmission"],
			(r) => {
				frappe.dom.unfreeze();
				if (r) {
					frm.set_value("engine_code", r.engine_code || "");
					frm.set_value("transmission", r.transmission || "");
				}
			}
		).catch(() => {
			frappe.dom.unfreeze();
			frappe.show_alert({
				message: __('Unable to load engine variant details.'),
				indicator: 'red',
			});
		});
	},
});
