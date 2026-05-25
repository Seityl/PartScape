/**
 * Partscape — Purchase Order Client Script
 *
 * Auto-fill PO Item fields when Part Catalog reference is selected.
 * Also handles Vehicle lookup to populate VIN.
 */

frappe.ui.form.on('Purchase Order', {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__('Decode Vehicle VINs'), () => {
                decode_all_line_vins(frm);
            }, __('Partscape'));
        }
    }
});

frappe.ui.form.on('Purchase Order Item', {
    vehicle(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.vehicle) {
            frappe.db.get_value('Vehicle', row.vehicle, ['vin', 'make', 'model', 'year'])
                .then(r => {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, 'vin', r.message.vin || '');
                        frappe.model.set_value(cdt, cdn, 'applicable_models',
                            `${r.message.year || ''} ${r.message.make || ''} ${r.message.model || ''}`.trim()
                        );
                    }
                });
        }
    },

    part_catalog_reference(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.part_catalog_reference) return;

        frappe.db.get_value('Part Catalog', row.part_catalog_reference,
            ['brand', 'part_number', 'part_name', 'diagram_reference', 'estimated_cost_usd', 'vehicle_make'])
            .then(r => {
                if (!r.message) return;
                const pc = r.message;

                // Auto-fill fields
                frappe.model.set_value(cdt, cdn, 'item_name', pc.part_name);
                frappe.model.set_value(cdt, cdn, 'description', `${pc.part_name} — ${pc.brand} ${pc.part_number}`);
                frappe.model.set_value(cdt, cdn, 'diagram_reference', pc.diagram_reference);

                // Try to find matching Item
                if (!row.item_code) {
                    frappe.db.get_value('Item', {part_catalog_reference: row.part_catalog_reference}, 'name')
                        .then(ir => {
                            if (ir.message && ir.message.name) {
                                frappe.model.set_value(cdt, cdn, 'item_code', ir.message.name);
                            }
                        });
                }

                // Populate alternative part numbers from interchange graph
                frappe.call({
                    method: 'partscape.api.interchange_api.get_interchange_numbers',
                    args: { part_catalog: row.part_catalog_reference },
                    callback(res) {
                        if (res.message) {
                            frappe.model.set_value(cdt, cdn, 'alternative_part_numbers', res.message.join(', '));
                        }
                    }
                });

                // Compute landed cost estimate
                compute_landed_cost(frm, cdt, cdn, pc.estimated_cost_usd);
            });
    }
});

function compute_landed_cost(frm, cdt, cdn, usd_cost) {
    if (!usd_cost) return;
    frappe.call({
        method: 'partscape.api.landed_cost_api.estimate_landed_cost',
        args: { usd_amount: usd_cost },
        callback(res) {
            if (res.message) {
                frappe.model.set_value(cdt, cdn, 'estimated_landed_cost_xcd', res.message.landed_xcd);
            }
        }
    });
}

function decode_all_line_vins(frm) {
    const rows = frm.doc.items || [];
    const uniqueVehicles = [...new Set(rows.filter(r => r.vehicle).map(r => r.vehicle))];
    if (!uniqueVehicles.length) {
        frappe.msgprint(__('No vehicle links found in line items.'));
        return;
    }

    uniqueVehicles.forEach(vehicle => {
        frappe.call({
            method: 'partscape.api.vin_decoder.decode_vin_api',
            args: { vin: vehicle },
            callback(res) {
                if (res.message) {
                    frappe.show_alert({
                        message: __(`Decoded ${vehicle}: ${res.message.make} ${res.message.model}`),
                        indicator: 'green'
                    });
                }
            }
        });
    });
}
