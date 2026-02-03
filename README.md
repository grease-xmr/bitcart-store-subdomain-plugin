# Store Subdomains Plugin for Bitcart

This plugin enables subdomain-based routing for Bitcart stores and static sites. It allows:

- **Store subdomains**: Access stores via `{slug}.yourdomain.com` instead of `/store/{id}`
- **Static site hosting**: Serve static files from configured directories via subdomains (e.g., `www.yourdomain.com`, `docs.yourdomain.com`)
- **Static redirects**: Redirect subdomains to external URLs

## Requirements

- Bitcart 0.10.x or later
- Docker deployment with nginx reverse proxy
- Wildcard DNS record pointing to your server (`*.yourdomain.com`)
- For HTTPS: Wildcard SSL certificate

## Installation

### Method 1: Admin UI (Recommended for Production)

1. **Package the plugin** (if you have the source):
   ```bash
   cd /path/to/store-subdomains
   bitcart-cli plugin package .
   ```
   This creates `store-subdomains.bitcart`.

2. **Upload via Admin Panel**:
   - Log in to your Bitcart admin panel
   - Navigate to **Server Settings** → **Plugins**
   - Click **Upload Plugin** and select `store-subdomains.bitcart`
   - Wait for the upload to complete

3. **Restart your Bitcart instance**:
   ```bash
   cd /path/to/bitcart-docker
   ./restart.sh
   ```
   The restart triggers a Docker image rebuild that includes the plugin.

### Method 2: CLI Installation

1. **Install with bitcart-cli**:
   ```bash
   cd /path/to/bitcart-docker
   bitcart-cli plugin install /path/to/store-subdomains
   ```

2. **Restart your instance**:
   ```bash
   ./restart.sh
   ```

### Method 3: API Installation

```bash
curl -X POST "https://api.yourdomain.com/plugins/install" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "plugin=@store-subdomains.bitcart"
```

Then restart your Bitcart instance.

## Configuration

### Environment Variables

Add these to your bitcart-docker environment (`.env` or export before running):

| Variable | Description | Example |
|----------|-------------|---------|
| `BITCART_STORE_HOST` | Base domain for store subdomains | `yourdomain.com` |
| `STATIC_SITES_PATH` | Host path to static files directory | `/var/statics` |

### Plugin Settings

Configure via the API after installation:

```bash
# Get an auth token
TOKEN=$(curl -s -X POST "https://api.yourdomain.com/token" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"yourpassword"}' | jq -r '.access_token')

# Configure plugin settings
curl -X PATCH "https://api.yourdomain.com/plugins/store-subdomains/settings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "base_domain": "yourdomain.com",
    "reserved_subdomains": ["www", "api", "admin", "store", "mail", "ftp", "static"],
    "static_sites": {
      "www": "/var/statics/www",
      "docs": "/var/statics/docs"
    },
    "static_redirects": {
      "blog": "https://blog.example.com"
    }
  }'
```

