# PostgreSQL for Masroofy. The schema itself is created by the backend's Flyway migrations
# (Backend/src/main/resources/db/migration); this image only prepares the server.
FROM postgres:16-alpine

# Entity doc convention: every timestamp is stored in UTC.
ENV TZ=UTC \
    PGTZ=UTC

# Runs once, on the first start with an empty data volume.
COPY init/ /docker-entrypoint-initdb.d/

# POSTGRES_DB, POSTGRES_USER and POSTGRES_PASSWORD come from the environment (docker-compose / .env).
HEALTHCHECK --interval=5s --timeout=5s --start-period=10s --retries=10 \
    CMD pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" || exit 1

EXPOSE 5432
