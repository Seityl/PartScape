# Part Catalogue Overview

The **Part Catalogue** is the heart of PartScape. It is a central register of every part your business might ever sell, buy, or stock — independent of ERPNext Items.

## Why a separate catalogue?

ERPNext Items are stock-keeping records. Creating an Item for every part you might ever touch can be overwhelming, especially when you have millions of possible parts.

PartScape solves this by:

1. Keeping a lightweight **Part Catalogue** with part numbers, brands, descriptions, categories, and vehicle fitment.
2. Creating an ERPNext **Item** only when you actually need it (for example, when adding it to a Purchase Order).
3. Linking the Item back to the catalogue entry so you always know the real-world part it represents.

## What is in a Part Catalogue entry?

| Field | Description |
|---|---|
| **Brand** | The brand or manufacturer of the part (for example, `BOSCH`, `TOYOTA`). |
| **Part Number** | The manufacturer's or supplier's part number. |
| **Part Name** | A short description of the part. |
| **Category** | The Part Category the part belongs to (for example, `Brake Pads`). |
| **Vehicle Make** | If the part is OEM, the vehicle manufacturer. |
| **Is OEM** | Checked when the brand matches the vehicle manufacturer. |
| **Description** | Longer description or notes. |
| **Estimated Cost (USD)** | Reference cost for purchase planning. |
| **Superseded By** | If this part is replaced by another catalogue entry. |
| **Applicable Vehicles** | Child table of Vehicle Part Applicability records. |
| **Diagrams** | Linked Part Diagrams, if any. |

## How a catalogue entry becomes an Item

1. A user searches the catalogue.
2. They select a part.
3. PartScape checks whether an ERPNext Item already exists for that catalogue entry.
4. If not, it creates the Item with defaults from PartScape Settings.
5. The new Item is returned to the transaction or form.

## Catalogue vs Item

| | Part Catalogue | ERPNext Item |
|---|---|---|
| Purpose | Universal reference | Stock/accounting record |
| Quantity | Millions possible | Only created when needed |
| Stock control | No | Yes |
| Used in transactions | Indirectly (via Item) | Directly |
| Barcode label | No | Yes |

## Managing the catalogue

Users with the **Purchase Manager** role can create and edit catalogue entries manually. **Parts Clerk** users can view entries but not edit them.

For bulk imports from TecDoc or FPI, see [Importing Data](../admin/data-import.md).
