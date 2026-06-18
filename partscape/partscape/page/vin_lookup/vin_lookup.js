frappe.require('/assets/partscape/js/partscape_utils.js');

frappe.pages["vin-lookup"].on_page_load = function (wrapper) {
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("VIN Lookup"),
		single_column: true,
	});

	page.vin_lookup = new PartscapeVINLookup(page);
};

class PartscapeVINLookup {
	constructor(page) {
		this.page = page;
		this.body = $(this.page.body);
		this.make();
	}

	make() {
		// Inject template HTML
		this.page.main.html(frappe.render_template("vin_lookup", {}));

		// Cache DOM references
		this.$vin_input = this.page.main.find("#vin_input");
		this.$btn_decode = this.page.main.find(".btn-decode-vin");
		this.$vehicle_section = this.page.main.find(".vehicle-info-section");
		this.$models_section = this.page.main.find(".vehicle-models-section");
		this.$parts_keyword = this.page.main.find("#parts_keyword");
		this.$btn_search_parts = this.page.main.find(".btn-search-parts");
		this.$parts_table = this.page.main.find(".parts-results-table");
		this.$no_parts = this.page.main.find(".no-parts-results");
		this.$models_table = this.page.main.find(".vehicle-models-table");
		this.$no_models = this.page.main.find(".no-vehicle-models");

		// Bind events
		this.bind_events();
	}

	bind_events() {
		let me = this;

		// Decode VIN button
		this.$btn_decode.on("click", function () {
			me.decode_vin();
		});

		// Enter key on VIN input
		this.$vin_input.on("keypress", function (e) {
			if (e.which === 13) {
				me.decode_vin();
			}
		});

		// Search parts button
		this.$btn_search_parts.on("click", function () {
			me.search_parts();
		});

		// Enter key on parts keyword input
		this.$parts_keyword.on("keypress", function (e) {
			if (e.which === 13) {
				me.search_parts();
			}
		});
	}

	decode_vin() {
		let vin = this.$vin_input.val().trim();
		if (!vin) {
			frappe.show_alert({
				message: __("Please enter a VIN or chassis number."),
				indicator: "orange",
			});
			return;
		}

		let me = this;
		partscape.set_button_loading(me.$btn_decode, true, __("Decoding..."));

		// Reset and show skeleton placeholders
		me.$vehicle_section.removeClass("hidden");
		me.$models_section.addClass("hidden");
		me._show_vehicle_skeleton();

		frappe.call({
			method: "partscape.partscape.page.vin_lookup.vin_lookup.decode_vin_page",
			args: {
				vin: vin,
				force_refresh: false,
			},
			callback: function (r) {
				partscape.set_button_loading(me.$btn_decode, false);
				if (r.message) {
					me.render_vehicle_info(r.message);
					me.fetch_matching_models(r.message);
				} else {
					frappe.show_alert({
						message: __("Could not decode VIN. Please check the number and try again."),
						indicator: "red",
					});
					me.$vehicle_section.addClass("hidden");
					me.$models_section.addClass("hidden");
				}
			},
			error: function () {
				partscape.set_button_loading(me.$btn_decode, false);
				me.$vehicle_section.addClass("hidden");
				me.$models_section.addClass("hidden");
				frappe.show_alert({
					message: __("Error decoding VIN. Please try again."),
					indicator: "red",
				});
			},
		});
	}

	_show_vehicle_skeleton() {
		this.$vehicle_section.find(".field-value").html(
			`<div class="skeleton" style="width: 70%; height: 16px;"></div>`
		);
	}

	render_vehicle_info(data) {
		this.$vehicle_section.removeClass("hidden");
		this.$vehicle_section.find(".vehicle-make").text(data.make || "—");
		this.$vehicle_section.find(".vehicle-model").text(data.model || "—");
		this.$vehicle_section.find(".vehicle-year").text(data.year || "—");
		this.$vehicle_section.find(".vehicle-engine").text(data.engine_code || "—");
		this.$vehicle_section.find(".vehicle-fuel").text(data.fuel_type || "—");
		this.$vehicle_section.find(".vehicle-transmission").text(data.transmission || "—");
		this.$vehicle_section.find(".vehicle-body").text(data.body_class || "—");
		this.$vehicle_section.find(".vehicle-steering").text(data.steering_location || data.steering || "—");
		this.$vehicle_section.find(".vehicle-plant").text(data.plant || "—");
	}

