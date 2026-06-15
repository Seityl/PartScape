# PartScape Settings

PartScape Settings is the single place where administrators configure defaults used when creating ERPNext Items from the Part Catalogue.

## Opening PartScape Settings

1. From the ERPNext desk, use the search bar and type **PartScape Settings**.
2. Open the document. There is only one record; create it if it does not exist.

## Fields

| Field | What it does |
|---|---|
| **Default Warehouse** | The warehouse assigned to new Items when they are created from the Part Catalogue. |
| **Default UOM** | Unit of measure for new Items (usually `Nos`). |
| **Default Item Group** | Item Group used when a Part Category does not have its own Item Group mapping. |
| **Default Root Item Group** | Fallback Item Group if the default item group is also missing. |
| **Default Income Account** | Income account for Item Defaults. |
| **Default Expense Account** | Expense account for Item Defaults. |
| **Default Buying Cost Center** | Cost center used for purchases. |
| **Default Selling Cost Center** | Cost center used for sales. |

## Why these defaults matter

When a user selects a part from the catalogue in a transaction, PartScape creates an ERPNext **Item** automatically. The Item needs basic accounting and stock defaults so it can be used in Purchase Orders, Sales Orders, Stock Entries, and invoices. The values above are used to populate those defaults.

## Recommended setup

1. Create the Item Groups you want for your parts (for example, `Auto Parts`, `Brakes`, `Filters`).
2. Map each **Part Category** to an Item Group on the Part Category form.
3. Fill in the accounts and cost centers in PartScape Settings.
4. Choose your default warehouse.

If a Part Category has its own Item Group, PartScape uses that. Otherwise it falls back to the settings here.

## Label Printer Settings

Label printing has its own settings document:

1. Search for **Label Printer Settings**.
2. Choose the **Default Label Size**:
   - `62mm continuous` for DK-22205 rolls.
   - `29mmx90mm` for DK-11201 die-cut labels.
3. Save.

The printer itself is not configured here. Each user selects their local Brother QL-800 in the browser/OS print dialog.
