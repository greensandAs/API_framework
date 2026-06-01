-- Streamlit apps are schema-level objects in Snowflake. 
-- Therefore, they are located in a schema under a database.
-- They also rely on virtual warehouses to provide the compute resource.
-- We recommend starting with X-SMALL warehouses and upgrade when needed.

-- To help your team create Streamlit apps successfully in the schema(s) you own,
-- consider running the following script.
-- Please note that this is an example setup. 
-- You can modify the script to suit your needs.

-- If you want all roles to create Streamlit apps, run
GRANT USAGE ON DATABASE <DATABASE_NAME> TO ROLE PUBLIC;
GRANT USAGE ON SCHEMA <DATABASE_NAME>.<SCHEMA_NAME> TO ROLE PUBLIC;
GRANT CREATE STREAMLIT ON SCHEMA <DATABASE_NAME>.<SCHEMA_NAME> TO ROLE PUBLIC;
GRANT CREATE STAGE ON SCHEMA <DATABASE_NAME>.<SCHEMA_NAME> TO ROLE PUBLIC;

-- Don't forget to grant USAGE on a warehouse (if you can).
GRANT USAGE ON WAREHOUSE <WAREHOUSE_NAME> TO ROLE PUBLIC;

-- If you only want certain roles to create Streamlit apps, 
-- change the role name in the above commands.