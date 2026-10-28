-- Register the three sources in Zetaris (run once; Administrators only).
-- 1) PostgreSQL datasource: the organisation's compliance register.
--    The demo database lives on the private Docker network next to Zetaris and holds only
--    synthetic data; the read-only role uses trust auth there. Use a real secret elsewhere.
CREATE DATASOURCE grants_pg DESCRIBE BY "Synthetic grant compliance register, PostgreSQL" OPTIONS (jdbcdriver "org.postgresql.Driver", jdbcurl "jdbc:postgresql://regsentinel-pg:5432/grants", username "sentinel_reader", password "", fetchsize "1000");
REGISTER DATASOURCE TABLES FROM grants_pg;
-- 2) File store: eCFR paragraph snapshots for 2024-09-30 and 2024-10-01 (public domain).
CREATE LIGHTNING DATABASE ecfr_files DESCRIBE BY "eCFR 2 CFR Part 200 paragraph snapshots, public domain";
CREATE LIGHTNING FILESTORE TABLE paragraphs FROM ecfr_files FORMAT CSV OPTIONS (path "/home/zetaris/customer-data/shared/regsentinel/paragraphs.csv", header "true", delimiter ",", quote '"', escape '"');
-- 3) Live REST table: the official eCFR versioner index for 2 CFR Part 200.
CREATE LIGHTNING DATABASE ECFR_REST DESCRIBE BY "Live eCFR versioner API";
CREATE LIGHTNING REST TABLE part200_versions FROM ECFR_REST REQUEST(endpoint "https://www.ecfr.gov/api/versioner/v1/versions/title-2.json?part=200", method "get", response_type "json", http_encoding "URLENCODED") HEADER () BODY ();
CREATE SCHEMASTORE CONTAINER regsentinel;
