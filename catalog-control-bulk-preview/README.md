# Catalog Control properties preview

This package adds 59 named Catalog Control extension properties to the existing Authoritative Sources Catalog route. The mapping CSV has 866 rules. The 59 properties are declared at each of the four existing control placements.

1. Replace `mapping.csv` and `routes_config.json` in the DEV notebook.
2. Replace Cells 3 and 4 with the two Python files. Use the structural registry from the current mapper.
3. Run Cells 1–7. The config selects Catalog in Preview with target writes disabled.

Each populated source value is carried as JSON text on its existing control. Local graph validation verified the added properties, control IDs, statements, and relationships. Snowflake DEV Preview is pending.

The worksheet contains 90 named property rows. This package covers 59 new properties. The rest include the existing Content ID property, one repeat, 13 transform rows, 15 TBD rows, and one clipped source field.
