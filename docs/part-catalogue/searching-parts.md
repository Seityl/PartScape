# Searching for Parts

PartScape provides a fast search over the Part Catalogue. You can search from the catalogue list view or from inside transactions.

## Searching from the Part Catalogue list

1. Go to **Part Catalogue** from the desk.
2. Use the search box at the top of the list.
3. Type a part number, brand, or part name.

The search uses a relevance-ranked strategy:

- Exact part number matches appear first.
- Exact brand matches appear next.
- Prefix matches on brand or part number follow.
- Matches on part name appear last.

If a prefix search finds nothing, PartScape falls back to a full-text search inside words.

## Searching from a transaction

Most transactional documents have a **PartScape** menu with a **Select from Part Catalog** button:

- Purchase Order
- Purchase Receipt
- Purchase Invoice
- Sales Order
- Delivery Note
- Sales Invoice
- Stock Entry

### Steps

1. Open the transaction (for example, a new Purchase Order).
2. Click **PartScape** in the menu bar.
3. Click **Select from Part Catalog**.
4. Enter a keyword, brand, or category in the dialog.
5. Click **Search**.
6. Select a row and click **Select**.

The dialog shows:

- Brand
- Part Number
- Part Name
- Category
- Estimated Cost
- Item Status (whether an ERPNext Item already exists)

## Filtering by VIN

If you know the vehicle a part must fit, enter the **VIN / Frame** number in the picker dialog. PartScape decodes the VIN and only shows parts that are applicable to that vehicle.

> VIN filtering only works if Vehicle Part Applicability data has been loaded. See [Vehicle Applicability](vehicle-applicability.md).

## Search tips

- Part numbers can be entered with or without dashes and spaces. Try the full number first.
- If you know the brand, use the **Brand** filter to narrow results quickly.
- Use the **Category** filter to browse a category.
- Partial brand names work; for example, typing `BOS` will match `BOSCH`.
