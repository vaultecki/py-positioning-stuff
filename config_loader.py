import json
import logging
from pathlib import Path
from typing import Any, Optional

class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass

class Config:
    """Singleton configuration manager for JSON files."""
    
    _instance = None
    _config_data = None

    def __new__(cls, config_path: str = "config.json"):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config(config_path)
        return cls._instance

    def _load_config(self, config_path: str) -> None:
        """Load configuration from JSON file."""
        config_file = Path(config_path)

        if not config_file.exists():
            logging.warning(f"Config file {config_path} not found. Using defaults.")
            self._config_data = self._get_default_config()
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config_data = json.load(f)
                logging.info(f"Configuration loaded from {config_path}")
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Error parsing JSON config: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading config file: {e}")

    def get(self, path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation."""
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
        """Get entire configuration section."""
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
                'level': 'INFO'
            }
        }

    def validate(self) -> bool:
        """Validate configuration for required fields."""
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
