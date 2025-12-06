#!/usr/bin/env bash

set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BACKEND_DIR"

export POSTGRES__HOST="localhost"
export POSTGRES__PORT="5432"
export POSTGRES__USER="test_user"
export POSTGRES__PASSWORD="test_password"
export POSTGRES__DB="test_db"

export LOG__LEVEL="WARNING"
export LOG__DISABLE_COLORS="true"

export AUTH__JWT__SECRET_KEY="test-secret-key-min-32-chars-long-for-security"
export AUTH__JWT__ALGORITHM="HS256"
export AUTH__JWT__ACCESS_TOKEN_EXPIRE_MINUTES="15"
export AUTH__JWT__REFRESH_TOKEN_EXPIRE_DAYS="7"

export AUTH__ENABLED="true"
export AUTH__JWT__ENABLED="true"
export AUTH__API_KEY__ENABLED="true"

# High rate limits for integration tests to avoid rate limiting
export AUTH__JWT__LOGIN_RATE_LIMIT="1000/minute"
export AUTH__JWT__REFRESH_RATE_LIMIT="1000/minute"
export AUTH__JWT__LOGOUT_RATE_LIMIT="1000/minute"
export AUTH__API_KEY__CREATE_RATE_LIMIT="1000/minute"
export AUTH__API_KEY__DELETE_RATE_LIMIT="1000/minute"
export AUTH__JWT__BLACKLIST_ENABLED="true"

export SUPER_USER__NAME="testadmin"
export SUPER_USER__EMAIL="testadmin@example.com"
export SUPER_USER__PASSWORD="testpass123"

DB_CONTAINER_NAME="backend-test-db-1"
WAIT_TIMEOUT=60
WAIT_INTERVAL=2

echo ""
echo "▶ SETUP"
echo "────────────────────────────────────────"

cleanup() {
    echo ""
    echo "▶ CLEANUP"
    echo "────────────────────────────────────────"
    docker compose -f docker-compose.test.yml down -v
    echo "✓ Cleanup complete"
}

trap cleanup EXIT INT TERM

echo "  • Cleaning previous state..."
docker compose -f docker-compose.test.yml down -v 2>&1 | grep -v "^$" || true

echo "  • Starting test database..."
docker compose -f docker-compose.test.yml up -d

echo -n "  • Waiting for database"
SECONDS=0
while true; do
    DB_HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' $DB_CONTAINER_NAME 2>/dev/null || echo "unknown")

    if [ "$DB_HEALTH_STATUS" = "healthy" ]; then
        echo " ✓"
        break
    fi

    if [ $SECONDS -ge $WAIT_TIMEOUT ]; then
        echo " ✗"
        echo ""
        echo "ERROR: PostgreSQL failed to become healthy within $WAIT_TIMEOUT seconds"
        echo "Database status: $DB_HEALTH_STATUS"
        docker logs $DB_CONTAINER_NAME
        exit 1
    fi

    echo -n "."
    sleep $WAIT_INTERVAL
done

source .venv/bin/activate

echo "  • Running migrations..."
alembic upgrade head 2>&1 | grep -E "(Running upgrade|ERROR)" || true

echo "  • Initializing database..."
python app/db/initialize.py

echo ""
echo "▶ TESTS"
echo "────────────────────────────────────────"

if [ $# -gt 0 ]; then
    pytest "$@"
else
    pytest tests/integration/ -v
fi

TEST_EXIT_CODE=$?

echo ""
echo "▶ RESULTS"
echo "────────────────────────────────────────"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✓ All tests passed (exit code: 0)"
else
    echo "✗ Tests failed (exit code: $TEST_EXIT_CODE)"
fi

exit $TEST_EXIT_CODE
