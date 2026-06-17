# Purchase Orders

PartScape adds a **Select from Part Catalog** button to Purchase Orders, making it easy to add parts without manually creating ERPNext Items first.

## Adding a part from the catalogue

1. Open a new or existing **Purchase Order**.
2. In the menu bar, click **PartScape**.
3. Click **Select from Part Catalog**.
4. Search by keyword, brand, category, or VIN.
5. Click a row to select it, then click **Select**.

If an ERPNext Item already exists for that catalogue entry, it is used. If not, PartScape creates it automatically.

## What fills in on the row

After selection, the Purchase Order item row is populated with:

- **Item Code** — the ERPNext Item.
- **Item Name** — from the catalogue.
- **Description** — combined part name, brand, and part number.
- **Part Catalogue Reference** — link to the catalogue entry.

## Editing a row manually

You can also type or select a **Part Catalogue Reference** directly in a Purchase Order item row. When the reference is set, PartScape:

1. Looks up the linked ERPNext Item.
2. Fills the item name and description.
3. Fetches alternative part numbers from interchange data.
4. Estimates the landed cost in XCD if cost data is available.

## After adding parts

The rest of the Purchase Order works like a normal ERPNext document:

- Set quantities.
- Set supplier.
- Set required-by date.
- Submit.

## Notes

- The Part Catalog Picker only creates Items when needed, so your Item master stays clean.
- If a part has Vehicle Part Applicability records, you can filter by VIN to find the right part faster.
