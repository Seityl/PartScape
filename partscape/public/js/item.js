/**
 * PartScape — Item Client Script
 *
 * Auto-suggest Part Catalog link when brand + part_number are entered,
 * and provide Brother QL-800 browser label printing.
 */

frappe.ui.form.on('Item', {
    refresh(frm) {
        _add_label_buttons(frm);
    },

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

function _add_label_buttons(frm) {
    if (frm.is_new()) return;

    frm.add_custom_button(__('Print Label'), () => {
        _show_print_label_dialog(frm, 'Item');
    });

    if (!frm.doc.partscape_barcode) {
        frm.add_custom_button(__('Generate Barcode'), () => {
            _generate_barcode(frm);
        });
    }
}

function _generate_barcode(frm) {
    frappe.call({
        method: 'partscape.print_label.generate_barcode',
        args: { item_code: frm.doc.name },
        freeze: true,
        freeze_message: __('Generating barcode...'),
        callback(r) {
            if (r.exc) return;
            frm.set_value('partscape_barcode', r.message);
            frappe.show_alert({
                message: __('Barcode generated: ') + r.message,
                indicator: 'green'
            });
            frm.save();
        }
    });
}

function _show_print_label_dialog(frm, doctype) {
    frappe.db.get_single_value('Label Printer Settings', 'default_label_size')
        .then(default_size => {
            const dialog = new frappe.ui.Dialog({
                title: __('Print Label'),
                fields: [
                    {
                        fieldtype: 'Select',
                        label: __('Label Size'),
                        fieldname: 'label_size',
                        options: '62mm continuous\n29mmx90mm',
                        default: default_size || '62mm continuous',
                        reqd: 1
                    },
                    {
                        fieldtype: 'Int',
                        label: __('Quantity'),
                        fieldname: 'label_qty',
                        default: 1,
                        reqd: 1,
                        non_negative: 1
                    }
                ],
                primary_action_label: __('Print'),
                primary_action(values) {
                    _print_label_via_browser(frm, doctype, values.label_size, values.label_qty);
                    dialog.hide();
                }
            });
            dialog.show();
        });
}

function _print_label_via_browser(frm, doctype, label_size, label_qty) {
    frappe.call({
        method: 'partscape.print_label.get_label_pdf',
        args: {
            doctype: doctype,
            name: frm.doc.name,
            label_size: label_size,
            label_qty: label_qty || 1
        },
        freeze: true,
        freeze_message: __('Preparing label PDF...'),
        callback(r) {
            if (r.exc || !r.message) return;

            const b64 = r.message.split(',')[1];
            const binary = atob(b64);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
                bytes[i] = binary.charCodeAt(i);
            }
            const blob = new Blob([bytes], { type: 'application/pdf' });
            const url = URL.createObjectURL(blob);
            window.open(url, '_blank');
        }
    });
}
