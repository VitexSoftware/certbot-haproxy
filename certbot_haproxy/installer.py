import os
import shutil
import subprocess
import logging
from certbot import interfaces
from certbot.plugins import common

logger = logging.getLogger(__name__)

class HaproxyInstaller(common.Installer):
    """Certbot Installer for HAProxy."""

    description = "Installer plugin for HAProxy"

    @classmethod
    def add_parser_arguments(cls, add):
        """Add plugin-specific command-line arguments."""
        add("haproxy-config-path", help="Path to the HAProxy configuration file")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_path = self.conf("haproxy-config-path")

    def prepare(self):
        """Prepare the installer (e.g., check if HAProxy is installed)."""
        if not self.config_path:
            raise ValueError("HAProxy configuration path must be specified.")

    def more_info(self):
        """Return a string with additional information about the plugin."""
        return "This plugin installs certificates into HAProxy."

    def deploy_cert(self, domain, cert_path, key_path, chain_path, fullchain_path):
        """
        Deploy the certificate and private key for HAProxy.

        :param domain: Domain name
        :param cert_path: Path to the certificate file
        :param key_path: Path to the private key file
        :param chain_path: Path to the chain file
        :param fullchain_path: Path to the full chain file
        """
        target_dir = "/etc/letsencrypt/haproxy_fullchains"
        os.makedirs(target_dir, exist_ok=True)

        target_pem_path = os.path.join(target_dir, f"{domain}.pem")

        try:
            with open(fullchain_path, 'rb') as cert_file:
                cert_data = cert_file.read()
            with open(key_path, 'rb') as key_file:
                key_data = key_file.read()

            # Sloučíme certifikát a klíč dohromady
            with open(target_pem_path, 'wb') as pem_file:
                pem_file.write(cert_data)
                pem_file.write(key_data)

            logger.info(f"Deployed combined cert and key for {domain} to {target_pem_path}")
        except Exception as e:
            logger.error(f"Failed to deploy certificate for {domain}: {e}")
            raise

    def enhance(self, domain, enhancement, options=None):
        """
        Enhance the configuration.

        :param domain: Domain name
        :param enhancement: Enhancement type
        :param options: Additional options
        """
        raise NotImplementedError("Enhancement logic is not implemented yet.")

    def supported_enhancements(self):
        """Return a list of supported enhancements."""
        return []

    def save(self, title=None, temporary=False):
        """Save the configuration."""
        # Implement logic to save HAProxy configuration
        raise NotImplementedError("Save logic is not implemented yet.")

    def rollback_checkpoints(self, rollback=1):
        """Rollback configuration to a previous checkpoint."""
        raise NotImplementedError("Rollback logic is not implemented yet.")

    def config_test(self):
        """Test the HAProxy configuration."""
        try:
            # Run HAProxy config test
            subprocess.run(["haproxy", "-c", "-f", self.config_path], check=True)
            logger.info("HAProxy configuration test passed.")
        except subprocess.CalledProcessError:
            logger.error("HAProxy configuration test failed.")
            raise

    def restart(self):
        """Restart the HAProxy service."""
        try:
            # Restart HAProxy
            subprocess.run(["systemctl", "restart", "haproxy"], check=True)
            logger.info("HAProxy service restarted successfully.")
        except subprocess.CalledProcessError:
            logger.error("Failed to restart HAProxy service.")
            raise


    def get_all_names(self):
        """Return all names that may be authenticated."""
        # Installer obvykle nemá co autentizovat, vracíme prázdnou množinu.
        return set()
