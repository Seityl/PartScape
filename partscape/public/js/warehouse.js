/**
 * PartScape — Warehouse Client Script
 *
 * Adds Brother QL-800 browser label printing to the Warehouse form.
 */

frappe.ui.form.on('Warehouse', {
    refresh(frm) {
        if (frm.is_new()) return;

        frm.add_custom_button(__('Print Label'), () => {
            _show_print_label_dialog(frm, 'Warehouse');
        });
    }
});

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
                    }
                ],
                primary_action_label: __('Print'),
                primary_action(values) {
                    _print_label_via_browser(frm, doctype, values.label_size);
                    dialog.hide();
                }
            });
            dialog.show();
        });
}

function _print_label_via_browser(frm, doctype, label_size) {
    frappe.call({
        method: 'partscape.print_label.get_label_pdf',
        args: {
            doctype: doctype,
            name: frm.doc.name,
            label_size: label_size
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
