/**
 * PartScape — Item List View Custom Search
 *
 * Adds a natural-language search field to the Item list view filter bar
 * that searches across Item fields (item_code, item_name, brand)
 * and linked Part Catalog fields (part_number, brand, part_name).
 */

frappe.listview_settings['Item'] = {
    onload: function(listview) {
        // Wait for the page form / filter row to render
        setTimeout(() => _injectPartScapeFilter(listview), 300);
    },
};

function _injectPartScapeFilter(listview) {
    const $pageForm = listview.page.page_form;
    if (!$pageForm.length) return;

    // Avoid double-injection
    if ($pageForm.find('.partscape-filter-wrap').length) return;

    // Build a visually matching filter input (no data-fieldname so Frappe ignores it)
    const $wrap = $(`
        <div class="partscape-filter-wrap form-group input-max-width col-md-2"
             title="${__('Search by part #, brand, name…')}">
            <div class="input-group">
                <input type="text"
                    autocomplete="off"
                    class="partscape-search-input input-with-feedback form-control input-xs"
                    maxlength="140"
                    placeholder="${__('PartScape Search…')}">
            </div>
            <span class="tooltip-content">PartScape</span>
        </div>
    `);

    // Insert as the first child of the filter row so it sits before ID, Item Name, etc.
    const $filterRow = $pageForm.find('.filter-section').first();
    if ($filterRow.length) {
        $filterRow.prepend($wrap);
    } else {
        // Fallback: insert at start of page form
        $pageForm.prepend($wrap);
    }

    const $input = $wrap.find('.partscape-search-input');

    // Search button
    listview.page.set_primary_action(__('Search Catalog'), function() {
        _doCatalogSearch(listview, $input.val());
    }, 'search');

    // Enter key
    $input.on('keypress', function(e) {
        if (e.which === 13) {
            _doCatalogSearch(listview, $input.val());
        }
    });
}

function _doCatalogSearch(listview, keyword) {
    keyword = (keyword || '').trim();

    // Remove any previous "no results" dummy filter
    const hasNoResults = listview.filter_area.filter_list.get_filters().some(
        f => f[1] === 'name' && f[3] === '__no_results__'
    );

    const clearPromise = hasNoResults
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
                    listview.filter_area.add('Item', 'name', '=', '__no_results__')
                        .then(() => listview.refresh());
                    return;
                }

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
