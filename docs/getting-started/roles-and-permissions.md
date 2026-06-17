# Roles & Permissions

PartScape uses two roles to keep things simple.

## Purchase Manager

This is the standard ERPNext **Purchase Manager** role. Users with this role have full access to PartScape. They can:

- Create, edit, and delete Part Catalogue entries.
- Add and edit Vehicle Part Applicability (fitment) records.
- Create and edit Part Interchange relationships.
- Add and edit Part Supplier References.
- Add and edit Vehicle Makes, Models, and Engine Variants.
- Configure PartScape Settings and Label Printer Settings.
- Use the Part Catalog Picker in transactions.
- Print labels.

## Parts Clerk

**Parts Clerk** is a custom role with read-only access. Users with this role can:

- View the Part Catalogue.
- View Vehicle Part Applicability.
- View Part Interchange relationships.
- View Part Supplier References.
- View Vehicles, Vehicle Makes, Models, and Engine Variants.
- View Label Printer Settings.
- Use the Part Catalog Picker in transactions.
- Print labels.

They **cannot** create or edit catalogue data, settings, or vehicle masters.

## Assigning roles

1. Go to **User** in ERPNext.
2. Open the user you want to configure.
3. In the **Roles** child table, add either:
   - **Purchase Manager** for full access, or
   - **Parts Clerk** for read-only access.
4. Save.

## Role summary table

| DocType | Purchase Manager | Parts Clerk |
|---|---|---|
| Part Catalogue | Read / Write / Create / Delete | Read only |
| Part Category | Full | Read only |
| Part Interchange | Full | Read only |
| Part Supplier Reference | Full | Read only |
| Vehicle | Full | Read only |
| Vehicle Make / Model / Engine Variant | Full | Read only |
| Customer Vehicle | Full | Read only |
| PartScape Settings | Full | No access |
| Label Printer Settings | Full | Read only |
| VIN Decode Cache | Full | Read only |

## Best practice

- Give **Purchase Manager** to the people who maintain your catalogue, suppliers, and vehicle data.
- Give **Parts Clerk** to counter staff, warehouse users, and anyone who only needs to look up parts and print labels.
