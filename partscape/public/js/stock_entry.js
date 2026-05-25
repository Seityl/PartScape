/**
 * Partscape — Stock Entry Client Script
 */

frappe.ui.form.on('Stock Entry', {
    refresh(frm) {
        if (frm.doc.purpose === 'Material Issue') {
            frm.add_custom_button(__('Create Job Card Consumption'), () => {
                frappe.msgprint(__('Job Card linking logic goes here.'));
            }, __('Partscape'));
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
