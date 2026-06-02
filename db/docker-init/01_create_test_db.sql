-- Runs once on first container init (Postgres entrypoint).
-- The main database (kpi) is created by POSTGRES_DB; this adds the test database.
CREATE DATABASE kpi_test;
