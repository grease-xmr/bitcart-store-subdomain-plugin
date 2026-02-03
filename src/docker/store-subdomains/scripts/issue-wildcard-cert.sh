#!/bin/bash
# Guided wildcard certificate issuance via manual DNS-01 challenge
set -e

DOMAIN="${1:-}"
CERT_DIR="${2:-./certs}"

if [ -z "$DOMAIN" ]; then
    echo "Usage: $0 <domain> [cert-output-dir]"
    echo "Example: $0 example.com ./certs"
    exit 1
fi

mkdir -p "$CERT_DIR"

echo ""
echo "========================================================================"
echo "     Wildcard Certificate Issuance for *.$DOMAIN"
echo "========================================================================"
echo ""
echo "This script will guide you through obtaining a wildcard SSL"
echo "certificate using Let's Encrypt with manual DNS verification."
echo ""
echo "You will need access to your DNS provider's control panel."
echo ""
read -p "Press Enter to continue..."

# Step 1: Generate challenge
echo ""
echo "Step 1: Generating DNS challenge..."
echo ""

docker run --rm -v "$CERT_DIR:/acme.sh" neilpang/acme.sh \
    --issue --dns -d "$DOMAIN" -d "*.$DOMAIN" \
    --yes-I-know-dns-manual-mode-enough-go-ahead-please 2>&1 | tee /tmp/acme-output.txt || true

# Extract the TXT record info
echo ""
echo "========================================================================"
echo "                    DNS RECORD REQUIRED"
echo "========================================================================"
echo ""
echo "Add this TXT record in your DNS provider's control panel:"
echo ""
echo "   Type:  TXT"
echo "   Host:  _acme-challenge.$DOMAIN"
echo "   Value: (shown above by acme.sh)"
echo ""
echo "NOTE: For wildcard + root domain, you may need TWO TXT values"
echo "      for the same _acme-challenge host. Add both as separate"
echo "      TXT records."
echo ""
echo "After adding the record(s), wait 2-5 minutes for DNS propagation."
echo ""
read -p "Press Enter after adding the DNS record(s)..."

# Step 2: Verify and complete
echo ""
echo "Step 2: Verifying DNS and completing challenge..."
echo ""

docker run --rm -v "$CERT_DIR:/acme.sh" neilpang/acme.sh \
    --renew -d "$DOMAIN" \
    --yes-I-know-dns-manual-mode-enough-go-ahead-please

echo ""
echo "========================================================================"
echo "                    SUCCESS!"
echo "========================================================================"
echo ""
echo "Certificate files are in: $CERT_DIR/$DOMAIN/"
echo ""
echo "To install in bitcart, run:"
echo ""
echo "  sudo cp $CERT_DIR/$DOMAIN/fullchain.cer \\"
echo "      /var/lib/docker/volumes/bitcart_nginx_certs/_data/*.$DOMAIN.crt"
echo "  sudo cp $CERT_DIR/$DOMAIN/$DOMAIN.key \\"
echo "      /var/lib/docker/volumes/bitcart_nginx_certs/_data/*.$DOMAIN.key"
echo "  docker exec bitcart-nginx-1 nginx -s reload"
echo ""
echo "IMPORTANT: Set a calendar reminder!"
echo "    This certificate expires in 90 days."
echo "    Re-run this script before: $(date -d '+85 days' '+%Y-%m-%d')"
echo ""
