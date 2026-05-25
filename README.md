# PartScape

Auto-parts intelligence system for fleet and workshop management, integrated natively into ERPNext.

## Quick Start

```bash
# From bench directory
bench get-app https://github.com/seityl/partscape.git
bench --site erp.autodepot.local install-app partscape
bench --site erp.autodepot.local migrate
```

## Features

- **VIN Decode Cache** — NHTSA vPIC + JDM frame number lookups
- **Part Catalog** — OEM part numbers with diagram references
- **Part Interchange** — Aftermarket cross-references (Bosch, Denso, KYB, etc.)
- **Vehicle Master** — Full fleet tracking with RHD/LHD awareness
- **Workshop Job Cards** — Parts consumption linked to Stock Entry and Purchase Order
- **Landed Cost Estimator** — Configurable customs duty + VAT calculations

## Directory Guide

- `api/` — External connectors (NHTSA, scrapers)
- `doctype/` — Core DocType schemas
- `public/js/` — Client scripts for PO, Item, Stock Entry
- `data_import/` — Bulk import scripts and CSV templates
- `patches/` — Data seeding patches

## License

MIT — Seityl Group Ltd.
