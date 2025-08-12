web: daphne -b 0.0.0.0 -p $PORT config.asgi:application
worker: python manage.py runworker
release: python manage.py migrate --noinput && python manage.py collectstatic --noinput

