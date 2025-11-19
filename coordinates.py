"""
Unified coordinate system for GPS Position System.
Provides consistent coordinate conversion and validation.
"""

from dataclasses import dataclass
from typing import Literal, Tuple
import math


class CoordinateError(Exception):
    """Raised when coordinate values are invalid."""
    pass


@dataclass
class Coordinate:
    """
    Represents a single coordinate (latitude or longitude).

    Attributes:
        decimal_degrees: Coordinate in decimal degree format
        hemisphere: Direction indicator ('N', 'S', 'E', 'W')

    Example:
        >>> lat = Coordinate(48.1234, 'N')
        >>> print(lat.degrees_minutes)
        4807.404
    """

    decimal_degrees: float
    hemisphere: Literal['N', 'S', 'E', 'W']

    def __post_init__(self):
        """Validate coordinate values after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate coordinate values are in valid range."""
        abs_value = abs(self.decimal_degrees)

        if self.hemisphere in ('N', 'S'):
            if abs_value > 90:
                raise CoordinateError(
                    f"Latitude {self.decimal_degrees} exceeds valid range [-90, 90]"
                )
        elif self.hemisphere in ('E', 'W'):
            if abs_value > 180:
                raise CoordinateError(
                    f"Longitude {self.decimal_degrees} exceeds valid range [-180, 180]"
                )
        else:
            raise CoordinateError(
                f"Invalid hemisphere '{self.hemisphere}'. Must be N, S, E, or W"
            )

    @property
    def degrees_minutes(self) -> float:
        """
        Convert to degrees and decimal minutes format (DDDMM.MMMM).

        Returns:
            Coordinate in DDDMM.MMMM format
        """
        abs_val = abs(self.decimal_degrees)
        degrees = int(abs_val)
        minutes = (abs_val - degrees) * 60.0
        return degrees * 100 + minutes

    @property
    def degrees_minutes_seconds(self) -> Tuple[int, int, float]:
        """
        Convert to degrees, minutes, seconds format.

        Returns:
            Tuple of (degrees, minutes, seconds)
        """
        abs_val = abs(self.decimal_degrees)
        degrees = int(abs_val)
        remaining = (abs_val - degrees) * 60.0
        minutes = int(remaining)
        seconds = (remaining - minutes) * 60.0
        return (degrees, minutes, seconds)

    @property
    def signed_decimal(self) -> float:
        """
        Get signed decimal degrees (negative for S/W).

        Returns:
            Signed decimal degrees
        """
        if self.hemisphere in ('S', 'W'):
            return -abs(self.decimal_degrees)
        return abs(self.decimal_degrees)

    @classmethod
    def from_nmea(cls, nmea_value: str, direction: str) -> 'Coordinate':
        """
        Create Coordinate from NMEA format (DDDMM.MMMM).

        Args:
            nmea_value: Coordinate value in NMEA format
            direction: Hemisphere indicator (N/S/E/W)

        Returns:
            Coordinate instance

        Example:
            >>> coord = Coordinate.from_nmea('4807.404', 'N')
            >>> print(coord.decimal_degrees)
            48.1234
        """
        try:
            value = float(nmea_value)

            # Extract degrees (everything before last 2 digits of integer part)
            degrees = int(value / 100)

            # Extract minutes (last 2 digits + decimal part)
            minutes = value - (degrees * 100)

            # Convert to decimal degrees
            decimal = degrees + minutes / 60.0

            return cls(decimal, direction)
        except (ValueError, TypeError) as e:
            raise CoordinateError(f"Invalid NMEA value '{nmea_value}': {e}")

    @classmethod
    def from_scaled(cls, scaled_value: float, hemisphere: str, scale: int = 100000) -> 'Coordinate':
        """
        Create Coordinate from scaled integer format.

        Args:
            scaled_value: Coordinate multiplied by scale factor
            hemisphere: Hemisphere indicator (N/S/E/W)
            scale: Scale factor (default: 100000)

        Returns:
            Coordinate instance
        """
        decimal = float(scaled_value) / scale
        return cls(decimal, hemisphere)

    def to_nmea_string(self, lat_format: bool = True) -> str:
        """
        Format coordinate as NMEA string.

        Args:
            lat_format: If True, use latitude format (DDMM.MMMM), else longitude (DDDMM.MMMM)

        Returns:
            Formatted NMEA coordinate string
        """
        dm = self.degrees_minutes
        if lat_format:
            return f"{dm:07.4f}"  # DDMM.MMMM
        else:
            return f"{dm:08.4f}"  # DDDMM.MMMM

    def __str__(self) -> str:
        """String representation."""
        dms = self.degrees_minutes_seconds
        return f"{dms[0]}° {dms[1]}' {dms[2]:.3f}\" {self.hemisphere}"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Coordinate({self.decimal_degrees}, '{self.hemisphere}')"