#### Settings Reference

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enabled` | bool | `true` | Enable/disable the plugin |
| `base_domain` | string | `"local"` | Base domain for generating nginx server blocks |
| `reserved_subdomains` | list | `["www", "api", ...]` | Subdomains that cannot be used as store slugs |
| `static_sites` | dict | `{}` | Map of subdomain → directory path for static file serving |
| `static_redirects` | dict | `{}` | Map of subdomain → URL for HTTP redirects |
| `map_file_name` | string | `"subdomain_store.map"` | Nginx map file for store routing |
| `static_sites_file_name` | string | `"static_sites.conf"` | Nginx config file for static sites |
| `static_redirects_file_name` | string | `"static_redirects.map"` | Nginx map file for redirects |

### Static Sites Setup

1. **Create the static files directory** on your host:
   ```bash
   sudo mkdir -p /var/statics/www
   sudo mkdir -p /var/statics/docs
   ```

2. **Add your static files**:
   ```bash
   # Example: Copy a built static site
   cp -r /path/to/website/dist/* /var/statics/www/
   ```

3. **Configure the mount** in your environment:
   ```bash
   export STATIC_SITES_PATH=/var/statics
   ```

4. **Configure the plugin** to serve these directories (see Plugin Settings above).

5. **Restart** to apply changes:
   ```bash
   ./restart.sh
   ```

## Usage

### Assigning Store Slugs

Via API:
```bash
# Set a slug for a store
curl -X PATCH "https://api.yourdomain.com/stores/{store_id}/slug" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"slug": "mystore"}'

# The store is now accessible at https://mystore.yourdomain.com
```

### Removing Store Slugs

```bash
curl -X DELETE "https://api.yourdomain.com/stores/{store_id}/slug" \
  -H "Authorization: Bearer $TOKEN"
```

### Looking Up Stores by Slug

```bash
curl "https://api.yourdomain.com/stores/by-slug/mystore"
# Returns: {"slug": "mystore", "store_id": "..."}
```

## DNS Configuration

### Required DNS Records

1. **Wildcard A record** pointing to your server:
   ```
   *.yourdomain.com    A    YOUR_SERVER_IP
   ```

2. **Or individual records** for each subdomain you use:
   ```
   www.yourdomain.com     A    YOUR_SERVER_IP
   docs.yourdomain.com    A    YOUR_SERVER_IP
   mystore.yourdomain.com A    YOUR_SERVER_IP
   ```

## HTTPS with Wildcard Certificates

Standard Let's Encrypt HTTP-01 validation cannot issue wildcard certificates. You need DNS-01 validation.

### Option 1: Manual DNS-01 Challenge

This plugin includes a helper script for guided wildcard certificate issuance:

```bash
cd /path/to/bitcart-docker
./compose/plugins/docker/cj_store-subdomains/scripts/issue-wildcard-cert.sh yourdomain.com
```

The script will:
1. Generate a DNS challenge
2. Prompt you to add a TXT record to your DNS
3. Complete verification and download the certificate

Then install the certificate:
```bash
sudo cp ./certs/yourdomain.com/fullchain.cer \
    /var/lib/docker/volumes/bitcart_nginx_certs/_data/*.yourdomain.com.crt
sudo cp ./certs/yourdomain.com/yourdomain.com.key \
    /var/lib/docker/volumes/bitcart_nginx_certs/_data/*.yourdomain.com.key
docker exec bitcart-nginx-1 nginx -s reload
```

**Important**: Manual DNS-01 certificates cannot auto-renew. Set a reminder to renew every 85 days.

### Option 2: Automated DNS-01 (Requires DNS API)

If your DNS provider has API access (Cloudflare, Route53, etc.), you can set up automated renewal. See the [acme.sh DNS API documentation](https://github.com/acmesh-official/acme.sh/wiki/dnsapi).

### Option 3: Cloudflare Proxy

Use Cloudflare's proxy with their Universal SSL certificate, which covers wildcards automatically.

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │  nginx (reverse proxy)                  │
                    │  ├── www.domain.com → /var/statics/www  │
                    │  ├── docs.domain.com → /var/statics/docs│
                    │  ├── {slug}.domain.com → /store/{id}    │
                    │  ├── api.domain.com → backend           │
                    │  └── admin.domain.com → admin panel     │
                    └─────────────────────────────────────────┘
                                       ▲
                                       │
  Generated files:                     │
  - subdomain_store.map    ┌───────────┴───────────────────┐
  - static_redirects.map   │  nginx-gen (docker-gen)       │
  - static_sites.conf      │  regenerates nginx.conf       │
                           │  from plugin's nginx.tmpl     │
┌────────────────────┐     └───────────────────────────────┘
│ subdomain-inotify  │                 ▲
│ watches map files  │─────────────────┘
│ triggers reload    │     (sends SIGHUP on file change)
└────────────────────┘
```

### Generated Files

| File | Location | Purpose |
|------|----------|---------|
| `subdomain_store.map` | `/datadir/plugin_data/store-subdomains/` | Maps slugs to store IDs |
| `static_redirects.map` | `/datadir/plugin_data/store-subdomains/` | Maps subdomains to redirect URLs |
| `static_sites.conf` | `/datadir/plugin_data/store-subdomains/` | Nginx server blocks for static sites |

## Troubleshooting

### Plugin not loading

Check the worker logs:
```bash
docker logs bitcart-worker-1 2>&1 | grep -i "store-subdomains"
```

### Nginx not routing subdomains

1. Check if the map files exist:
   ```bash
   docker exec bitcart-backend-1 ls -la /datadir/plugin_data/store-subdomains/
   ```

2. Check the nginx configuration:
   ```bash
   docker exec bitcart-nginx-1 cat /etc/nginx/conf.d/default.conf | grep -A5 "subdomain"
   ```

3. Verify DNS resolution:
   ```bash
   nslookup mystore.yourdomain.com
   ```

### Static sites not serving

1. Verify the mount exists in the nginx container:
   ```bash
   docker exec bitcart-nginx-1 ls -la /var/statics/
   ```

2. Check file permissions - nginx runs as a non-root user.

3. Verify `static_sites.conf` was generated:
   ```bash
   docker exec bitcart-backend-1 cat /datadir/plugin_data/store-subdomains/static_sites.conf
   ```

### Force plugin rebuild

If you update the plugin and changes aren't reflected:
```bash
# Clear the plugin hash to force rebuild
export BACKEND_PLUGINS_HASH=""
./start.sh
```

## Development

### Local Testing

1. Add test domains to `/etc/hosts`:
   ```
   127.0.0.1 local www.local api.local admin.local mystore.local
   ```

2. Configure for local development:
   ```bash
   export BITCART_HOST=api.local
   export BITCART_STORE_HOST=local
   export BITCART_ADMIN_HOST=admin.local
   export BITCART_REVERSEPROXY=nginx  # HTTP only
   ```

3. Use `bitcart-cli plugin install --dev` for symlinked installation during development.

### Running Tests

```bash
cd /path/to/bitcart
pytest tests/test_ext/test_store_subdomains.py -v
```

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request
