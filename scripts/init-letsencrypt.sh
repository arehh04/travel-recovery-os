#!/bin/bash
# Let's Encrypt initialization script (Phase 10)
# Obtains SSL certificates via certbot standalone challenge
#
# Usage:
#   ./scripts/init-letsencrypt.sh yourdomain.com
#
# Prerequisites:
#   - certbot installed (apt install certbot)
#   - Port 80 accessible from the internet
#   - Domain DNS points to this server

set -euo pipefail

DOMAIN="${1:-}"
EMAIL="${2:-admin@$DOMAIN}"

if [ -z "$DOMAIN" ]; then
    echo "Usage: $0 <domain> [email]"
    echo "Example: $0 example.com admin@example.com"
    exit 1
fi

echo "=== Let's Encrypt Certificate Setup ==="
echo "Domain: $DOMAIN"
echo "Email:  $EMAIL"
echo ""

# Stop nginx temporarily to free port 80
echo "Stopping nginx..."
docker compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true

# Obtain certificate via standalone challenge
echo "Obtaining certificate..."
certbot certonly \
    --standalone \
    --preferred-challenges http \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

echo "Certificate obtained successfully!"

# Update ssl.conf with actual domain
SSL_CONF="nginx/ssl.conf"
if [ -f "$SSL_CONF" ]; then
    sed -i "s/yourdomain.com/$DOMAIN/g" "$SSL_CONF"
    echo "Updated $SSL_CONF with domain: $DOMAIN"
fi

# Setup auto-renewal cron
echo "Setting up auto-renewal cron job..."
CRON_CMD="0 3 * * * certbot renew --quiet --deploy-hook 'docker compose -f docker-compose.prod.yml exec nginx nginx -s reload'"
(crontab -l 2>/dev/null | grep -v "certbot renew"; echo "$CRON_CMD") | crontab -
echo "Auto-renewal cron configured (daily at 3:00 AM)"

# Restart nginx
echo "Starting nginx..."
docker compose -f docker-compose.prod.yml up -d nginx

echo ""
echo "=== Setup Complete ==="
echo "HTTPS is now enabled for $DOMAIN"
echo "Certificate will auto-renew daily at 3:00 AM"
