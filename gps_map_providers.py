"""
Abstract map provider interface with multiple implementations.
Supports OpenStreetMap, Google Maps, and other tile servers.
"""

import logging
import requests
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Any
from PIL import Image
from io import BytesIO
from pathlib import Path

logger = logging.getLogger(__name__)


class MapProviderError(Exception):
    """Raised when map operations fail."""
    pass


class MapProvider(ABC):
    """
    Abstract base class for map providers.

    Defines interface for fetching map tiles and metadata.
    """

    @abstractmethod
    def get_tile(self, x: int, y: int, zoom: int) -> Image.Image:
        """
        Get map tile image.

        Args:
            x: Tile X coordinate
            y: Tile Y coordinate
            zoom: Zoom level

        Returns:
            PIL Image object
        """
        pass

    @abstractmethod
    def get_attribution(self) -> str:
        """Get map attribution text."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get provider name."""
        pass

    @abstractmethod
    def validate_coordinates(self, lat: float, lon: float) -> bool:
        """Validate coordinates for this provider."""
        pass


class OSMProvider(MapProvider):
    """OpenStreetMap tile provider."""

    TILE_URL = "http://a.tile.openstreetmap.org/{zoom}/{x}/{y}.png"
    ATTRIBUTION = "© OpenStreetMap contributors"
    NAME = "OpenStreetMap"

    def __init__(self, timeout: int = 5):
        """
        Initialize OSM provider.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.headers = {
            "User-Agent": "GPS-Position-System/1.0"
        }

    def get_tile(self, x: int, y: int, zoom: int) -> Image.Image:
        """Fetch OSM tile."""
        try:
            url = self.TILE_URL.format(zoom=zoom, x=x, y=y)
            response = requests.get(url, headers=self.headers,
                                    timeout=self.timeout)
            response.raise_for_status()

            return Image.open(BytesIO(response.content))

        except Exception as e:
            logger.error(f"Error fetching OSM tile: {e}")
            raise MapProviderError(f"Failed to fetch tile: {e}")

    def get_attribution(self) -> str:
        """Get attribution text."""
        return self.ATTRIBUTION

    def get_name(self) -> str:
        """Get provider name."""
        return self.NAME

    def validate_coordinates(self, lat: float, lon: float) -> bool:
        """Validate coordinates."""
        return -90 <= lat <= 90 and -180 <= lon <= 180


class CartoDarkProvider(MapProvider):
    """Carto Dark Mode tile provider."""

    TILE_URL = "https://a.basemaps.cartocdn.com/dark_all/{zoom}/{x}/{y}.png"
    ATTRIBUTION = "© CARTO, © OpenStreetMap contributors"
    NAME = "Carto Dark"

    def __init__(self, timeout: int = 5):
        """Initialize Carto provider."""
        self.timeout = timeout
        self.headers = {
            "User-Agent": "GPS-Position-System/1.0"
        }

    def get_tile(self, x: int, y: int, zoom: int) -> Image.Image:
        """Fetch Carto tile."""
        try:
            url = self.TILE_URL.format(zoom=zoom, x=x, y=y)
            response = requests.get(url, headers=self.headers,
                                    timeout=self.timeout)
            response.raise_for_status()

            return Image.open(BytesIO(response.content))

        except Exception as e:
            logger.error(f"Error fetching Carto tile: {e}")
            raise MapProviderError(f"Failed to fetch tile: {e}")

    def get_attribution(self) -> str:
        """Get attribution text."""
        return self.ATTRIBUTION

    def get_name(self) -> str:
        """Get provider name."""
        return self.NAME

    def validate_coordinates(self, lat: float, lon: float) -> bool:
        """Validate coordinates."""
        return -90 <= lat <= 90 and -180 <= lon <= 180


class MapProviderFactory:
    """
    Factory for creating map provider instances.

    Manages available providers and provider selection.
    """

    _providers = {
        'osm': OSMProvider,
        'openstreetmap': OSMProvider,
        'carto-dark': CartoDarkProvider,
        'carto': CartoDarkProvider,
    }

    @classmethod
    def create(cls, provider_name: str = 'osm') -> MapProvider:
        """
        Create map provider instance.

        Args:
            provider_name: Provider name (case-insensitive)

        Returns:
            Map provider instance
        """
        provider_class = cls._providers.get(provider_name.lower())

        if provider_class is None:
            available = ", ".join(cls._providers.keys())
            raise MapProviderError(
                f"Unknown provider '{provider_name}'. "
                f"Available: {available}"
            )

        logger.info(f"Created map provider: {provider_name}")
        return provider_class()

    @classmethod
    def register(cls, name: str, provider_class: type) -> None:
        """
        Register custom provider.

        Args:
            name: Provider name
            provider_class: Provider class
        """
        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered map provider: {name}")

    @classmethod
    def list_providers(cls) -> list[str]:
        """List available providers."""
        return list(cls._providers.keys())


class MapTileCache:
    """
    Caches map tiles to reduce network requests.
    """

    def __init__(self, cache_dir: str = ".map_cache", max_size: int = 100):
        """
        Initialize tile cache.

        Args:
            cache_dir: Cache directory path
            max_size: Maximum cached tiles
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_size = max_size
        self.cache_index = {}

    def get_tile_path(self, x: int, y: int, zoom: int) -> Path:
        """Get cache file path for tile."""
        return self.cache_dir / f"tile_{zoom}_{x}_{y}.png"

    def get(self, x: int, y: int, zoom: int) -> Optional[Image.Image]:
        """Get cached tile."""
        try:
            path = self.get_tile_path(x, y, zoom)

            if path.exists():
                logger.debug(f"Cache hit: {path}")
                return Image.open(path)

        except Exception as e:
            logger.warning(f"Cache read error: {e}")

        return None

    def set(self, x: int, y: int, zoom: int,
            image: Image.Image) -> None:
        """Cache tile image."""
        try:
            # Enforce cache size limit
            if len(self.cache_index) >= self.max_size:
                self._evict_oldest()

            path = self.get_tile_path(x, y, zoom)
            image.save(path)

            self.cache_index[str(path)] = True
            logger.debug(f"Cached tile: {path}")

        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    def _evict_oldest(self) -> None:
        """Remove oldest cached tile."""
        if not self.cache_index:
            return

        oldest = min(
            self.cache_dir.glob("tile_*.png"),
            key=lambda p: p.stat().st_mtime
        )

        oldest.unlink()
        del self.cache_index[str(oldest)]
        logger.debug(f"Evicted cached tile: {oldest}")

    def clear(self) -> None:
        """Clear cache."""
        for f in self.cache_dir.glob("tile_*.png"):
            f.unlink()
        self.cache_index.clear()
        logger.info("Cache cleared")
