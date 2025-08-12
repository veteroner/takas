web: DJANGO_SETTINGS_MODULE=config.settings daphne -b 0.0.0.0 -p $PORT config.asgi:application
release: DJANGO_SETTINGS_MODULE=config.settings python manage.py migrate --noinput && DJANGO_SETTINGS_MODULE=config.settings python manage.py collectstatic --noinput

