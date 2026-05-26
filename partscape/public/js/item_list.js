/**
 * PartScape — Item List View Custom Search
 *
 * Injects a native-looking filter field into the Item list view filter bar.
 * Searches across Item fields (item_code, item_name, brand) and linked
 * Part Catalog fields (part_number, brand, part_name).
 */

frappe.listview_settings['Item'] = {
    onload: function(listview) {
        // Wait for the standard filter fields to render
        setTimeout(() => _injectPartScapeFilter(listview), 400);
    },
};

function _injectPartScapeFilter(listview) {
    const $pageForm = listview.page.page_form;
    if (!$pageForm.length || $pageForm.find('.partscape-filter-wrap').length) return;

    // Build a wrapper that matches native page-field markup exactly:
    // .frappe-control .col-md-2  (no .form-group, no .input-group)
    const $wrap = $(`
        <div class="partscape-filter-wrap form-group frappe-control col-md-2"
             title="${__('PartScape Search')}" data-original-title="${__('PartScape Search')}">
            <input type="text"
                autocomplete="off"
                class="partscape-search-input input-with-feedback form-control input-xs"
                maxlength="140"
                placeholder="${__('PartScape Search…')}">
            <span class="tooltip-content">PartScape</span>
        </div>
    `);

    // Place it at the front of the default list filters
    const $firstFilter = $pageForm.children('.frappe-control.col-md-2').first();
    if ($firstFilter.length) {
        $firstFilter.before($wrap);
    } else {
        $pageForm.prepend($wrap);
    }

    const $input = $wrap.find('.partscape-search-input');

    // Search on Enter
    $input.on('keypress', function(e) {
        if (e.which === 13) {
            _doCatalogSearch(listview, $input.val());
        }
    });
}

function _doCatalogSearch(listview, keyword) {
    keyword = (keyword || '').trim();

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
