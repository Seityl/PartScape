/**
 * PartScape — Item Price Client Script
 *
 * Allows entering a VAT-inclusive price and defaults the VAT rate from
 * PartScape Settings.
 */

frappe.ui.form.on('Item Price', {
    refresh(frm) {
        _set_vat_rate_default(frm);
    },

    partscape_price_includes_vat(frm) {
        _set_vat_rate_default(frm);
        if (frm.doc.partscape_price_includes_vat) {
            _recalculate_net_price(frm);
        }
    },

    partscape_price_with_vat(frm) {
        if (frm.doc.partscape_price_includes_vat) {
            _recalculate_net_price(frm);
        }
    },

    partscape_vat_rate(frm) {
        if (frm.doc.partscape_price_includes_vat) {
            _recalculate_net_price(frm);
        }
    }
});

function _set_vat_rate_default(frm) {
    if (!frm.doc.partscape_price_includes_vat) return;
    if (frm.doc.partscape_vat_rate) return;

    frappe.db.get_single_value('PartScape Settings', 'default_vat_rate')
        .then(rate => {
            if (rate !== null && rate !== undefined) {
                frm.set_value('partscape_vat_rate', rate);
            }
        });
}

function _recalculate_net_price(frm) {
    const price_with_vat = flt(frm.doc.partscape_price_with_vat);
    const vat_rate = flt(frm.doc.partscape_vat_rate);

    if (!price_with_vat) return;
    if (vat_rate <= -100) return;

    const net_price = price_with_vat / (1 + (vat_rate / 100));
    frm.set_value('price_list_rate', net_price);
}
