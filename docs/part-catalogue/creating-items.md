# Creating ERPNext Items from the Catalogue

PartScape creates ERPNext **Items** from catalogue entries on demand. This keeps your Item master clean while still letting you transact any part.

## When an Item is created

An Item is created automatically when:

- You select a part from the catalogue picker in a transaction, or
- You open a catalogue entry and choose to create an Item manually.

If the Item already exists, PartScape reuses it.

## Item code generation

PartScape generates Item codes in this format:

```
AD-{BRAND_ABBREVIATION}-{SANITIZED_PART_NUMBER}
```

For example:

| Brand | Part Number | Item Code |
|---|---|---|
| TOYOTA | 52150-0P030 | `AD-TOYO-521500P030` |
| BOSCH | 0 986 494 046 | `AD-BOSC-0986494046` |

## What is copied to the Item?

When an Item is created from the catalogue, PartScape sets:

- **Item Code** — generated as above.
- **Item Name** — from the catalogue part name.
- **Item Group** — from the catalogue category (Item Group) or PartScape Settings fallback.
- **Stock UOM** — from PartScape Settings.
- **Is Stock Item** — Yes.
- **Is Purchase Item** — Yes.
- **Is Sales Item** — Yes.
- **Valuation Method** — FIFO.
- **Item Defaults** — warehouse, income account, expense account, cost centers from PartScape Settings.
- **Part Catalogue Reference** — link back to the catalogue entry.
- **Brand** and **Part Number** — copied from the catalogue.
- **Supplier Items** — copied from Part Supplier Reference records.

## Manual Item creation

1. Open a **Part Catalogue** entry.
2. If you have a custom button or workflow to create an Item, use it.
3. Otherwise, the Item is created automatically the first time the part is used in a transaction.

## Checking whether an Item exists

In the catalogue picker, the **Item Status** column shows:

- `Item: AD-XXX-...` — an Item already exists.
- `No Item yet` — selecting this row will create one.

## After the Item is created

Once created, the Item behaves like any other ERPNext Item. You can:

- Add it to Purchase Orders, Sales Orders, Stock Entries, invoices.
- Print barcode labels for it.
- Set reorder levels and valuations.
- View it in stock reports.

The link back to the Part Catalogue entry is stored in the Item's **Part Catalogue Reference** field, so you can always navigate back to the original catalogue data.