@dataclass
class Position:
    """
    Represents a geographic position with latitude and longitude.

    Attributes:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        altitude: Altitude in meters (optional)
    """

    latitude: Coordinate
    longitude: Coordinate
    altitude: float = 0.0

    @classmethod
    def from_decimal(cls, lat: float, lon: float, alt: float = 0.0) -> 'Position':
        """
        Create Position from decimal degrees.

        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            alt: Altitude in meters

        Returns:
            Position instance
        """
        lat_hem = 'N' if lat >= 0 else 'S'
        lon_hem = 'E' if lon >= 0 else 'W'

        return cls(
            Coordinate(abs(lat), lat_hem),
            Coordinate(abs(lon), lon_hem),
            alt
        )

    @classmethod
    def from_nmea(cls, lat_str: str, lat_dir: str, lon_str: str, lon_dir: str, alt: float = 0.0) -> 'Position':
        """
        Create Position from NMEA format strings.

        Args:
            lat_str: Latitude in NMEA format
            lat_dir: Latitude direction (N/S)
            lon_str: Longitude in NMEA format
            lon_dir: Longitude direction (E/W)
            alt: Altitude in meters

        Returns:
            Position instance
        """
        return cls(
            Coordinate.from_nmea(lat_str, lat_dir),
            Coordinate.from_nmea(lon_str, lon_dir),
            alt
        )

    def to_decimal_tuple(self) -> Tuple[float, float, float]:
        """
        Get position as tuple of signed decimal degrees.

        Returns:
            Tuple of (latitude, longitude, altitude)
        """
        return (
            self.latitude.signed_decimal,
            self.longitude.signed_decimal,
            self.altitude
        )

    def distance_to(self, other: 'Position') -> float:
        """
        Calculate great circle distance to another position using Haversine formula.

        Args:
            other: Target position

        Returns:
            Distance in kilometers
        """
        R = 6371.0  # Earth radius in km

        lat1 = math.radians(self.latitude.signed_decimal)
        lon1 = math.radians(self.longitude.signed_decimal)
        lat2 = math.radians(other.latitude.signed_decimal)
        lon2 = math.radians(other.longitude.signed_decimal)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def __str__(self) -> str:
        """String representation."""
        return f"Position({self.latitude}, {self.longitude}, {self.altitude}m)"


class CoordinateConverter:
    """Utility class for various coordinate conversions."""

    @staticmethod
    def decimal_to_dms(decimal: float) -> Tuple[int, int, float]:
        """
        Convert decimal degrees to degrees, minutes, seconds.

        Args:
            decimal: Decimal degrees

        Returns:
            Tuple of (degrees, minutes, seconds)
        """
        abs_val = abs(decimal)
        degrees = int(abs_val)
        remaining = (abs_val - degrees) * 60.0
        minutes = int(remaining)
        seconds = (remaining - minutes) * 60.0
        return (degrees, minutes, seconds)

    @staticmethod
    def dms_to_decimal(degrees: int, minutes: int, seconds: float) -> float:
        """
        Convert degrees, minutes, seconds to decimal degrees.

        Args:
            degrees: Degrees
            minutes: Minutes
            seconds: Seconds

        Returns:
            Decimal degrees
        """
        return degrees + minutes / 60.0 + seconds / 3600.0

    @staticmethod
    def validate_latitude(lat: float) -> bool:
        """Check if latitude is in valid range."""
        return -90.0 <= lat <= 90.0

    @staticmethod
    def validate_longitude(lon: float) -> bool:
        """Check if longitude is in valid range."""
        return -180.0 <= lon <= 180.0


if __name__ == "__main__":
    # Test coordinate system
    print("=== Testing Coordinate System ===\n")

    # Create coordinates
    lat = Coordinate(48.1234, 'N')
    lon = Coordinate(11.5678, 'E')

    print(f"Decimal: {lat.decimal_degrees}° {lat.hemisphere}")
    print(f"Degrees Minutes: {lat.degrees_minutes}")
    print(f"DMS: {lat}")
    print()

    # Create from NMEA
    lat_nmea = Coordinate.from_nmea('4807.404', 'N')
    print(f"From NMEA '4807.404': {lat_nmea.decimal_degrees}°")
    print()

    # Create position
    pos1 = Position.from_decimal(48.1234, 11.5678, 100.0)
    pos2 = Position.from_decimal(48.2000, 11.6000, 150.0)

    print(f"Position 1: {pos1}")
    print(f"Position 2: {pos2}")
    print(f"Distance: {pos1.distance_to(pos2):.2f} km")
