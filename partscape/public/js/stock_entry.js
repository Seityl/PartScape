/**
 * PartScape — Stock Entry Client Script
 */

frappe.require('/assets/partscape/js/part_catalog_picker.js');

frappe.ui.form.on('Stock Entry', {
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
                    frappe.model.set_value(row.doctype, row.name, 'diagram_reference', result.diagram_reference);
                    frm.refresh_field('items');
                },
            });
        }, __('PartScape'));

        if (frm.doc.purpose === 'Material Issue') {
            frm.add_custom_button(__('Create Job Card Consumption'), () => {
                frappe.msgprint(__('Job Card linking logic goes here.'));
            }, __('PartScape'));
        }
    }
});

frappe.ui.form.on('Stock Entry Detail', {
    item_code(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.item_code || row.part_catalog_reference) return;

        frappe.db.get_value('Item', row.item_code, 'part_catalog_reference')
            .then(r => {
                if (r.message && r.message.part_catalog_reference) {
                    frappe.model.set_value(cdt, cdn, 'part_catalog_reference', r.message.part_catalog_reference);
                }
            });
    }
});
