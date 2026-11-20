#!/bin/sh
# Executed once by the postgres image when the data volume is first created.
# The tables are created by the backend's Flyway migrations, not here.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
ALTER DATABASE "$POSTGRES_DB" SET timezone TO 'UTC';
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SQL
