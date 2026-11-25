#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files into STATIC_ROOT for WhiteNoise
python manage.py collectstatic --no-input

# Seed university demo data (15 skills, sample projects, students & faculty accounts)
python manage.py seed_demo
