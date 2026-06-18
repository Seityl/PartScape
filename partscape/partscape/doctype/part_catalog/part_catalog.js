frappe.require('/assets/partscape/js/partscape_utils.js');

frappe.ui.form.on("Part Catalog", {
	refresh(frm) {
		// Add action button to create ERPNext Stock Item from this Part Catalog.
		if (!frm.is_new() && !frm.doc.linked_item) {
			frm.add_custom_button(
				__("Create Stock Item"),
				() => frm.events.create_stock_item(frm),
				__("Actions")
			);
		}

		// Set per-row variant filter based on the row's Vehicle Model.
		frm.events.set_variant_query(frm);

		// Ensure all existing applicable-vehicle rows are populated.
		(frm.doc.applicable_vehicles || []).forEach((row) => {
			if (row.vehicle_model && (!row.year_start || !row.year_end)) {
				frm.events.populate_vehicle_fields(frm, "applicable_vehicles", row.name);
			}
		});
	},

	set_variant_query(frm) {
		// Filter the Engine Variant link to variants of the row's Vehicle Model.
		const grid = frm.fields_dict.applicable_vehicles?.grid;
		if (!grid) return;

		const variant_field = grid.get_field("variant");
		if (!variant_field) return;

		variant_field.get_query = function(doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return {
				filters: row.vehicle_model ? { model: row.vehicle_model } : {},
			};
		};
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

		frappe.dom.freeze(__('Fetching vehicle model details...'));
		frappe.db.get_doc("Vehicle Model", row.vehicle_model)
			.then((model) => {
				let steering = "Universal";
				if (model.steering_position === "RHD") steering = "RHD";
				if (model.steering_position === "LHD") steering = "LHD";
				if (model.steering_position === "Both") steering = "Universal";

				frappe.model.set_value(cdt, cdn, "year_start", model.year_start || "");
				frappe.model.set_value(cdt, cdn, "year_end", model.year_end || "");
				frappe.model.set_value(cdt, cdn, "steering_position", steering);
				frappe.model.set_value(cdt, cdn, "market_code", model.primary_market || "");
			})
			.catch(() => {
				frappe.show_alert({
					message: __('Unable to load vehicle model details.'),
					indicator: 'red',
				});
			})
			.finally(() => {
				frappe.dom.unfreeze();
			});
	},

	create_stock_item(frm) {
		frappe.confirm(
			__("Create a new Stock Item from {0} {1}?", [frm.doc.brand, frm.doc.part_number]),
			() => {
				frappe.call({
					method: "partscape.utils.item_factory.create_item_from_part_catalog",
					args: { part_catalog_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Creating Stock Item..."),
					callback(r) {
						if (r.message) {
							frappe.show_alert({
								message: __("Stock Item {0} created/linked", [r.message]),
								indicator: "green",
							});
							frm.reload_doc().then(() => {
								frm.refresh_field("linked_item");
							});
							frappe.set_route("Form", "Item", r.message);
						}
					},
				});
			},
			() => {}
		);
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
		} else if (!row.vehicle_model) {
			frappe.model.set_value(cdt, cdn, "variant", "");
		}
	},

	applicable_vehicles_add(frm, cdt, cdn) {
		// New rows are automatically linked to the parent Part Catalog.
		if (frm.doc.doctype === "Part Catalog") {
			frappe.model.set_value(cdt, cdn, "part_catalog", frm.doc.name);
		}
		frm.events.set_variant_query(frm);
	},
});
