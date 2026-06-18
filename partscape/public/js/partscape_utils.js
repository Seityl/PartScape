/**
 * PartScape — Shared client-side utilities
 *
 * Thin wrappers around standard Frappe loading UX so every custom script
 * behaves consistently without re-inventing spinners / freeze overlays.
 */

frappe.provide('partscape');

/**
 * Call a whitelisted Frappe method with a standard freeze overlay + spinner.
 *
 * @param {string} method           Dotted path to the whitelisted method.
 * @param {object} args             Arguments object.
 * @param {string} freeze_message   Message shown under the spinner.
 * @param {function} on_success     Optional callback receiving r.message.
 * @returns {Promise}               Resolves with r.message or rejects on error.
 */
partscape.call_with_freeze = function(method, args, freeze_message, on_success) {
    return new Promise((resolve, reject) => {
        frappe.call({
            method: method,
            args: args || {},
            freeze: true,
            freeze_message: freeze_message || __('Loading...'),
            callback(r) {
                if (r.exc) {
                    reject(r.exc);
                    return;
                }
                resolve(r.message);
                if (on_success) on_success(r.message);
            },
            error(err) {
                reject(err);
                frappe.show_alert({
                    message: __('Request failed. Please try again.'),
                    indicator: 'red',
                });
            },
        });
    });
};

/**
 * Toggle a button between its normal text and a spinner-disabled state.
 *
 * @param {jQuery} $btn        The button element.
 * @param {boolean} loading    True to show spinner, false to restore text.
 * @param {string} label       Optional label while loading (defaults to "Loading...").
 */
partscape.set_button_loading = function($btn, loading, label) {
    if (!$btn || !$btn.length) return;

    if (loading) {
        if (!$btn.data('original-text')) {
            $btn.data('original-text', $btn.text());
        }
        $btn.prop('disabled', true).html(
            `<i class="fa fa-circle-notch fa-spin"></i> ${__(label || 'Loading...')}`
        );
    } else {
        $btn.prop('disabled', false).text($btn.data('original-text') || '');
        $btn.removeData('original-text');
    }
};

/**
 * Build a skeleton placeholder table body using Frappe's standard .skeleton class.
 *
 * @param {number} columns   Number of columns.
 * @param {number} rows      Number of skeleton rows.
 * @returns {string}         HTML <tbody> string.
 */
partscape.skeleton_table_rows = function(columns, rows) {
    columns = columns || 1;
    rows = rows || 3;
    let html = '<tbody>';
    for (let i = 0; i < rows; i++) {
        html += '<tr>';
        for (let j = 0; j < columns; j++) {
            html += '<td><div class="skeleton" style="width: 90%; height: 14px;"></div></td>';
        }
        html += '</tr>';
    }
    html += '</tbody>';
    return html;
};

/**
 * Build a simple centred spinner message for an HTML wrapper.
 *
 * @param {string} message   Optional message (defaults to "Loading...").
 * @returns {string}         HTML string.
 */
partscape.spinner_html = function(message) {
    return `<div class="text-muted text-center" style="padding: 40px;">
        <i class="fa fa-circle-notch fa-spin" style="margin-right: 8px;"></i>
        ${__(message || 'Loading...')}
    </div>`;
};

/**
 * Apply common Part Catalog details to a transactional child row.
 *
 * @param {string} cdt         Child DocType (e.g. "Sales Order Item").
 * @param {string} cdn         Child document name.
 * @param {object} details     Result from get_part_catalog_line_details.
 */
partscape.apply_part_catalog_details = function(cdt, cdn, details) {
    if (!details) return;

    const row = locals[cdt][cdn];

    if (details.part_name) {
        frappe.model.set_value(cdt, cdn, 'item_name', details.part_name);
        frappe.model.set_value(
            cdt, cdn, 'description',
            `${details.part_name} — ${details.brand || ''} ${details.part_number || ''}`.trim()
        );
    }

    if (details.item_code && !row.item_code) {
        frappe.model.set_value(cdt, cdn, 'item_code', details.item_code);
    }

    if (details.interchange_numbers) {
        frappe.model.set_value(
            cdt, cdn, 'alternative_part_numbers',
            details.interchange_numbers.join(', ')
        );
    }
};

/**
 * Apply common Vehicle details to a transactional child row.
 *
 * @param {string} cdt         Child DocType.
 * @param {string} cdn         Child document name.
 * @param {object} details     Result from get_vehicle_line_details.
 */
partscape.apply_vehicle_details = function(cdt, cdn, details) {
    if (!details) return;

    frappe.model.set_value(cdt, cdn, 'vin', details.vin || '');
    frappe.model.set_value(
        cdt, cdn, 'applicable_models',
        `${details.year || ''} ${details.make || ''} ${details.model || ''}`.trim()
    );
};
