frappe.ui.form.on("Part Catalog", {
	refresh(frm) {
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

		// Filter variant options to the selected vehicle model.
		const row = locals[cdt][cdn];
		if (row.vehicle_model) {
			frm.fields_dict.applicable_vehicles.grid.get_field("variant").get_query = () => {
				return { filters: { model: row.vehicle_model } };
			};
		}
	},

	applicable_vehicles_add(frm, cdt, cdn) {
		// New rows are automatically linked to the parent Part Catalog.
		if (frm.doc.doctype === "Part Catalog") {
			frappe.model.set_value(cdt, cdn, "part_catalog", frm.doc.name);
		}
	},
});
