# Part Interchange (Cross References)

**Part Interchange** records relationships between parts that can replace each other. This includes equivalents, supersessions, and replacement numbers.

## Relationship types

PartScape uses the following relationship types:

| Type | Meaning |
|---|---|
| **Equivalent** | The two parts are interchangeable (cross-reference). |
| **New Number** | The manufacturer has issued a new part number that replaces the old one. |
| **Replacement** | A direct replacement part, often aftermarket for OEM or vice versa. |

## Where interchange data is used

- When you look up a part, PartScape can show alternatives.
- If a requested part is out of stock, staff can quickly find an equivalent.
- Purchasing can compare OEM and aftermarket options.

## Viewing interchange records

1. Go to **Part Interchange** from the desk.
2. The list shows pairs of parts and their relationship.
3. You can filter by relationship type or source.

## Adding interchange manually

Users with the **Purchase Manager** role can create interchange records:

1. Go to **Part Interchange** → **New**.
2. Select **Part A** and **Part B** from the Part Catalogue.
3. Choose the **Relationship Type**.
4. Set the **Quality Tier** (for example, `OEM`, `OEM Equivalent`, `Aftermarket`).
5. Save.

PartScape prevents duplicate or reverse-duplicate pairs automatically.

## Bulk loading interchange data

Interchange relationships can be loaded from TecDoc files:

- `article_new_numbers.csv` → New Number
- `article_replace_numbers.csv` → Replacement
- `article_cross_list.csv` → Equivalent

The importer matches part numbers to Part Catalogue entries and creates the relationships.

See [Importing Data](../admin/data-import.md) for details.

## Important note

Interchange data is directional in TecDoc but stored as undirected pairs in PartScape. The relationship type describes the nature of the link, not a one-way replacement order.
