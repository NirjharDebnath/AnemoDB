-- reset.sql

-- Drop the schema and all tables, data, and indexes inside it
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

-- Grant default permissions back
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;