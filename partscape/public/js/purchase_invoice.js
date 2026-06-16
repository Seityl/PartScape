/**
 * PartScape — Purchase Invoice Client Script
 */

frappe.require('/assets/partscape/js/part_catalog_picker.js');

frappe.ui.form.on('Purchase Invoice', {
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

frappe.ui.form.on('Purchase Invoice Item', {
    part_catalog_reference(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.part_catalog_reference) return;

        frappe.db.get_value('Part Catalog', row.part_catalog_reference,
            ['brand', 'part_number', 'part_name', 'estimated_cost_usd', 'oem_make'])
            .then(r => {
                if (!r.message) return;
                const pc = r.message;
                frappe.model.set_value(cdt, cdn, 'item_name', pc.part_name);
                frappe.model.set_value(cdt, cdn, 'description', `${pc.part_name} — ${pc.brand} ${pc.part_number}`);

                if (!row.item_code) {
                    frappe.db.get_value('Item', {part_catalog_reference: row.part_catalog_reference}, 'name')
                        .then(ir => {
                            if (ir.message && ir.message.name) {
                                frappe.model.set_value(cdt, cdn, 'item_code', ir.message.name);
                            }
                        });
                }

                frappe.call({
                    method: 'partscape.api.interchange_api.get_interchange_numbers',
                    args: { part_catalog: row.part_catalog_reference },
                    callback(res) {
                        if (res.message) {
                            frappe.model.set_value(cdt, cdn, 'alternative_part_numbers', res.message.join(', '));
                        }
                    }
                });
            });
    },

    vehicle(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.vehicle) return;
        frappe.db.get_value('Vehicle', row.vehicle, ['vin', 'make', 'model', 'year'])
            .then(r => {
                if (r.message) {
                    frappe.model.set_value(cdt, cdn, 'vin', r.message.vin || '');
                    frappe.model.set_value(cdt, cdn, 'applicable_models',
                        `${r.message.year || ''} ${r.message.make || ''} ${r.message.model || ''}`.trim()
                    );
                }
            });
    },
});
