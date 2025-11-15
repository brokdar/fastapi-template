#! /usr/bin/env bash

set -e
set -x

# Run migrations
alembic upgrade head

# Initialize database with required data
python app/db/initialize.py
