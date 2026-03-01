#!/bin/sh
# Entrypoint for Railway: patch nginx listen port from $PORT env var,
# then hand off to supervisord.
set -e

PORT="${PORT:-80}"

echo "Starting VoidFill — nginx will listen on port ${PORT}"

# Replace the hardcoded listen 80 with the Railway-injected $PORT
sed -i "s/listen 80;/listen ${PORT};/g" /etc/nginx/voidfill.conf

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
