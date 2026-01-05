"""HAProxy Authenticator.

The HAProxy Authenticator is an extension of the "standalone" authenticator
that is part of certbot. It limits its functionality to only support the
`http-01` challenge because `tls-sni-01` checks the challenge by connecting to
port 443.  We can't proxy requests to certbot because we can't see the
requested uri until the request is decrypted, and we can't do decryption in
HAProxy because `tls-sni-01` expects to do a TLS handshake.

This authenticator creates its own ephemeral TCP listener on the necessary port
in order to respond to incoming `http-01` challenges from the certificate
authority. You need to forward port requests for `/.well-known/acme-challenge/`
on port 80 to the configured value for `haproxy-http-01-port` (default:8000).
This can be achieved by adding this example to your haproxy configuration
file::

    default_backend nodes

    acl is_certbot path_beg -i /.well-known/acme-challenge
    use_backend certbot if is_certbot

    backend certbot
        log global
        mode http
        server certbot 127.0.0.1:8000

    backend nodes
        log global
        mode http
        option tcplog
        balance roundrobin
        option forwardfor
        option http-server-close
        option httpclose
        http-request set-header X-Forwarded-Port %[dst_port]
        http-request add-header X-Forwarded-Proto https if { ssl_fc }
        option httpchk HEAD / HTTP/1.1\\r\\nHost:localhost
        server node1 127.0.0.1:8080 check
        server node2 127.0.0.1:8080 check
        server node3 127.0.0.1:8080 check
        server node4 127.0.0.1:8080 check

For instructions on how to make HAProxy serve certificates that were created
with this authenticator, read the documentation of the
`.certbot_haproxy.installer`
"""
import logging
import socket
from contextlib import contextmanager

import zope.component
import zope.interface

from acme import challenges
from certbot import errors
from certbot import interfaces
from certbot.plugins import common
from certbot._internal.plugins import standalone

logger = logging.getLogger(__name__)  # pylint:disable=invalid-name


@contextmanager
def _test_port_availability(port, host='127.0.0.1'):
    """Test if a port is available for binding.
    
    Args:
        port (int): Port number to test
        host (str): Host to bind to, defaults to localhost
        
    Raises:
        errors.PluginError: If port is not available
    """
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        yield
    except OSError as e:
        if e.errno == 98:  # Address already in use
            raise errors.PluginError(
                f"Could not bind to port {port} on {host}. "
                f"Port is already in use. If HAProxy is running on port 80, "
                f"make sure you're using a different port (like 8000) for the authenticator "
                f"and that HAProxy forwards /.well-known/acme-challenge/ requests to it."
            )
        else:
            raise errors.PluginError(f"Could not bind to port {port} on {host}: {e}")
    finally:
        if sock:
            sock.close()


@zope.interface.implementer(interfaces.IAuthenticator)
@zope.interface.provider(interfaces.IPluginFactory)
class HAProxyAuthenticator(standalone.Authenticator):
    """HAProxy Authenticator."""

    description = "Certbot standalone authenticator with HAProxy preset."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def prepare(self):
        """Prepare the authenticator."""
        super().prepare()
        # Override the http01_port from config with our haproxy-specific port
        # The CLI arg --haproxy-authenticator-haproxy-http-01-port becomes 'haproxy_http_01_port' in config
        haproxy_port = self.conf('haproxy_http_01_port')
        if haproxy_port is not None:
            self.config.http01_port = haproxy_port
            logger.info(f"Using HAProxy authenticator port: {haproxy_port}")
        else:
            # Fallback to default if not set
            default_port = 8000
            self.config.http01_port = default_port
            logger.info(f"Using default HAProxy authenticator port: {default_port}")
        
        logger.debug(f"Final http01_port configuration: {self.config.http01_port}")
        
        # Validate that the configured port is available
        try:
            with _test_port_availability(self.config.http01_port):
                logger.debug(f"Port {self.config.http01_port} is available for binding")
        except errors.PluginError as e:
            # Provide more helpful error message
            if self.config.http01_port == 80:
                raise errors.PluginError(
                    f"The HAProxy authenticator is trying to bind to port 80, which is likely "
                    f"used by HAProxy itself. Please use --haproxy-authenticator-haproxy-http-01-port "
                    f"with a different port (e.g., 8000) and configure HAProxy to forward "
                    f"/.well-known/acme-challenge/ requests to that port."
                )
            else:
                raise

    @classmethod
    def add_parser_arguments(cls, add):
        """
            This method adds extra CLI arguments to the plugin.
            The arguments can be retrieved by asking for corresponding names
            in `self.conf([argument name])`

            .. note:: This overrides a method defined in the parent, we
                are deliberately not calling super() because it would add
                arguments that are not supported.

            :param func add: The function to be called to add an argument.
        """
        add(
            "haproxy-http-01-port",
            help=(
                "Port for the HAProxy authenticator to bind to internally (default: 8000). "
                "HAProxy should forward /.well-known/acme-challenge/ requests from port 80 "
                "to this port. Do NOT use port 80 if HAProxy is already using it."
            ),
            type=int,
            default=8000
        )

    @property
    def supported_challenges(self):
        """
            Challenges supported by this plugin: only http-01
            See introduction for reasoning.

            :returns: List of supported challenges
            :rtype: list
        """
        return [challenges.HTTP01]

    @staticmethod
    def more_info():
        """
            This info string only appears in the curses UI in the plugin
            selection sequence.
        """
        return (
            "This authenticator creates its own ephemeral TCP listener"
            " on the configured internal port (default=8000) in order to"
            " respond to incoming http-01 challenges from the certificate"
            " authority. HAProxy must be configured to forward requests to"
            " /.well-known/acme-challenge/ from port 80 to the configured port."
            " IMPORTANT: Do not use port 80 for the authenticator if HAProxy"
            " is already using it - use port 8000 or another available port."
        )
