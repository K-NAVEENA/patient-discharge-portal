#!/usr/bin/env bash
# exit on error
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Create instance directory if not present
mkdir -p instance

# Initialize tables and seed demonstration data
python -c "from app import create_app; from database.seed import seed_database; app = create_app(); app.app_context().push(); seed_database()"
