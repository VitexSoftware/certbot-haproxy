# certbot-haproxy Troubleshooting Guide

This document provides solutions to common issues encountered when using the certbot-haproxy plugin.

## Common Issues and Solutions

### Issue 1: "Could not bind TCP port 80" Error

**Problem**: The plugin tries to bind to port 80 even when using `--haproxy-authenticator-haproxy-http-01-port 8000`.

**Root Cause**: The plugin wasn't properly parsing the port configuration parameter.

**Solution**: 
1. **Fixed in latest version**: The plugin now correctly respects the `--haproxy-authenticator-haproxy-http-01-port` parameter.

2. **Correct Usage**:
   ```bash
   certbot certonly \
     --authenticator haproxy-authenticator \
     --haproxy-authenticator-haproxy-http-01-port 8000 \
     -d example.com
   ```

3. **Alternative**: Use the standalone authenticator with custom port:
   ```bash
   certbot certonly \
     --authenticator standalone \
     --http-01-port 8000 \
     -d example.com
   ```

### Issue 2: HAProxy Configuration Problems

**Problem**: HAProxy doesn't forward ACME challenges to the authenticator.

**Solution**: Configure HAProxy properly:

```haproxy
frontend http-in
    bind *:80
    
    # ACME challenge handling - MUST come before other rules
    acl is_certbot path_beg -i /.well-known/acme-challenge
    use_backend certbot if is_certbot
    
    # Your other rules
    default_backend your_servers

backend certbot
    log global
    mode http
    server certbot 127.0.0.1:8000

backend your_servers
    # Your server configuration
```

**Validation**: Use the provided validation script:
```bash
./validate-haproxy-config.sh -p 8000
```

### Issue 3: Port Already in Use

**Problem**: The configured port is already in use by another service.

**Symptoms**:
- "Address already in use" error
- Plugin fails to start

**Solutions**:
1. **Choose a different port**:
   ```bash
   certbot certonly \
     --authenticator haproxy-authenticator \
     --haproxy-authenticator-haproxy-http-01-port 8080 \
     -d example.com
   ```

2. **Check what's using the port**:
   ```bash
   sudo netstat -tulpn | grep :8000
   # or
   sudo ss -tulpn | grep :8000
   ```

3. **Stop conflicting service temporarily** (if safe to do so).

### Issue 4: Certificate Renewal Failures

**Problem**: Automated renewal fails with port binding errors.

**Solution**: Update renewal configuration:

1. **Check existing renewal config**:
   ```bash
   sudo cat /etc/letsencrypt/renewal/example.com.conf
   ```

2. **Update renewal config** to use correct port:
   ```ini
   # Add or modify these lines
   authenticator = haproxy-authenticator
   haproxy_authenticator_haproxy_http_01_port = 8000
   ```

3. **Test renewal**:
   ```bash
   sudo certbot renew --dry-run -d example.com
   ```

### Issue 5: Missing Dependencies

**Problem**: Import errors or missing modules.

**Symptoms**:
- `ModuleNotFoundError: No module named 'zope.component'`
- `ModuleNotFoundError: No module named 'certbot'`

**Solution**: Install dependencies:
```bash
# For Ubuntu/Debian
sudo apt update
sudo apt install python3-certbot python3-zope.interface

# For CentOS/RHEL
sudo yum install python3-certbot python3-zope-interface

# Via pip (if using virtual environment)
pip install certbot zope.interface acme
```

## Best Practices

### 1. Port Selection
- **Avoid port 80**: Never use port 80 for the authenticator if HAProxy is running
- **Use port 8000**: This is the default and recommended port
- **Check availability**: Always verify the port is available before use

### 2. HAProxy Configuration
- **Place ACME ACL first**: ACME challenge rules should come before other routing rules
- **Test configuration**: Use `haproxy -c -f /etc/haproxy/haproxy.cfg` to validate
- **Reload safely**: Use `sudo systemctl reload haproxy` instead of restart when possible

