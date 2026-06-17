# PartScape

Auto-parts intelligence system for fleet and workshop management, integrated natively into ERPNext.

## Quick Start

```bash
# From bench directory
bench get-app https://github.com/seityl/partscape.git
bench --site your-site.local install-app partscape
bench --site your-site.local migrate
```

## Features

- **VIN Decode Cache** — NHTSA vPIC + VIN Decoder EU (Vincario) + JDM frame number lookups
- **Part Catalog** — OEM part numbers and descriptions
- **Part Interchange** — Aftermarket cross-references (Bosch, Denso, KYB, etc.)
- **Vehicle Master** — Full fleet tracking with RHD/LHD awareness
- **Landed Cost Estimator** — Configurable customs duty + VAT calculations

## Documentation

User-friendly documentation is available in the [`docs/`](docs/) folder:

- [Wiki Home](docs/README.md)
- [Installation & Setup](docs/getting-started/installation.md)
- [Roles & Permissions](docs/getting-started/roles-and-permissions.md)
- [Part Catalogue](docs/part-catalogue/overview.md)
- [Label Printing](docs/tools/label-printing.md)
- [Troubleshooting](docs/admin/troubleshooting.md)

## Directory Guide

- `api/` — External connectors (NHTSA vPIC, VIN Decoder EU, scrapers)
- `doctype/` — Core DocType schemas
- `public/js/` — Client scripts for PO, Item, Stock Entry
- `data_import/` — Bulk import scripts and CSV templates
- `patches/` — Data seeding patches
- `docs/` — User wiki documentation

## License

MIT — Seityl Group Ltd.
