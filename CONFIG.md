# Certbot HAProxy Configuration

## Automatic Configuration

The package installs a default configuration file at `/etc/letsencrypt/certbot-haproxy.ini` that ensures consistent behavior across installations.

### Default Settings

- **Authenticator**: `haproxy-authenticator`
- **Installer**: `haproxy-installer`
- **HTTP-01 Port**: `8000` (HAProxy forwards from port 80)
- **Deploy Hook**: `/usr/bin/certbot-haproxy-deploy`
- **Key Type**: ECDSA (secp256r1) for better performance

## Using the Configuration

The configuration file is automatically used by certbot. You can:

1. **Use defaults** - Just run certbot:
   ```bash
   certbot certonly -d example.com
   ```

2. **Override specific options**:
   ```bash
   certbot certonly -d example.com --key-type rsa
   ```

3. **Use a different config file**:
   ```bash
   certbot --config /path/to/other.ini certonly -d example.com
   ```

## HAProxy Configuration Requirements

Your HAProxy must forward ACME challenges to port 8000:

```haproxy
frontend http-in
    bind *:80
    
    # ACME challenge routing
    acl is_certbot path_beg -i /.well-known/acme-challenge
    use_backend certbot if is_certbot
    
    # Your other rules...

backend certbot
    mode http
    server certbot 127.0.0.1:8000
```

## Customization

Edit `/etc/letsencrypt/certbot-haproxy.ini` to change defaults for your system. Common customizations:

- Change port: `haproxy-authenticator-haproxy-http-01-port = 9000`
- Use RSA keys: `key-type = rsa`
- Custom deploy hook: `deploy-hook = /path/to/custom-script`

## Troubleshooting

### Port Already in Use
If you see "Could not bind TCP port 80", ensure HAProxy is configured to forward ACME challenges to the internal port (default 8000).

### Certificate Not Deploying
Check the deploy hook is executable and configured:
```bash
ls -l /usr/bin/certbot-haproxy-deploy
grep deploy-hook /etc/letsencrypt/certbot-haproxy.ini
```

### Custom HAProxy Config Path
If your haproxy.cfg is not in the standard location:
```bash
certbot certonly --haproxy-installer-haproxy-config-path /custom/path/haproxy.cfg
```