	fetch_matching_models(data) {
		let me = this;
		me.$models_section.removeClass("hidden");
		me.$models_table.removeClass("hidden");
		me.$no_models.addClass("hidden");
		me.$models_table.find("tbody").html(partscape.skeleton_table_rows(7, 3));

		frappe.call({
			method: "partscape.partscape.page.vin_lookup.vin_lookup.get_vehicle_models",
			args: {
				make: data.make || "",
				model: data.model || "",
				year: data.year || 0,
			},
			callback: function (r) {
				me.render_vehicle_models(r.message || []);
			},
			error: function () {
				me.$models_table.addClass("hidden");
				me.$no_models.removeClass("hidden");
			},
		});
	}

	render_vehicle_models(models) {
		let tbody = this.$models_table.find("tbody");
		tbody.empty();

		if (!models || models.length === 0) {
			this.$models_section.removeClass("hidden");
			this.$models_table.addClass("hidden");
			this.$no_models.removeClass("hidden");
			return;
		}

		this.$models_section.removeClass("hidden");
		this.$models_table.removeClass("hidden");
		this.$no_models.addClass("hidden");

		models.forEach(function (m) {
			let years = "";
			if (m.year_start && m.year_end) {
				years = m.year_start + " – " + m.year_end;
			} else if (m.year_start) {
				years = m.year_start + "+";
			} else {
				years = "—";
			}

			let row = `
				<tr data-name="${frappe.utils.escape_html(m.name)}">
					<td><a href="#Form/Vehicle Model/${encodeURIComponent(m.name)}">${frappe.utils.escape_html(m.model_name)}</a></td>
					<td>${frappe.utils.escape_html(m.make)}</td>
					<td>${frappe.utils.escape_html(m.model_code || "—")}</td>
					<td>${frappe.utils.escape_html(m.body_type || "—")}</td>
					<td>${frappe.utils.escape_html(years)}</td>
					<td>${frappe.utils.escape_html(m.steering_position || "—")}</td>
					<td>${frappe.utils.escape_html(m.primary_market || "—")}</td>
				</tr>
			`;
			tbody.append(row);
		});
	}

	search_parts() {
		let keyword = this.$parts_keyword.val().trim();
		let me = this;

		if (!keyword) {
			frappe.show_alert({
				message: __("Please enter a keyword."),
				indicator: "orange",
			});
			return;
		}

		partscape.set_button_loading(me.$btn_search_parts, true, __("Searching..."));
		me.$parts_table.removeClass("hidden");
		me.$no_parts.addClass("hidden");
		me.$parts_table.find("tbody").html(partscape.skeleton_table_rows(8, 4));

		frappe.call({
			method: "partscape.partscape.page.vin_lookup.vin_lookup.search_part_catalog",
			args: {
				keyword: keyword,
			},
			callback: function (r) {
				partscape.set_button_loading(me.$btn_search_parts, false);
				me.render_parts_results(r.message || []);
			},
			error: function () {
				partscape.set_button_loading(me.$btn_search_parts, false);
				me.$parts_table.addClass("hidden");
				me.$no_parts.removeClass("hidden");
				frappe.show_alert({
					message: __("Error searching parts. Please try again."),
					indicator: "red",
				});
			},
		});
	}

	render_parts_results(parts) {
		let tbody = this.$parts_table.find("tbody");
		tbody.empty();

		if (!parts || parts.length === 0) {
			this.$parts_table.addClass("hidden");
			this.$no_parts.removeClass("hidden");
			return;
		}

		this.$parts_table.removeClass("hidden");
		this.$no_parts.addClass("hidden");

		parts.forEach(function (p) {
			let cost = p.estimated_cost_usd
				? frappe.format(p.estimated_cost_usd, { fieldtype: "Currency" })
				: "—";
			let oem_badge = p.is_oem
				? '<span class="badge badge-success">' + __("OEM") + "</span>"
				: "";

			let row = `
				<tr data-name="${frappe.utils.escape_html(p.name)}">
					<td><strong>${frappe.utils.escape_html(p.part_number)}</strong></td>
					<td><a href="#Form/Part Catalog/${encodeURIComponent(p.name)}">${frappe.utils.escape_html(p.part_name)}</a></td>
					<td>${frappe.utils.escape_html(p.brand)}</td>
					<td>${frappe.utils.escape_html(p.category || "—")}</td>
					<td class="text-right">${cost}</td>
					<td>${oem_badge}</td>
					<td>${frappe.utils.escape_html(p.steering_position || "—")}</td>
					<td>${frappe.utils.escape_html(p.market_restriction || "—")}</td>
				</tr>
			`;
			tbody.append(row);
		});
	}
}
