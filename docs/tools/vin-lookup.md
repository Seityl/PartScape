# VIN Lookup

The **VIN Lookup** tool decodes a Vehicle Identification Number (VIN) or frame number and shows vehicle details. This helps identify the correct parts for a vehicle.

## Opening VIN Lookup

From the ERPNext desk, search for **VIN Lookup**.

## How to use it

1. Enter the VIN or frame number.
2. Click **Decode**.
3. The tool returns:
   - Make
   - Model
   - Year
   - Engine details (when available)

## VIN in the Part Catalog Picker

You can also enter a VIN directly in the **PartScape → Select from Part Catalog** dialog. PartScape decodes the VIN and filters the catalogue to parts that are applicable to that vehicle.

> VIN filtering requires Vehicle Part Applicability data to be loaded. If no fitment data exists, the filter will return no results.

## Supported VIN sources

PartScape uses multiple sources to decode VINs:

- **NHTSA vPIC** for North American vehicles.
- **VIN Decoder EU** for European vehicles.
- A built-in fallback for common JDM frame prefixes.

Decoded results are cached so repeated lookups are fast.

## Notes

- Some Japanese and grey-import vehicles use frame numbers instead of standard 17-character VINs. The fallback handles common prefixes.
- If a VIN cannot be decoded, the picker will not filter by vehicle and you can search by keyword or part number instead.
