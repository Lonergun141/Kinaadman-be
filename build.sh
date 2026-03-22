#!/usr/bin/env bash

set -o errexit

pip install -r requirements/production.txt

export DJANGO_SETTINGS_MODULE=config.settings.production

python manage.py collectstatic --no-input
python manage.py migrate --no-input
