-- Executed after any syncdb (including tests)
SET GLOBAL innodb_file_format=Barracuda;
SET GLOBAL innodb_file_per_table=1;
ALTER TABLE grants_grantapplication row_format=DYNAMIC;

