/**
 * PartScape — Purchase Order Client Script
 *
 * Auto-fill PO Item fields when Part Catalog reference is selected.
 * Also handles Vehicle lookup to populate VIN.
 */

frappe.require('/assets/partscape/js/part_catalog_picker.js');
frappe.require('/assets/partscape/js/partscape_utils.js');

frappe.ui.form.on('Purchase Order', {
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

        if (!frm.is_new()) {
            frm.add_custom_button(__('Decode Vehicle VINs'), () => {
                decode_all_line_vins(frm);
            }, __('PartScape'));
        }
    }
});

frappe.ui.form.on('Purchase Order Item', {
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

    part_catalog_reference(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.part_catalog_reference) return;

        partscape.call_with_freeze(
            'partscape.api.transaction_helpers.get_part_catalog_line_details',
            { part_catalog: row.part_catalog_reference },
            __('Fetching part details...'),
            function(details) {
                partscape.apply_part_catalog_details(cdt, cdn, details);
                if (details && details.landed_cost_xcd) {
                    frappe.model.set_value(cdt, cdn, 'estimated_landed_cost_xcd', details.landed_cost_xcd);
                }
            }
        );
    }
});

function decode_all_line_vins(frm) {
    const rows = frm.doc.items || [];
    const uniqueVehicles = [...new Set(rows.filter(r => r.vehicle).map(r => r.vehicle))];
    if (!uniqueVehicles.length) {
        frappe.msgprint(__('No vehicle links found in line items.'));
        return;
    }

    const total = uniqueVehicles.length;
    let completed = 0;

    frappe.show_progress(__('Decoding VINs'), completed, total, __('Starting...'));

    uniqueVehicles.forEach(vehicle => {
        partscape.call_with_freeze(
            'partscape.api.vin_decoder.decode_vin_api',
            { vin: vehicle },
            __('Decoding VINs...')
        ).then(res => {
            completed += 1;
            if (res) {
                frappe.show_alert({
                    message: __(`Decoded ${vehicle}: ${res.make} ${res.model}`),
                    indicator: 'green'
                });
            }
            frappe.show_progress(__('Decoding VINs'), completed, total, `${completed} / ${total}`);
            if (completed >= total) {
                setTimeout(() => frappe.hide_progress(), 1500);
            }
        }).catch(() => {
            completed += 1;
            frappe.show_progress(__('Decoding VINs'), completed, total, `${completed} / ${total}`);
            if (completed >= total) {
                setTimeout(() => frappe.hide_progress(), 1500);
            }
        });
    });
}
