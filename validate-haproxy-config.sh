#!/bin/bash
#
# HAProxy ACME Challenge Configuration Validator
# 
# This script helps validate that HAProxy is properly configured to work with
# the certbot-haproxy authenticator for ACME challenge handling.
#

set -euo pipefail

HAPROXY_CONFIG="${HAPROXY_CONFIG:-/etc/haproxy/haproxy.cfg}"
ACME_PORT="${ACME_PORT:-8000}"
TEST_DOMAIN="${TEST_DOMAIN:-test.local}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_haproxy_config() {
    local config_file="$1"
    
    if [[ ! -f "$config_file" ]]; then
        log_error "HAProxy configuration file not found: $config_file"
        return 1
    fi
    
    log_info "Checking HAProxy configuration: $config_file"
    
    # Check for ACME challenge ACL
    if ! grep -q "acl.*certbot.*path_beg.*\.well-known/acme-challenge" "$config_file"; then
        log_error "Missing ACME challenge ACL in HAProxy config"
        log_error "Add: acl is_certbot path_beg -i /.well-known/acme-challenge"
        return 1
    else
        log_info "✓ Found ACME challenge ACL"
    fi
    
    # Check for certbot backend usage
    if ! grep -q "use_backend.*certbot.*if.*certbot" "$config_file"; then
        log_error "Missing certbot backend usage rule"
        log_error "Add: use_backend certbot if is_certbot"
        return 1
    else
        log_info "✓ Found certbot backend usage rule"
    fi
    
    # Check for certbot backend definition
    if ! grep -q "backend.*certbot" "$config_file"; then
        log_error "Missing certbot backend definition"
        log_error "Add a backend certbot section with server pointing to 127.0.0.1:$ACME_PORT"
        return 1
    else
        log_info "✓ Found certbot backend definition"
    fi
    
    # Check if the backend points to the correct port
    if grep -A10 "backend.*certbot" "$config_file" | grep -v "^[[:space:]]*#" | grep -q "server.*127.0.0.1:$ACME_PORT"; then
        log_info "✓ Backend certbot points to port $ACME_PORT"
    else
        log_warn "Backend certbot may not be pointing to expected port $ACME_PORT"
        log_warn "Current certbot backend configuration:"
        grep -A10 "backend.*certbot" "$config_file" | grep -v "^[[:space:]]*#" | grep "server" || true
    fi
    
    return 0
}

check_port_availability() {
    local port="$1"
    
    log_info "Checking if port $port is available for binding..."
    
    if nc -z 127.0.0.1 "$port" 2>/dev/null; then
        log_error "Port $port is already in use"
        log_error "If this is HAProxy or another service, make sure certbot uses a different port"
        return 1
    else
        log_info "✓ Port $port is available"
    fi
    
    return 0
}

suggest_haproxy_config() {
    log_info "Suggested HAProxy configuration for ACME challenges:"
    cat << EOF

# Add to your frontend section:
frontend http-in
    bind *:80
    
    # ACME challenge handling
    acl is_certbot path_beg -i /.well-known/acme-challenge
    use_backend certbot if is_certbot
    
    # Your other rules...
    default_backend your_servers

# Add this backend:
backend certbot
    log global
    mode http
    server certbot 127.0.0.1:$ACME_PORT

# Your other backends...
backend your_servers
    # Your server configuration

EOF
}

test_acme_forwarding() {
    local port="$1"
    local test_domain="$2"
    
    log_info "Testing ACME challenge forwarding (requires HAProxy to be running)..."
    
    # Start a simple HTTP server on the ACME port in the background
    python3 -m http.server "$port" --bind 127.0.0.1 >/dev/null 2>&1 &
    local server_pid=$!
    
    # Give the server time to start
    sleep 2
    
    # Test the forwarding
    if curl -s -H "Host: $test_domain" "http://127.0.0.1/.well-known/acme-challenge/test" | grep -q "Directory listing"; then
        log_info "✓ ACME challenge forwarding appears to be working"
    else
        log_warn "ACME challenge forwarding test failed"
        log_warn "Make sure HAProxy is running and properly configured"
    fi
    
    # Clean up
    kill $server_pid 2>/dev/null || true
}

print_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Validate HAProxy configuration for certbot-haproxy ACME challenges.

OPTIONS:
    -c, --config FILE    HAProxy configuration file (default: /etc/haproxy/haproxy.cfg)
    -p, --port PORT      ACME challenge port (default: 8000)
    -d, --domain DOMAIN  Test domain (default: test.local)
    -h, --help          Show this help message

EXAMPLES:
    $0                                    # Use default settings
    $0 -c /custom/haproxy.cfg -p 8080     # Custom config and port
    $0 --port 9000                       # Use port 9000 for ACME

EOF
}

main() {
    local config_file="$HAPROXY_CONFIG"
    local acme_port="$ACME_PORT"
    local test_domain="$TEST_DOMAIN"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--config)
                config_file="$2"
                shift 2
                ;;
            -p|--port)
                acme_port="$2"
                shift 2
                ;;
            -d|--domain)
                test_domain="$2"
                shift 2
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done
    
    log_info "HAProxy ACME Challenge Configuration Validator"
    log_info "=============================================="
    log_info "Config file: $config_file"
    log_info "ACME port: $acme_port"
    log_info "Test domain: $test_domain"
    echo
    
    local errors=0
    
    # Check HAProxy configuration
    if ! check_haproxy_config "$config_file"; then
        ((errors++))
        echo
        suggest_haproxy_config
    fi
    
    echo
    
    # Check port availability
    if ! check_port_availability "$acme_port"; then
        ((errors++))
    fi
    
    echo
    
    # Test forwarding if no errors so far
    if [[ $errors -eq 0 ]]; then
        if command -v nc >/dev/null 2>&1 && command -v curl >/dev/null 2>&1; then
            test_acme_forwarding "$acme_port" "$test_domain"
        else
            log_warn "Skipping forwarding test (requires nc and curl commands)"
        fi
    fi
    
    echo
    
    if [[ $errors -eq 0 ]]; then
        log_info "✓ HAProxy configuration validation passed!"
        log_info "You can now use: certbot --authenticator haproxy-authenticator --haproxy-authenticator-haproxy-http-01-port $acme_port"
    else
        log_error "✗ HAProxy configuration validation failed with $errors error(s)"
        log_error "Please fix the configuration issues before running certbot-haproxy"
        exit 1
    fi
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi