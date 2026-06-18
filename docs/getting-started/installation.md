# Installation & Setup

This guide explains how to install the PartScape app on a Frappe/ERPNext bench.

## Prerequisites

Before you start, you need:

- A working Frappe Bench (version 16).
- ERPNext installed on the same bench.
- MariaDB with large-query support enabled.
- `wkhtmltopdf` installed on the server (used for label PDF generation).
- A GitHub account with access to the PartScape repository.

## 1. Install the app on the bench

Run the following commands on your Frappe server:

```bash
cd /home/user/frappe-bench
bench get-app --branch version-16 https://github.com/Seityl/PartScape.git
```

This downloads the PartScape app into `apps/partscape`.

## 2. Install the app on your site

```bash
bench --site yoursite.local install-app partscape
bench --site yoursite.local migrate
bench restart
```

The `migrate` command:

- Creates all PartScape DocTypes (Part Catalogue, Vehicle Model, Part Interchange, etc.).
- Loads fixtures such as custom fields, print formats, and roles.
- Runs any pending patches (for example, seeding vehicle makes and models).

## 3. Install extra Python packages

PartScape needs a few Python packages that are not included with ERPNext:

```bash
bench pip install brother-ql python-barcode Pillow
```

These packages are also declared in the app's `pyproject.toml` and will be installed automatically when you run `bench get-app` or `bench setup requirements`.

## 4. Verify wkhtmltopdf

Label printing uses `wkhtmltopdf` to generate label-sized PDFs. Check that it is available:

```bash
which wkhtmltopdf
```

If it is missing, install it for your operating system. On Ubuntu/Debian:

```bash
sudo apt update
sudo apt install wkhtmltopdf
```

## 5. First-time configuration

After installation, complete the setup steps in [PartScape Settings](settings.md).

## Common issues

### `wkhtmltopdf` not found when printing labels

Install `wkhtmltopdf` on the server and restart the bench:

```bash
bench restart
```

### App changes do not appear

Clear the site cache and restart:

```bash
bench --site yoursite.local clear-cache
bench restart
```

### Migrate fails on a large table

If you see an error about `MAX_JOIN_SIZE`, enable large selects for the session or globally in MariaDB:

```sql
SET GLOBAL SQL_BIG_SELECTS = 1;
```

## Updating PartScape

To update to the latest code:

```bash
cd /home/user/frappe-bench/apps/partscape
git pull origin version-16
cd /home/user/frappe-bench
bench --site yoursite.local migrate
bench restart
```

Always back up your site before updating.
