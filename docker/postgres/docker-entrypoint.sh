#!/bin/sh
set -e

for ext in postgis hstore; do
    create_ext_sql="CREATE EXTENSION IF NOT EXISTS $ext"
    # Add the extensions to the default db template so that any
    # new db will have the extensions enabled includin test db.
    echo "Installing $ext extension for template1"
    psql template1 -c "$create_ext_sql"
    echo "Installing $ext extension for $POSTGRES_DB database"
    psql --username "$POSTGRES_USER" "$POSTGRES_DB" -c "$create_ext_sql"
done
