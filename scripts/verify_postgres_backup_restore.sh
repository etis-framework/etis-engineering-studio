#!/usr/bin/env bash
set -euo pipefail

PGHOST="${ETIS_BACKUP_TEST_PGHOST:-127.0.0.1}"
PGPORT="${ETIS_BACKUP_TEST_PGPORT:-5432}"
PGUSER="${ETIS_BACKUP_TEST_PGUSER:-etis}"
PGPASSWORD="${ETIS_BACKUP_TEST_PGPASSWORD:-etis-test-only}"

SOURCE_DB="${ETIS_BACKUP_SOURCE_DB:-etis_backup_source}"
RESTORE_DB="${ETIS_BACKUP_RESTORE_DB:-etis_backup_restore}"

POSTGRES_IMAGE="${ETIS_BACKUP_POSTGRES_IMAGE:-postgres:16-alpine@sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685}"

BACKUP_FILE="$(mktemp "${TMPDIR:-/tmp}/etis-backup-XXXXXX.dump")"

cleanup() {
  rm -f "${BACKUP_FILE}"

  docker run --rm --network host \
    -e PGPASSWORD="${PGPASSWORD}" \
    "${POSTGRES_IMAGE}" \
    dropdb \
      --if-exists \
      --host="${PGHOST}" \
      --port="${PGPORT}" \
      --username="${PGUSER}" \
      "${SOURCE_DB}" >/dev/null 2>&1 || true

  docker run --rm --network host \
    -e PGPASSWORD="${PGPASSWORD}" \
    "${POSTGRES_IMAGE}" \
    dropdb \
      --if-exists \
      --host="${PGHOST}" \
      --port="${PGPORT}" \
      --username="${PGUSER}" \
      "${RESTORE_DB}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

run_psql() {
  local database="$1"
  local sql="$2"

  docker run --rm --network host \
    -e PGPASSWORD="${PGPASSWORD}" \
    "${POSTGRES_IMAGE}" \
    psql \
      --host="${PGHOST}" \
      --port="${PGPORT}" \
      --username="${PGUSER}" \
      --dbname="${database}" \
      --no-psqlrc \
      --set=ON_ERROR_STOP=1 \
      --tuples-only \
      --no-align \
      --command="${sql}"
}

echo "Creating isolated backup source and restore databases."

for database in "${SOURCE_DB}" "${RESTORE_DB}"; do
  docker run --rm --network host \
    -e PGPASSWORD="${PGPASSWORD}" \
    "${POSTGRES_IMAGE}" \
    dropdb \
      --if-exists \
      --host="${PGHOST}" \
      --port="${PGPORT}" \
      --username="${PGUSER}" \
      "${database}" >/dev/null 2>&1 || true

  docker run --rm --network host \
    -e PGPASSWORD="${PGPASSWORD}" \
    "${POSTGRES_IMAGE}" \
    createdb \
      --host="${PGHOST}" \
      --port="${PGPORT}" \
      --username="${PGUSER}" \
      "${database}"
done

SOURCE_DATABASE_URL="postgresql+psycopg://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/${SOURCE_DB}"

echo "Migrating backup source database to Alembic head."
ETIS_DATABASE_URL="${SOURCE_DATABASE_URL}" alembic upgrade head

EXPECTED_REVISION="$(
  run_psql "${SOURCE_DB}" "SELECT version_num FROM alembic_version;"
)"

if [ -z "${EXPECTED_REVISION}" ]; then
  echo "Source database does not contain an Alembic revision."
  exit 1
fi

echo "Creating backup/restore sentinel data."
run_psql "${SOURCE_DB}" \
  "CREATE TABLE gate16_backup_restore_sentinel (
     id integer PRIMARY KEY,
     marker text NOT NULL
   );
   INSERT INTO gate16_backup_restore_sentinel (id, marker)
   VALUES (1, 'gate16-backup-restore-ok');" >/dev/null

echo "Creating PostgreSQL logical backup."
docker run --rm --network host \
  -e PGPASSWORD="${PGPASSWORD}" \
  "${POSTGRES_IMAGE}" \
  pg_dump \
    --host="${PGHOST}" \
    --port="${PGPORT}" \
    --username="${PGUSER}" \
    --dbname="${SOURCE_DB}" \
    --format=custom \
    --no-owner \
    --no-privileges \
    > "${BACKUP_FILE}"

test -s "${BACKUP_FILE}"

echo "Restoring PostgreSQL logical backup into clean database."
docker run --rm --network host \
  -i \
  -e PGPASSWORD="${PGPASSWORD}" \
  "${POSTGRES_IMAGE}" \
  pg_restore \
    --host="${PGHOST}" \
    --port="${PGPORT}" \
    --username="${PGUSER}" \
    --dbname="${RESTORE_DB}" \
    --no-owner \
    --no-privileges \
    --exit-on-error \
    < "${BACKUP_FILE}"

RESTORED_REVISION="$(
  run_psql "${RESTORE_DB}" "SELECT version_num FROM alembic_version;"
)"

if [ "${RESTORED_REVISION}" != "${EXPECTED_REVISION}" ]; then
  echo "Restore validation failed: Alembic revision changed."
  echo "Expected: ${EXPECTED_REVISION}"
  echo "Restored: ${RESTORED_REVISION}"
  exit 1
fi

RESTORED_MARKER="$(
  run_psql "${RESTORE_DB}" \
    "SELECT marker FROM gate16_backup_restore_sentinel WHERE id = 1;"
)"

if [ "${RESTORED_MARKER}" != "gate16-backup-restore-ok" ]; then
  echo "Restore validation failed: sentinel data was not recovered."
  exit 1
fi

echo "PostgreSQL backup/restore drill passed."
echo "Alembic revision: ${RESTORED_REVISION}"
