# Label Printing

PartScape supports native thermal label printing for the **Brother QL-800** USB printer. Labels are generated as PDFs with the exact page size, and each user prints through their browser/OS print dialog.

## Supported label sizes

| Size | Roll | Use case |
|---|---|---|
| **62 mm continuous** | DK-22205 | Larger item labels with more text and a bigger barcode. |
| **29 mm × 90 mm** | DK-11201 | Smaller die-cut labels. |

## What you need

- Brother QL-800 printer connected to the user's computer.
- Correct label roll loaded.
- `wkhtmltopdf` installed on the Frappe server.
- Label Printer Settings configured.

## Setup

### Server side

1. Install `wkhtmltopdf` on the Frappe server.
2. Install the Python packages:
   ```bash
   bench pip install brother-ql python-barcode Pillow
   ```
3. Go to **Label Printer Settings** and choose the **Default Label Size**.

### User workstation

1. Install the Brother QL-800 driver.
2. Load the correct roll.
3. In the OS printer settings, choose the matching paper size:
   - 62 mm continuous → set length to 100 mm.
   - 29 mm × 90 mm → choose the die-cut size.

## Printing an Item label

1. Open an **Item**.
2. If the **PartScape Barcode** field is empty, click **Generate Barcode**.
3. Click **Print Label**.
4. Choose the label size.
5. A label-sized PDF opens in a new tab.
6. Click **Print** in the PDF viewer and select the local **Brother QL-800**.

The label shows:

- Company name and price
- Item name and brand
- Category
- OEM / part number
- Scannable barcode

## Printing a Warehouse label

1. Open a **Warehouse**.
2. Click **Print Label**.
3. Choose the label size.
4. Print the PDF on the Brother QL-800.

The label shows:

- Warehouse name
- Warehouse code
- Zone / area
- Scannable barcode

## Barcode types

- **Code 128** is used by default for any alphanumeric value.
- If the source value is exactly 12 or 13 numeric digits, **EAN-13** is generated automatically.

## Troubleshooting

### Label is scaled or cut off

- In the OS print dialog, disable **Fit to page** / **Scale to fit**.
- Select the exact paper size: 62 mm × 100 mm or 29 mm × 90 mm.
- Make sure the Brother driver matches the loaded roll.

### Nothing happens when clicking Print

- Check that the browser did not block the popup.
- Ensure the site is served over HTTPS or localhost.
- Restart the bench:
  ```bash
  bench restart
  bench --site yoursite.local clear-cache
  ```

### PDF generation fails

`wkhtmltopdf` must be installed on the server. Verify with:

```bash
which wkhtmltopdf
```

If it is missing, install it and restart the bench.
