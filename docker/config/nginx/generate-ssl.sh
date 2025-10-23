#!/bin/bash
# Generate self-signed SSL certificate for development

set -e

SSL_DIR="/etc/nginx/ssl"
CERT_FILE="$SSL_DIR/nginx.crt"
KEY_FILE="$SSL_DIR/nginx.key"

# Create SSL directory if it doesn't exist
mkdir -p "$SSL_DIR"

# Generate private key
openssl genrsa -out "$KEY_FILE" 2048

# Generate certificate signing request
openssl req -new -key "$KEY_FILE" -out "$SSL_DIR/nginx.csr" -subj "/C=US/ST=State/L=City/O=Organization/OU=OrgUnit/CN=localhost"

# Generate self-signed certificate
openssl x509 -req -days 365 -in "$SSL_DIR/nginx.csr" -signkey "$KEY_FILE" -out "$CERT_FILE"

# Set proper permissions
chmod 600 "$KEY_FILE"
chmod 644 "$CERT_FILE"

# Clean up CSR file
rm "$SSL_DIR/nginx.csr"

echo "SSL certificate generated successfully!"
echo "Certificate: $CERT_FILE"
echo "Private key: $KEY_FILE"