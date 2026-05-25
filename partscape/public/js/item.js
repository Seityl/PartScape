/**
 * Partscape — Item Client Script
 *
 * Auto-suggest Part Catalog link when brand + part_number are entered.
 */

frappe.ui.form.on('Item', {
    brand(frm) {
        _try_link_to_catalog(frm);
    },

    part_number(frm) {
        _try_link_to_catalog(frm);
    }
});

function _try_link_to_catalog(frm) {
    const brand = (frm.doc.brand || "").trim();
    const part_number = (frm.doc.part_number || "").trim();
    if (!brand || !part_number || frm.doc.part_catalog_reference) return;

    frappe.db.get_value('Part Catalog', {brand: brand, part_number: part_number}, 'name')
        .then(r => {
            if (r.message && r.message.name) {
                frm.set_value('part_catalog_reference', r.message.name);
                frappe.show_alert({
                    message: __('Linked to Part Catalog: ') + r.message.name,
                    indicator: 'blue'
                });
            }
        });
}
