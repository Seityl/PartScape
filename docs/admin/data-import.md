# Importing Data

PartScape can be populated from several data sources. This page covers the available importers and what they load.

## Import sources

| Source | Files | What is loaded |
|---|---|---|
| **TecDoc 1Q2019** | `articles.csv`, `article_oe_numbers.csv`, etc. | Part Catalogue, Part Supplier References (OEM numbers). |
| **TecDoc sample GitHub** | `articles_linkages.csv`, `article_new_numbers.csv`, `article_replace_numbers.csv`, `article_cross_list.csv` | Vehicle Part Applicability, Part Interchange. |
| **FPI Auto Parts PDFs** | PDF catalogues | Part Catalogue, Part Supplier References, limited Vehicle Part Applicability. |
| **Generic bulk CSV** | Any CSV matching the template | Part Catalogue, Vehicle Part Applicability, Part Interchange. |

## TecDoc bulk import

The main TecDoc importer loads articles and OEM reference numbers.

### Requirements

- TecDoc 1Q2019 CSV files placed in `/tmp/tecdoc1q2019`:
  - `articles.csv`
  - `suppliers.csv`
  - `products.csv`
  - `article_oe_numbers.csv`

### Run

```bash
bench --site yoursite.local execute partscape.patches.v1_0_0_import_tecdoc_bulk.execute
```

This creates Part Catalogue entries and Part Supplier Reference records for OEM numbers.

## TecDoc associations import (sample data)

The association importer downloads freely available sample slices from GitHub and loads fitment and interchange data.

### Run

```bash
bench --site yoursite.local execute partscape.data_import.import_tecdoc_associations.execute
```

### What it does

1. Downloads reference files to `/tmp/tecdoc_associations`.
2. Streams `articles.csv` parts to map TecDoc article IDs to part numbers.
3. Creates **Vehicle Part Applicability** rows from `articles_linkages.csv`.
4. Creates **Part Interchange** rows from new/replace/cross-reference files.

### Important note

The GitHub repositories contain sample-sized files, not the full TecDoc DVD. The importer will populate a subset of associations. For full coverage, you need the complete TecDoc linkage and interchange dump.

## Generic CSV import

For your own data, use the generic CSV importer.

### CSV columns

```csv
brand,part_number,part_name,category,description,weight_kg,dimensions,estimated_cost_usd,vehicle_model,year_start,year_end,engine_code,steering_position,market_code,interchange_brand,interchange_part_number,relationship_type,quality_tier
```

- `brand` — must match an existing **Brand** doc (or one will be created).
- `category` — must match an existing **Item Group** (or one will be created under `Auto Parts`).
- `market_code` — must match an existing **Market** doc (or one will be created).

### Run

```bash
bench --site yoursite.local execute partscape.data_import.import_part_catalog.import_from_csv --args '["/path/to/file.csv", "Toyota"]'
```

The second argument is the default vehicle make when the CSV does not specify one.

## Vehicle master data

Vehicle makes, models, and engine variants are seeded by patches during migrate. Additional sources can be imported using the dedicated vehicle import patches if needed.

## Verifying imports

After any import, check the counts:

```bash
bench --site yoursite.local mariadb -e "SET SQL_BIG_SELECTS=1;
SELECT 'Part Catalogue' as t, COUNT(*) FROM \`tabPart Catalog\`
UNION ALL SELECT 'Supplier Refs', COUNT(*) FROM \`tabPart Supplier Reference\`
UNION ALL SELECT 'Applicability', COUNT(*) FROM \`tabVehicle Part Applicability\`
UNION ALL SELECT 'Interchange', COUNT(*) FROM \`tabPart Interchange\`;"
```