### 3. Automation Setup
- **Use deploy hooks**: Set up proper certificate deployment with `--deploy-hook`
- **Monitor renewals**: Check renewal logs regularly
- **Test renewals**: Use `--dry-run` to test renewal process

## Debugging Steps

### 1. Enable Debug Logging
```bash
certbot --authenticator haproxy-authenticator \
  --haproxy-authenticator-haproxy-http-01-port 8000 \
  --debug \
  --dry-run \
  -d example.com
```

### 2. Check Port Status
```bash
# Check if port is in use
sudo netstat -tulpn | grep :8000

# Test port binding manually
python3 -c "
import socket
s = socket.socket()
try:
    s.bind(('127.0.0.1', 8000))
    print('Port 8000 is available')
except OSError as e:
    print(f'Port 8000 is not available: {e}')
finally:
    s.close()
"
```

### 3. Test HAProxy ACME Forwarding
```bash
# Start test server on ACME port
python3 -m http.server 8000 --bind 127.0.0.1 &
SERVER_PID=$!

# Test forwarding
curl -H "Host: example.com" "http://localhost/.well-known/acme-challenge/test"

# Clean up
kill $SERVER_PID
```

### 4. Verify Plugin Installation
```bash
certbot plugins
# Should show haproxy-authenticator in the list
```

### 5. Check Certbot Configuration
```bash
# View current configuration
certbot config
# or check specific domain renewal config
sudo cat /etc/letsencrypt/renewal/example.com.conf
```

## Migration from Older Versions

If you're upgrading from an older version of certbot-haproxy:

1. **Update renewal configurations**: Older configs might have incorrect port settings
2. **Test with dry-run**: Always test before actual renewal
3. **Update HAProxy config**: Ensure it matches the current recommended format
4. **Check plugin entry points**: Make sure the plugin is properly registered

## Getting Help

If you still encounter issues:

1. **Enable debug logging**: Use `--debug` flag
2. **Check HAProxy logs**: Look for forwarding issues
3. **Validate configuration**: Use the validation script
4. **Create minimal test case**: Try with a simple HAProxy config first
5. **Check plugin version**: Ensure you're using the latest version with the fixes

## Example Working Configuration

Here's a complete working example:

**HAProxy configuration** (`/etc/haproxy/haproxy.cfg`):
```haproxy
global
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s

defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms

frontend http-in
    bind *:80
    
    # ACME challenge handling
    acl is_certbot path_beg -i /.well-known/acme-challenge
    use_backend certbot if is_certbot
    
    # Redirect HTTP to HTTPS
    redirect scheme https code 301 if !{ ssl_fc }

frontend https-in
    bind *:443 ssl crt /etc/haproxy/ssl/
    
    # Your HTTPS routing rules
    default_backend web_servers

backend certbot
    log global
    mode http
    server certbot 127.0.0.1:8000

backend web_servers
    balance roundrobin
    server web1 127.0.0.1:8080 check
```

**Certbot command**:
```bash
certbot certonly \
  --authenticator haproxy-authenticator \
  --haproxy-authenticator-haproxy-http-01-port 8000 \
  --deploy-hook "/usr/bin/certbot-haproxy-deploy" \
  -d example.com
```

**Renewal configuration** (`/etc/letsencrypt/renewal/example.com.conf`):
```ini
version = 1.0.0
archive_dir = /etc/letsencrypt/archive/example.com
cert = /etc/letsencrypt/live/example.com/cert.pem
privkey = /etc/letsencrypt/live/example.com/privkey.pem
chain = /etc/letsencrypt/live/example.com/chain.pem
fullchain = /etc/letsencrypt/live/example.com/fullchain.pem

[renewalparams]
authenticator = haproxy-authenticator
haproxy_authenticator_haproxy_http_01_port = 8000
account = your-account-id
server = https://acme-v02.api.letsencrypt.org/directory
```