/**
 * PartScape — Delivery Note Client Script
 */

frappe.require('/assets/partscape/js/part_catalog_picker.js');
frappe.require('/assets/partscape/js/partscape_utils.js');

frappe.ui.form.on('Delivery Note', {
    refresh(frm) {
        frm.set_query('item_code', 'items', function() {
            return {
                query: 'partscape.api.smart_item_search.smart_item_search_query'
            };
        });

        frm.add_custom_button(__('Select from Part Catalog'), () => {
            partscape.showPartCatalogPicker({
                onSelect: function(result) {
                    if (!result) return;
                    const row = frm.add_child('items');
                    frappe.model.set_value(row.doctype, row.name, 'item_code', result.item_code);
                    frappe.model.set_value(row.doctype, row.name, 'item_name', result.item_name);
                    frappe.model.set_value(row.doctype, row.name, 'description', result.description);
                    frappe.model.set_value(row.doctype, row.name, 'part_catalog_reference', result.part_catalog_reference);
                    frm.refresh_field('items');
                },
            });
        }, __('PartScape'));
    },
});

frappe.ui.form.on('Delivery Note Item', {
    part_catalog_reference(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.part_catalog_reference) return;

        partscape.call_with_freeze(
            'partscape.api.transaction_helpers.get_part_catalog_line_details',
            { part_catalog: row.part_catalog_reference },
            __('Fetching part details...'),
            function(details) {
                partscape.apply_part_catalog_details(cdt, cdn, details);
            }
        );
    },

    vehicle(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.vehicle) return;

        partscape.call_with_freeze(
            'partscape.api.transaction_helpers.get_vehicle_line_details',
            { vehicle: row.vehicle },
            __('Fetching vehicle details...'),
            function(details) {
                partscape.apply_vehicle_details(cdt, cdn, details);
            }
        );
    },
});
