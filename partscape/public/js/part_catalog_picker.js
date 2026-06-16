/**
 * PartScape — Part Catalog Picker Dialog
 *
 * Reusable dialog to search the 5.7M Part Catalog and select a part
 * for any transactional document (PO, PR, PI, SO, DN, SI, Stock Entry).
 */

frappe.provide('partscape');

function _escapeHtml(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

partscape.showPartCatalogPicker = function(opts) {
    opts = opts || {};
    const onSelect = opts.onSelect || function() {};
    const defaultVin = opts.defaultVin || '';

    let currentOffset = 0;
    const pageSize = 20;
    let currentResults = [];

    const dialog = new frappe.ui.Dialog({
        title: __('Select from Part Catalog'),
        size: 'extra-large',
        fields: [
            {
                fieldtype: 'Section Break',
                label: __('Search Filters'),
            },
            {
                fieldname: 'keyword',
                label: __('Keyword'),
                fieldtype: 'Data',
                description: __('Part number, name, or brand'),
            },
            {
                fieldname: 'brand',
                label: __('Brand'),
                fieldtype: 'Link',
                options: 'Brand',
            },
            {
                fieldname: 'category',
                label: __('Category'),
                fieldtype: 'Link',
                options: 'Item Group',
            },
            {
                fieldname: 'vehicle_vin',
                label: __('Vehicle VIN / Frame'),
                fieldtype: 'Data',
                default: defaultVin,
                description: __('Filter to parts applicable to this vehicle'),
            },
            {
                fieldtype: 'Column Break',
            },
            {
                fieldname: 'search_btn',
                label: __('Search'),
                fieldtype: 'Button',
                click: () => doSearch(0),
            },
            {
                fieldtype: 'Section Break',
                label: __('Results'),
            },
            {
                fieldname: 'results_html',
                fieldtype: 'HTML',
            },
        ],
        primary_action_label: __('Select'),
        primary_action: function() {
            const selected = dialog.selected_row;
            if (!selected) {
                frappe.msgprint(__('Please select a part from the results.'));
                return;
            }
            // Create/find Item from catalog selection
            frappe.call({
                method: 'partscape.api.part_catalog_search.create_item_from_catalog_dialog',
                args: { part_catalog_name: selected.part_catalog_name },
                callback: function(r) {
                    if (r.message && r.message.error) {
                        frappe.msgprint(r.message.error);
                        return;
                    }
                    dialog.hide();
                    onSelect(r.message);
                },
            });
        },
    });

    dialog.selected_row = null;

    function doSearch(offset) {
        currentOffset = offset || 0;
        const values = dialog.get_values();

        frappe.call({
            method: 'partscape.api.part_catalog_search.search_part_catalog_for_transaction',
            args: {
                keyword: values.keyword || '',
                brand: values.brand || '',
                category: values.category || '',
                vehicle_vin: values.vehicle_vin || '',
                limit: pageSize,
                offset: currentOffset,
            },
            callback: function(r) {
                if (r.message) {
                    renderResults(r.message);
                }
            },
        });
    }

    function renderResults(response) {
        currentResults = response.data || [];
        const total = response.total || 0;
        const limit = response.limit || pageSize;
        const offset = response.offset || 0;
        const hasMore = response.has_more || false;

        if (!currentResults.length) {
            dialog.fields_dict.results_html.$wrapper.html(
                `<div class="text-muted text-center" style="padding: 40px;">${__('No parts found.')}</div>`
            );
            return;
        }

        let html = `<div class="partscape-catalog-grid">`;
        html += `<style>
            .partscape-catalog-grid table {
                width: 100%; border-collapse: collapse; font-size: 12px;
            }
            .partscape-catalog-grid th {
                background: #f8f9fa; padding: 8px; text-align: left;
                border-bottom: 2px solid #dee2e6; font-weight: 600;
            }
            .partscape-catalog-grid td {
                padding: 8px; border-bottom: 1px solid #e9ecef;
                vertical-align: middle;
            }
            .partscape-catalog-grid tr:hover td {
                background: #f1f3f5; cursor: pointer;
            }
            .partscape-catalog-grid tr.selected td {
                background: #e7f3ff !important;
            }
            .partscape-catalog-grid .brand-badge {
                display: inline-block; background: #1abc9c; color: white;
                padding: 2px 8px; border-radius: 4px; font-size: 11px;
                font-weight: 600;
            }
            .partscape-catalog-grid .item-exists {
                color: #28a745; font-size: 11px;
            }
            .partscape-catalog-grid .item-missing {
                color: #dc3545; font-size: 11px;
            }
            .partscape-pagination {
                display: flex; justify-content: space-between;
                align-items: center; padding: 10px 0;
            }
        </style>`;

        html += `<table>
            <thead>
                <tr>
                    <th style="width: 30px;"></th>
                    <th>${__('Brand')}</th>
                    <th>${__('Part Number')}</th>
                    <th>${__('Name')}</th>
                    <th>${__('Category')}</th>
                    <th>${__('Est. Cost')}</th>
                    <th>${__('Item Status')}</th>
                </tr>
            </thead>
            <tbody>`;

        currentResults.forEach(function(row, idx) {
            const selectedClass = dialog.selected_row && dialog.selected_row.part_catalog_name === row.part_catalog_name ? 'selected' : '';
            const itemStatus = row.item_code
                ? `<span class="item-exists">${__('Item:')} ${row.item_code}</span>`
                : `<span class="item-missing">${__('No Item yet')}</span>`;

            html += `<tr class="catalog-row ${selectedClass}" data-idx="${idx}">
                <td><input type="radio" name="catalog_select" ${selectedClass ? 'checked' : ''}></td>
                <td><span class="brand-badge">${_escapeHtml(row.brand || '')}</span></td>
                <td><code>${_escapeHtml(row.part_number || '')}</code></td>
                <td>${_escapeHtml(row.part_name || '')}</td>
                <td>${_escapeHtml(row.category || '')}</td>
                <td>${row.estimated_cost_usd ? format_currency(row.estimated_cost_usd, 'USD') : '-'}</td>
                <td>${itemStatus}</td>
            </tr>`;
        });

        html += `</tbody></table>`;

        // Pagination
        const hasPrev = offset > 0;
        const totalDisplay = hasMore
            ? `${total}+`
            : String(total);
        html += `<div class="partscape-pagination">
            <span>${__('Showing')} ${offset + 1}–${Math.min(offset + limit, total)} ${__('of')} ${totalDisplay}</span>
            <div>
                <button class="btn btn-default btn-sm" ${hasPrev ? '' : 'disabled'} data-action="prev">${__('Previous')}</button>
                <button class="btn btn-default btn-sm" ${hasMore ? '' : 'disabled'} data-action="next">${__('Next')}</button>
            </div>
        </div>`;

        html += `</div>`;

        dialog.fields_dict.results_html.$wrapper.html(html);

        // Bind row click
        dialog.fields_dict.results_html.$wrapper.find('.catalog-row').on('click', function(e) {
            const idx = parseInt($(this).data('idx'));
            dialog.selected_row = currentResults[idx];
            dialog.fields_dict.results_html.$wrapper.find('.catalog-row').removeClass('selected');
            dialog.fields_dict.results_html.$wrapper.find('.catalog-row').find('input[type="radio"]').prop('checked', false);
            $(this).addClass('selected');
            $(this).find('input[type="radio"]').prop('checked', true);
        });

        // Bind pagination
        dialog.fields_dict.results_html.$wrapper.find('[data-action="prev"]').on('click', function() {
            if (!$(this).prop('disabled')) doSearch(offset - limit);
        });
        dialog.fields_dict.results_html.$wrapper.find('[data-action="next"]').on('click', function() {
            if (!$(this).prop('disabled')) doSearch(offset + limit);
        });
    }

    // Auto-search on Enter key in keyword field
    dialog.fields_dict.keyword.$input.on('keypress', function(e) {
        if (e.which === 13) doSearch(0);
    });

    dialog.show();
    // Don't auto-search on open — wait for user to type + click Search
    // to avoid hammering the 5.7M table on every dialog open.
};
