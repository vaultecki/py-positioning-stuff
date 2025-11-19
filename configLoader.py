"""
Configuration management module for GPS Position System.
Provides centralized access to configuration parameters.
"""

import yaml
import logging
from pathlib import Path
from typing import Any, Optional


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class Config:
    """
    Singleton configuration manager.

    Loads and provides access to configuration parameters from YAML file.
    Supports nested configuration access via dot notation.

    Example:
        >>> config = Config()
        >>> port = config.get('network.udp_port', default=19711)
    """

    _instance = None
    _config_data = None

    def __new__(cls, config_path: str = "config.yaml"):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config(config_path)
        return cls._instance

    def _load_config(self, config_path: str) -> None:
        """Load configuration from YAML file."""
        config_file = Path(config_path)

        if not config_file.exists():
            logging.warning(f"Config file {config_path} not found. Using defaults.")
            self._config_data = self._get_default_config()
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f)
                logging.info(f"Configuration loaded from {config_path}")
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Error parsing config file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading config file: {e}")

    def get(self, path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            path: Dot-separated path to config value (e.g., 'network.udp_port')
            default: Default value if path not found

        Returns:
            Configuration value or default

        Example:
            >>> config.get('network.udp_port', 19711)
            19711
        """
        if self._config_data is None:
            return default

        keys = path.split('.')
        value = self._config_data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default

        return value

    def get_section(self, section: str) -> dict:
        """
        Get entire configuration section.

        Args:
            section: Top-level section name

        Returns:
            Dictionary with section configuration
        """
        if self._config_data is None:
            return {}

        return self._config_data.get(section, {})

    def _get_default_config(self) -> dict:
        """Return default configuration if file not found."""
        return {
            'network': {
                'udp_address': '127.0.0.1',
                'udp_port': 19711,
                'receive_port': 19710,
                'timeout': 5.0
            },
            'gps': {
                'data_file': 'data/AguasVivasGPSData.mat',
                'start_timeout': 5,
                'time_between_positions': 1.0,
                'max_stored_positions': 1000
            },
            'map': {
                'delta_lat': 0.075,
                'delta_lon': 0.15,
                'zoom_level': 13,
                'update_threshold_km': 1.0
            },
            'ui': {
                'window_title': 'GPS Position Receiver',
                'map_widget_width': 500,
                'map_widget_height': 300
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        }

    def reload(self, config_path: str = "config.yaml") -> None:
        """Reload configuration from file."""
        self._load_config(config_path)

    def validate(self) -> bool:
        """
        Validate configuration for required fields and valid values.

        Returns:
            True if configuration is valid

        Raises:
            ConfigurationError: If configuration is invalid
        """
        required_fields = [
            'network.udp_port',
            'network.receive_port',
            'gps.data_file'
        ]

        for field in required_fields:
            if self.get(field) is None:
                raise ConfigurationError(f"Required field '{field}' is missing")

        # Validate port numbers
        udp_port = self.get('network.udp_port')
        recv_port = self.get('network.receive_port')

        if not (0 < udp_port < 65536):
            raise ConfigurationError(f"Invalid UDP port: {udp_port}")

        if not (0 < recv_port < 65536):
            raise ConfigurationError(f"Invalid receive port: {recv_port}")

        # Validate zoom level
        zoom = self.get('map.zoom_level', 13)
        if not (0 <= zoom <= 19):
            raise ConfigurationError(f"Invalid map zoom level: {zoom}")

        return True


# Convenience function for direct access
_config_instance = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


if __name__ == "__main__":
    # Test configuration loading
    config = Config()

    print("Network Configuration:")
    print(f"  UDP Port: {config.get('network.udp_port')}")
    print(f"  Receive Port: {config.get('network.receive_port')}")

    print("\nGPS Configuration:")
    print(f"  Data File: {config.get('gps.data_file')}")
    print(f"  Max Positions: {config.get('gps.max_stored_positions')}")

    print("\nValidation:", "PASSED" if config.validate() else "FAILED")
