#!/bin/sh
set -e

# Ждём Postgres: контейнер БД поднимается дольше, чем приложение.
if [ -n "$POSTGRES_HOST" ]; then
  echo "Ожидание Postgres на $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
  until python -c "
import os, socket, sys
s = socket.socket()
s.settimeout(2)
try:
    s.connect((os.environ['POSTGRES_HOST'], int(os.environ.get('POSTGRES_PORT', 5432))))
except OSError:
    sys.exit(1)
"; do
    sleep 1
  done
  echo "Postgres доступен."
fi

if [ "$RUN_MIGRATIONS" = "1" ]; then
  python manage.py migrate --noinput
fi

if [ "$RUN_COLLECTSTATIC" = "1" ]; then
  python manage.py collectstatic --noinput
fi

exec "$@"
