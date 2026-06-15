# PartScape Wiki

Welcome to the PartScape documentation. PartScape is a Frappe/ERPNext app built for automotive parts businesses. It adds a dedicated **Part Catalogue** on top of ERPNext so you can manage, search, and transact millions of parts without treating every part as a stock item until you actually need it.

## What PartScape does

- Stores a universal **Part Catalogue** independent of ERPNext Items.
- Links parts to **vehicles** (make, model, year range, engine variant).
- Tracks **alternative / interchangeable / superseded** part numbers.
- Lets you create ERPNext **Items** from catalogue entries on demand.
- Adds a **Part Catalog Picker** to Purchase Orders, Sales Orders, Stock Entries, and other transactions.
- Provides native **thermal label printing** for Brother QL-800 printers.
- Includes a **VIN lookup** tool to find parts by vehicle identification number.

## Who this documentation is for

These pages are written for day-to-day users — parts clerks, purchasers, warehouse staff, and administrators — not just developers. If you need technical/developer notes, see the source code comments and `LABEL_PRINTING.md` in the app root.

## Quick navigation

### Getting started
- [Installation & Setup](getting-started/installation.md)
- [Roles & Permissions](getting-started/roles-and-permissions.md)
- [PartScape Settings](getting-started/settings.md)

### Part Catalogue
- [Part Catalogue Overview](part-catalogue/overview.md)
- [Searching for Parts](part-catalogue/searching-parts.md)
- [Creating ERPNext Items from the Catalogue](part-catalogue/creating-items.md)
- [Vehicle Applicability (Fitment)](part-catalogue/vehicle-applicability.md)
- [Part Interchange (Cross References)](part-catalogue/interchange.md)

### Using Parts in Transactions
- [Purchase Orders](transactions/purchase-orders.md)
- [Other Transactions](transactions/other-documents.md)

### Tools
- [Label Printing](tools/label-printing.md)
- [VIN Lookup](tools/vin-lookup.md)

### Administration
- [Importing Data](admin/data-import.md)
- [Troubleshooting](admin/troubleshooting.md)

## One-minute overview

1. A supplier sends you a parts list or you look up a part by number.
2. You search the **Part Catalogue** and find the part.
3. PartScape creates an ERPNext **Item** automatically if one does not exist.
4. The Item is linked back to the catalogue entry so you always know which real-world part it represents.
5. You can print a barcode label, add the part to a Purchase Order, or check which vehicles it fits.

---

If something is missing or unclear, ask your system administrator to update this wiki or raise an issue in the PartScape repository.
