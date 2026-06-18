# PartScape Label Printing — Brother QL-800

Native Frappe/ERPNext label printing for the Brother QL-800 USB thermal printer, supporting DK-22205 62 mm continuous labels and DK-11201 29 mm × 90 mm die-cut labels.

This implementation uses a **browser-native workflow**: the server generates a label-sized PNG and the client opens the OS print dialog, so each user selects their own locally attached Brother QL-800.

## What is included

- **PartScape Settings** — includes the default label size for label printing.
- **Custom fields** on Item (`partscape_barcode`) and Warehouse (`warehouse_code`, `warehouse_zone`).
- **Server module** `partscape/print_label.py` with barcode generation and label PNG generation.
- **Print Formats** — four Jinja thermal label layouts:
  - PartScape Item Label 62mm
  - PartScape Item Label 29mm
  - PartScape Warehouse Label 62mm
  - PartScape Warehouse Label 29mm
- **Client scripts** — "Print Label" button on Item and Warehouse forms, plus a "Generate Barcode" button on Item when the barcode is empty.

## Dependencies

The following Python packages are declared in `pyproject.toml`:

```text
brother-ql>=0.9
python-barcode>=0.13.1
Pillow>=9.0.0
```

Install them with bench:

```bash
bench pip install brother-ql python-barcode Pillow
```

For label generation you need `wkhtmltopdf` (which also includes `wkhtmltoimage`). Frappe normally installs it. Verify with:

```bash
which wkhtmltopdf
```

If it is missing, install wkhtmltopdf for your distribution.

## Frappe configuration

1. Go to **PartScape Settings** (search from the desk).
2. In the **Label Printing** section, choose the **Default Label Size**:
   - `62mm continuous` (DK-22205)
   - `29mmx90mm` (DK-11201)
3. Save.

The printer itself is not configured here — each user selects it in their browser/OS print dialog.

## Client workstation setup

1. Install the Brother QL-800 driver for your operating system.
2. Plug in the printer and load the correct DK roll.
3. In the OS printer settings, define the paper/label size:
   - 62 mm continuous → set length to 100 mm (or select continuous).
   - 29 mm × 90 mm → select the die-cut label size.

## Usage

### Item labels

1. Open an **Item**.
2. If the **PartScape Barcode** field is empty, click **Generate Barcode**.
3. Click **Print Label** and choose the label size.
4. Click **Print** — a label-sized PDF opens in a new tab.
5. In the PDF viewer, click **Print** and select the local **Brother QL-800**.

The label includes company name, price, item name, brand, category, OEM/part number, and a scannable barcode.

### Warehouse labels

1. Open a **Warehouse**.
2. Click **Print Label** and choose the label size.
3. Click **Print** — a label-sized PDF opens in a new tab.
4. In the PDF viewer, click **Print** and select the local **Brother QL-800**.

The label includes warehouse name, warehouse code, zone/area, and a scannable barcode.

## Barcode generation

- **Code 128** is used by default (works with any alphanumeric value).
- If the source value is exactly 12 or 13 numeric digits, **EAN-13** is generated automatically to match the reference label style.

## How it works

1. The user clicks **Print Label** in the Item or Warehouse form.
2. The client calls the server method `partscape.print_label.get_label_pdf`.
3. The server renders the Jinja Print Format and converts it to a PDF with the exact label page size using `wkhtmltopdf`:
   - 62 mm continuous → 62 mm × 100 mm page
   - 29 mm × 90 mm → 29 mm × 90 mm page
4. The client opens the PDF in a new browser tab.
5. The user clicks **Print** in the PDF viewer and selects the local Brother QL-800. Because the PDF already has the correct page size, the OS print dialog defaults to the right paper size and the label is not scaled down to A4/Letter.

## Troubleshooting

### `get_label_image` not found / method error

Restart the bench workers so the updated Python module is loaded:

```bash
bench restart
bench --site erp.autodepot.local clear-cache
```

### Nothing happens when I click Print

- Check that the browser did not block the popup. The print view opens in a new tab/window.
- Ensure the site is served over HTTPS or localhost.

### Label is cut off or scaled incorrectly

- Because the label is generated as a PDF with the exact page size, the OS print dialog should default to the right paper size. If it does not, manually select the matching custom paper size (62 mm × 100 mm or 29 mm × 90 mm).
- In the OS print dialog, disable scaling / fit-to-page.
- Select the exact label size in the Brother driver (62 mm continuous or 29 mm × 90 mm).
- Verify **Default Label Size** matches the physical roll loaded in the printer.

### Barcode does not scan

- Make sure the printed label is not scaled by the OS print dialog.
- Use a high print quality setting in the Brother driver.
- Ensure the label roll matches the selected size.

### PDF generation fails

`get_label_pdf` requires `wkhtmltopdf`. If it is missing, the server returns an error. Install wkhtmltopdf on the Frappe host.

The older PNG fallback (`get_label_image`) is still available on the server but is no longer used by the client print workflow.
