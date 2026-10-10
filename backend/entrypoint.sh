#!/bin/sh
# Runs before the API starts: apply database migrations, then make sure
# every permission exists (existing role changes are kept).
set -e

alembic upgrade head
python -m app.scripts.seed_permissions

exec "$@"
