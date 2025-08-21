#!/usr/bin/env bash
set -euo pipefail

trap 'echo "Migration failed"; exit 1' ERR

if [ ! -f .env ]; then
  echo ".env file not found"
  exit 1
fi

source .env

: "${SOURCE_DATABASE_URL:?SOURCE_DATABASE_URL is required}"
: "${TARGET_DATABASE_URL:?TARGET_DATABASE_URL is required}"

echo "Dumping source database..."
pg_dump "$SOURCE_DATABASE_URL" -Fc --no-owner --no-acl --if-exists -f backup.dump

echo "Restoring into target database..."
pg_restore -d "$TARGET_DATABASE_URL" --clean --if-exists --no-owner --no-acl backup.dump

echo "Migration successful"
