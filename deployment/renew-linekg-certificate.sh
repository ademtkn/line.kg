#!/bin/sh
# Install as /etc/letsencrypt/renewal-hooks/deploy/linekg-reload-nginx.
# Certbot's webroot renewal must reload Nginx to activate the renewed certificate.
set -eu
if [ "${RENEWED_LINEAGE:-}" = "/etc/letsencrypt/live/line.kg" ]; then
    /usr/sbin/nginx -t
    /bin/systemctl reload nginx
fi
