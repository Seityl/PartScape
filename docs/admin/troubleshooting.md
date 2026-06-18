# Troubleshooting

This page lists common issues and how to resolve them.

## PartScape menu does not appear in transactions

1. Clear cache and restart:
   ```bash
   bench --site yoursite.local clear-cache
   bench restart
   ```
2. Make sure the user has either **Purchase Manager** or **Parts Clerk** role.

## Select from Part Catalog shows no results

- Check that the Part Catalogue has data. If counts are zero, run the appropriate importer.
- Try a broader keyword or remove filters.
- If filtering by VIN, make sure Vehicle Part Applicability data exists.

## Selecting a part gives an error

- Check that the user has permission to create Items (Purchase Manager).
- Check the browser console and server error log for details.
- Restart the bench to ensure the latest code is loaded.

## VIN filter returns no parts

- Confirm the VIN is valid and decodes correctly in **VIN Lookup**.
- Confirm Vehicle Part Applicability records exist for the decoded make/model.
- If the vehicle is a JDM import, try the frame number instead of a 17-character VIN.

## Label printing problems

See [Label Printing](../tools/label-printing.md) for detailed troubleshooting.

Quick checks:

- `wkhtmltopdf` is installed on the server.

- The user's Brother QL-800 is installed locally.
- The browser is not blocking popups.

## Part Catalogue counts look wrong

Run this query to see current counts:

```bash
bench --site yoursite.local mariadb -e "SET SQL_BIG_SELECTS=1;
SELECT 'Part Catalogue' as t, COUNT(*) FROM \`tabPart Catalog\`
UNION ALL SELECT 'Supplier Refs', COUNT(*) FROM \`tabPart Supplier Reference\`
UNION ALL SELECT 'Applicability', COUNT(*) FROM \`tabVehicle Part Applicability\`
UNION ALL SELECT 'Interchange', COUNT(*) FROM \`tabPart Interchange\`;"
```

## Database error: MAX_JOIN_SIZE exceeded

Enable large selects in MariaDB:

```sql
SET GLOBAL SQL_BIG_SELECTS = 1;
```

Or add this to your MariaDB configuration:

```ini
[mysqld]
sql_big_selects = 1
```

## Slow searches

- The Part Catalogue table has a FULLTEXT index on part number, part name, and brand.
- Searches with no keyword are cached for one hour.
- If searches are still slow, check server RAM and MariaDB buffer pool size.

## Getting more help

If an issue persists:

1. Check the **Error Log** in ERPNext.
2. Review the server logs in `sites/yoursite.local/logs/`.
3. Raise an issue in the PartScape repository with the error message and steps to reproduce.
