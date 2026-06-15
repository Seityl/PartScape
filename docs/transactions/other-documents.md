# Using PartScape in Other Transactions

The Part Catalog Picker is available in several ERPNext transactional documents:

- Purchase Order
- Purchase Receipt
- Purchase Invoice
- Sales Order
- Delivery Note
- Sales Invoice
- Stock Entry

The workflow is the same in each document.

## General steps

1. Open the transaction.
2. Click **PartScape** in the menu bar.
3. Click **Select from Part Catalog**.
4. Search and select the part.
5. The Item row is created or updated automatically.

## Differences by document

| Document | Typical use |
|---|---|
| **Purchase Receipt** | Receive parts you ordered. |
| **Purchase Invoice** | Bill parts from a supplier. |
| **Sales Order** | Sell a part to a customer. |
| **Delivery Note** | Ship parts to a customer. |
| **Sales Invoice** | Invoice a customer for parts. |
| **Stock Entry** | Move parts between warehouses or adjust stock. |

## Item creation

In every document, if the selected catalogue entry does not yet have an ERPNext Item, PartScape creates one on the fly using the defaults in PartScape Settings.

## Line-level reference

Each transaction item row stores the **Part Catalogue Reference**. This makes it easy to trace a transaction line back to the original catalogue entry and its vehicle fitment or interchange data.

## For administrators

The picker button is added by client scripts registered in `hooks.py`. If you need to add it to another DocType, a developer can copy the pattern from `public/js/purchase_order.js`.
