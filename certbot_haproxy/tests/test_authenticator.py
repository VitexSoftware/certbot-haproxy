import unittest
from unittest import mock
import os

from certbot_haproxy.authenticator import HAProxyAuthenticator
from acme import challenges

class TestAuthenticator(unittest.TestCase):

    test_domain = 'le.wtf'

    """Test the relevant functions of the certbot_haproxy installer"""

    def setUp(self):
        mock_le_config = mock.MagicMock(
            # TODO: Don't know what we need here
            )
        self.authenticator = HAProxyAuthenticator(
            config=mock_le_config, name="authenticator")

    def test_more_info(self):
        info = self.authenticator.more_info()
        self.assertIsInstance(info, str)

    @mock.patch("certbot_haproxy.authenticator.logger")
    @mock.patch("certbot.util.logger")
    def test_add_parser_arguments(self, util_logger, certbot_logger):
        """Weak test taken from apache plugin tests"""
        self.authenticator.add_parser_arguments(mock.MagicMock())
        self.assertEqual(certbot_logger.error.call_count, 0)
        self.assertEqual(util_logger.error.call_count, 0)

    def test_supported_challenges(self):
        chal = self.authenticator.supported_challenges
        self.assertIsInstance(chal, list)
        self.assertTrue(challenges.HTTP01 in chal)

    @mock.patch("certbot_haproxy.authenticator._test_port_availability")
    def test_prepare_with_port_configuration(self, mock_port_test):
        """Test that prepare() correctly configures the port"""
        mock_port_test.return_value.__enter__ = mock.Mock(return_value=None)
        mock_port_test.return_value.__exit__ = mock.Mock(return_value=None)
        
        # Mock the conf method to return a specific port
        self.authenticator.conf = mock.Mock(return_value=8000)
        
        # Call prepare
        self.authenticator.prepare()
        
        # Check that the config was updated
        self.assertEqual(self.authenticator.config.http01_port, 8000)
        
        # Check that port availability was tested
        mock_port_test.assert_called_once_with(8000)

    @mock.patch("certbot_haproxy.authenticator._test_port_availability")
    def test_prepare_with_default_port(self, mock_port_test):
        """Test that prepare() uses default port when none configured"""
        mock_port_test.return_value.__enter__ = mock.Mock(return_value=None)
        mock_port_test.return_value.__exit__ = mock.Mock(return_value=None)
        
        # Mock the conf method to return None (no port configured)
        self.authenticator.conf = mock.Mock(return_value=None)
        
        # Call prepare
        self.authenticator.prepare()
        
        # Check that the default port was used
        self.assertEqual(self.authenticator.config.http01_port, 8000)
        
        # Check that port availability was tested
        mock_port_test.assert_called_once_with(8000)
