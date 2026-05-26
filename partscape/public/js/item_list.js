/**
 * PartScape — Item List View Custom Search
 *
 * Adds a natural-language search field to the Item list view
 * that searches across Item fields (item_code, item_name, brand)
 * and linked Part Catalog fields (part_number, brand, part_name).
 */

frappe.listview_settings['Item'] = {
    onload: function(listview) {
        // Add custom search input manually (outside Frappe's filter system)
        // so it doesn't get sent as a query filter to the server.
        const $input = $(`
            <div class="partscape-list-search" style="display:inline-block;margin-right:12px;">
                <input type="text"
                    class="form-control input-sm"
                    placeholder="${__('PartScape Search…')}"
                    style="width:260px;display:inline-block;"
                    title="${__('Search by part #, brand, name…')}">
            </div>
        `);

        // Insert before the standard list-view filters
        listview.page.page_form.find('.filter-section').before($input);

        const $field = $input.find('input');

        // Search button
        listview.page.set_primary_action(__('Search Catalog'), function() {
            _doCatalogSearch(listview, $field.val());
        }, 'search');

        // Enter key
        $field.on('keypress', function(e) {
            if (e.which === 13) {
                _doCatalogSearch(listview, $field.val());
            }
        });
    },
};

function _doCatalogSearch(listview, keyword) {
    keyword = (keyword || '').trim();

    // Clear any previous impossible filter
    const removeImpossible = listview.filter_area.filter_list.get_filters().some(
        f => f[1] === 'name' && f[3] === '__no_results__'
    );

    const clearPromise = removeImpossible
        ? listview.filter_area.remove('name').catch(() => {})
        : Promise.resolve();

    clearPromise.then(() => {
        if (!keyword) {
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
                        .then(() => listview.refresh());
                    return;
                }

                // Apply filter: name IN [item_names]
                const filterNames = items.length > 100 ? items.slice(0, 100) : items;
                listview.filter_area.add('Item', 'name', 'in', filterNames)
                    .then(() => {
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
