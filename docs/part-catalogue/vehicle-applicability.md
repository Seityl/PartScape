# Vehicle Applicability (Fitment)

**Vehicle Part Applicability** links a Part Catalogue entry to the vehicles it fits. This is often called "fitment" or "application" data.

## What it tells you

A Vehicle Part Applicability record says:

> This part fits this vehicle model, in these years, with this engine variant.

For example:

- Part: `BOSCH 0 986 494 046` (brake pads)
- Vehicle Model: `Toyota Hilux`
- Year Start: `2012`
- Year End: `2020`
- Variant: `3.0 D`

## Where it is used

- **VIN search** — when you enter a VIN in the Part Catalog Picker, PartScape decodes the vehicle and filters to parts with matching applicability records.
- **Catalogue lookup** — users can open a part and see which vehicles it fits.
- **Cross-selling / recommendations** — knowing fitment helps suggest related parts.

## Viewing applicability

1. Open a **Part Catalogue** entry.
2. Scroll to the **Applicable Vehicles** section.
3. Each row shows a vehicle model, year range, and optional engine variant.

## Adding applicability manually

Users with the **Purchase Manager** role can add rows directly in the Part Catalogue form:

1. Open the Part Catalogue entry.
2. In **Applicable Vehicles**, click **Add Row**.
3. Select the **Vehicle Model**.
4. Enter **Year Start** and **Year End**.
5. Optionally select or enter an **Engine Variant**.
6. Save.

## Bulk loading applicability

Fitment data can be loaded in bulk from TecDoc. The importer reads `articles_linkages.csv` and creates applicability records by matching part numbers and vehicle descriptions.

See [Importing Data](../admin/data-import.md) for details.

## Notes

- Fitment records are child rows of a Part Catalogue entry.
- A part can have many applicability records (one per model/year/variant combination).
- If no applicability data is loaded, VIN filtering will not return any results.
