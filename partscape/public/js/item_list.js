/**
 * PartScape — Item List View Custom Search
 *
 * Adds a natural-language search field to the Item list view
 * that searches across Item fields (item_code, item_name, brand)
 * and linked Part Catalog fields (part_number, brand, part_name).
 */

frappe.listview_settings['Item'] = {
    onload: function(listview) {
        // Track whether a PartScape catalog filter is active
        listview.partscape_filter_active = false;

        // Add custom search field to the page toolbar (next to standard search)
        const searchField = listview.page.add_field({
            fieldtype: 'Data',
            label: __('PartScape Search'),
            fieldname: 'partscape_keyword',
            placeholder: __('e.g. suzuki, brake pad, BOSCH…'),
            width: '280px',
        });

        // Add search button
        listview.page.set_primary_action(__('Search Catalog'), function() {
            _doCatalogSearch(listview, searchField.get_value());
        }, 'search');

        // Trigger on Enter key
        searchField.$input.on('keypress', function(e) {
            if (e.which === 13) {
                _doCatalogSearch(listview, searchField.get_value());
            }
        });

        // Hook into list refresh so we can detect when standard filters change
        const originalRefresh = listview.refresh;
        listview.refresh = function() {
            // If user clears standard filters and we had a catalog filter active,
            // make sure we also clear our internal state
            if (listview.partscape_filter_active && !listview.partscape_preserve_filter) {
                // Check if part_catalog_reference filter was removed manually
                const hasCatalogFilter = listview.filter_area.filter_list.get_filters().some(
                    f => f[1] === 'part_catalog_reference' || f[1] === 'name'
                );
                if (!hasCatalogFilter) {
                    listview.partscape_filter_active = false;
                }
            }
            return originalRefresh.apply(this, arguments);
        };
    },
};

function _doCatalogSearch(listview, keyword) {
    keyword = (keyword || '').trim();

    // Clear any previous catalog filter first
    listview.partscape_preserve_filter = true;
    const clearPromise = listview.partscape_filter_active
        ? listview.filter_area.remove('part_catalog_reference').catch(() => {})
        : Promise.resolve();

    clearPromise.then(() => {
        listview.partscape_preserve_filter = false;

        if (!keyword) {
            listview.partscape_filter_active = false;
            listview.refresh();
            return;
        }

        frappe.dom.freeze(__('Searching…'));

        frappe.call({
            method: 'partscape.api.item_search.search_items_by_catalog',
            args: { keyword: keyword, limit: 500 },
            callback: function(r) {
                frappe.dom.unfreeze();
                const items = r.message || [];

                if (!items.length) {
                    frappe.show_alert({
                        message: __('No items found for "{0}"', [keyword]),
                        indicator: 'orange',
                    });
                    // Set impossible filter to show empty list
                    listview.filter_area.add('Item', 'name', '=', '__no_results__')
                        .then(() => {
                            listview.partscape_filter_active = true;
                            listview.refresh();
                        });
                    return;
                }

                // Apply filter: name IN [item_names]
                // Cap at 100 to keep URL length reasonable
                const filterNames = items.length > 100 ? items.slice(0, 100) : items;
                listview.filter_area.add('Item', 'name', 'in', filterNames)
                    .then(() => {
                        listview.partscape_filter_active = true;
                        listview.refresh();
                        frappe.show_alert({
                            message: __('Showing {0} items', [items.length]),
                            indicator: 'green',
                        });
                    });
            },
            error: function() {
                frappe.dom.unfreeze();
                frappe.msgprint(__('Search failed. Please try again.'));
            },
        });
    });
}
