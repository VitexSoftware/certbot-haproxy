#!/usr/bin/env python3
"""
Test script to verify certbot-haproxy plugin port configuration fixes.

This script tests the key functionality that was fixed:
1. Proper port parameter parsing
2. Port availability validation
3. Error handling for port conflicts
"""

import os
import sys
import tempfile
import socket
import subprocess
from pathlib import Path
from unittest import mock
import logging

# Add the plugin directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "certbot_haproxy"))

try:
    from certbot_haproxy.authenticator import HAProxyAuthenticator, _test_port_availability
    from certbot import errors
    print("✓ Successfully imported plugin modules")
except ImportError as e:
    print(f"✗ Failed to import plugin modules: {e}")
    print("Make sure certbot and dependencies are installed")
    sys.exit(1)

def test_port_availability_check():
    """Test the port availability checking function."""
    print("\n--- Testing Port Availability Check ---")
    
    # Test with an available port (using 0 to get any available port)
    try:
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.bind(('127.0.0.1', 0))
        _, available_port = test_sock.getsockname()
        test_sock.close()
        
        with _test_port_availability(available_port):
            print(f"✓ Port {available_port} availability check passed")
    except Exception as e:
        print(f"✗ Port availability check failed: {e}")
        return False
    
    # Test with a port that's in use
    try:
        # Create a server socket to occupy a port
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(('127.0.0.1', 0))
        _, occupied_port = server_sock.getsockname()
        server_sock.listen(1)
        
        try:
            with _test_port_availability(occupied_port):
                print("✗ Should have detected port as occupied")
                return False
        except errors.PluginError as e:
            if "already in use" in str(e):
                print(f"✓ Correctly detected port {occupied_port} as occupied")
            else:
                print(f"✗ Wrong error message: {e}")
                return False
        finally:
            server_sock.close()
            
    except Exception as e:
        print(f"✗ Port occupation test failed: {e}")
        return False
    
    return True

def test_plugin_port_configuration():
    """Test that the plugin correctly handles port configuration."""
    print("\n--- Testing Plugin Port Configuration ---")
    
    try:
        # Mock configuration
        mock_config = mock.MagicMock()
        mock_config.http01_port = 80  # Default that should be overridden
        
        # Create authenticator instance
        authenticator = HAProxyAuthenticator(config=mock_config, name="haproxy-authenticator")
        
        # Mock the conf method to return our test port
        test_port = 8000
        authenticator.conf = mock.Mock(return_value=test_port)
        
        # Mock the port availability check to avoid actual binding
        with mock.patch('certbot_haproxy.authenticator._test_port_availability') as mock_port_check:
            mock_port_check.return_value.__enter__ = mock.Mock(return_value=None)
            mock_port_check.return_value.__exit__ = mock.Mock(return_value=None)
            
            # Call prepare method
            authenticator.prepare()
            
            # Verify that the config was updated with our port
            if authenticator.config.http01_port == test_port:
                print(f"✓ Plugin correctly configured to use port {test_port}")
            else:
                print(f"✗ Plugin used wrong port: {authenticator.config.http01_port} (expected {test_port})")
                return False
            
            # Verify that port availability was checked
            mock_port_check.assert_called_once_with(test_port)
            print("✓ Plugin correctly checked port availability")
        
    except Exception as e:
        print(f"✗ Plugin configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_default_port_handling():
    """Test that the plugin uses default port when none is configured."""
    print("\n--- Testing Default Port Handling ---")
    
    try:
        # Mock configuration
        mock_config = mock.MagicMock()
        mock_config.http01_port = 80  # Default that should be overridden
        
        # Create authenticator instance
        authenticator = HAProxyAuthenticator(config=mock_config, name="haproxy-authenticator")
        
        # Mock the conf method to return None (no port configured)
        authenticator.conf = mock.Mock(return_value=None)
        
        # Mock the port availability check
        with mock.patch('certbot_haproxy.authenticator._test_port_availability') as mock_port_check:
            mock_port_check.return_value.__enter__ = mock.Mock(return_value=None)
            mock_port_check.return_value.__exit__ = mock.Mock(return_value=None)
            
            # Call prepare method
            authenticator.prepare()
            
            # Verify that the default port (8000) was used
            if authenticator.config.http01_port == 8000:
                print("✓ Plugin correctly used default port 8000")
            else:
                print(f"✗ Plugin used wrong default port: {authenticator.config.http01_port}")
                return False
            
            # Verify that port availability was checked
            mock_port_check.assert_called_once_with(8000)
            print("✓ Plugin correctly checked default port availability")
        
    except Exception as e:
        print(f"✗ Default port handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_port_80_error_handling():
    """Test that the plugin provides helpful error when trying to use port 80."""
    print("\n--- Testing Port 80 Error Handling ---")
    
    try:
        # Mock configuration
        mock_config = mock.MagicMock()
        mock_config.http01_port = 80
        
        # Create authenticator instance
        authenticator = HAProxyAuthenticator(config=mock_config, name="haproxy-authenticator")
        
        # Mock the conf method to return port 80
        authenticator.conf = mock.Mock(return_value=80)
        
        # Mock the port availability check to fail (port in use)
        with mock.patch('certbot_haproxy.authenticator._test_port_availability') as mock_port_check:
            mock_port_check.side_effect = errors.PluginError("Could not bind to port 80")
            
            try:
                authenticator.prepare()
                print("✗ Should have raised an error for port 80")
                return False
            except errors.PluginError as e:
                error_msg = str(e)
                if "port 80" in error_msg and "haproxy-authenticator-haproxy-http-01-port" in error_msg:
                    print("✓ Plugin provided helpful error message for port 80 conflict")
                else:
                    print(f"✗ Plugin provided unhelpful error message: {error_msg}")
                    return False
        
    except Exception as e:
        print(f"✗ Port 80 error handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def run_cli_test():
    """Test the CLI argument parsing."""
    print("\n--- Testing CLI Argument Parsing ---")
    
    try:
        # Test that the plugin defines the expected CLI arguments
        authenticator_class = HAProxyAuthenticator
        
        # Mock the add function to capture arguments
        added_args = []
        def mock_add(name, **kwargs):
            added_args.append((name, kwargs))
        
        authenticator_class.add_parser_arguments(mock_add)
        
        # Check that the haproxy-http-01-port argument was added
        port_arg_found = False
        for arg_name, arg_config in added_args:
            if arg_name == "haproxy-http-01-port":
                port_arg_found = True
                if arg_config.get('default') == 8000 and arg_config.get('type') == int:
                    print("✓ CLI argument 'haproxy-http-01-port' correctly defined")
                else:
                    print(f"✗ CLI argument has wrong config: {arg_config}")
                    return False
                break
        
        if not port_arg_found:
            print("✗ CLI argument 'haproxy-http-01-port' not found")
            return False
        
    except Exception as e:
        print(f"✗ CLI argument parsing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def main():
    """Run all tests."""
    print("🔧 Testing certbot-haproxy Plugin Fixes")
    print("=" * 50)
    
    # Enable logging for better visibility
    logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
    
    tests = [
        test_port_availability_check,
        test_plugin_port_configuration,
        test_default_port_handling,
        test_port_80_error_handling,
        run_cli_test,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print(f"\n{'=' * 50}")
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! The plugin fixes are working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())