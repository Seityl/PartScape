frappe.ui.form.on("Part Catalog", {
	refresh(frm) {
		// Set per-row variant filter based on the row's Vehicle Model.
		frm.set_query("variant", "applicable_vehicles", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			return {
				filters: row.vehicle_model ? { model: row.vehicle_model } : {},
			};
		});

		// Ensure all existing applicable-vehicle rows are populated.
		(frm.doc.applicable_vehicles || []).forEach((row) => {
			if (row.vehicle_model && (!row.year_start || !row.year_end)) {
				frm.events.populate_vehicle_fields(frm, "applicable_vehicles", row.name);
			}
		});
	},

	populate_vehicle_fields(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.vehicle_model) {
			frappe.model.set_value(cdt, cdn, "year_start", "");
			frappe.model.set_value(cdt, cdn, "year_end", "");
			frappe.model.set_value(cdt, cdn, "steering_position", "Universal");
			frappe.model.set_value(cdt, cdn, "market_code", "");
			return;
		}

		frappe.db.get_doc("Vehicle Model", row.vehicle_model).then((model) => {
			let steering = "Universal";
			if (model.steering_position === "RHD") steering = "RHD";
			if (model.steering_position === "LHD") steering = "LHD";
			if (model.steering_position === "Both") steering = "Universal";

			frappe.model.set_value(cdt, cdn, "year_start", model.year_start || "");
			frappe.model.set_value(cdt, cdn, "year_end", model.year_end || "");
			frappe.model.set_value(cdt, cdn, "steering_position", steering);
			frappe.model.set_value(cdt, cdn, "market_code", model.primary_market || "");
		});
	},
});

frappe.ui.form.on("Vehicle Part Applicability", {
	vehicle_model(frm, cdt, cdn) {
		frm.events.populate_vehicle_fields(frm, cdt, cdn);

		// Clear variant if it no longer belongs to the newly selected model.
		const row = locals[cdt][cdn];
		if (row.variant && row.vehicle_model) {
			frappe.db.get_value("Vehicle Engine Variant", row.variant, "model").then((r) => {
				if (r.message && r.message.model !== row.vehicle_model) {
					frappe.model.set_value(cdt, cdn, "variant", "");
				}
			});
		}
	},

	applicable_vehicles_add(frm, cdt, cdn) {
		// New rows are automatically linked to the parent Part Catalog.
		if (frm.doc.doctype === "Part Catalog") {
			frappe.model.set_value(cdt, cdn, "part_catalog", frm.doc.name);
		}
	},
});
