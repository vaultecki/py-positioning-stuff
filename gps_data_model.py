"""
GPS Data Model - Manages GPS position data.
Part of MVC architecture for GPS Position System.
"""

import logging
from collections import deque
from typing import List, Callable, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


@dataclass
class GPSPosition:
    """
    Represents a single GPS position reading.

    Attributes:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        altitude: Altitude in meters
        timestamp: Time of reading
        speed: Speed in m/s (optional)
        course: Course in degrees (optional)
        satellites: Number of satellites (optional)
        quality: GPS fix quality indicator (optional)
    """
    latitude: float
    longitude: float
    altitude: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    speed: Optional[float] = None
    course: Optional[float] = None
    satellites: Optional[int] = None
    quality: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert position to dictionary."""
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude,
            'timestamp': self.timestamp.isoformat(),
            'speed': self.speed,
            'course': self.course,
            'satellites': self.satellites,
            'quality': self.quality
        }

    def distance_to(self, other: 'GPSPosition') -> float:
        """
        Calculate distance to another position using Haversine formula.

        Args:
            other: Target position

        Returns:
            Distance in meters
        """
        import math

        R = 6371000  # Earth radius in meters

        lat1 = math.radians(self.latitude)
        lon1 = math.radians(self.longitude)
        lat2 = math.radians(other.latitude)
        lon2 = math.radians(other.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c


class GPSDataModel:
    """
    Model for GPS position data.

    Manages GPS positions with observer pattern for updates.
    Thread-safe for concurrent access.
    """

    def __init__(self, max_positions: int = 1000):
        """
        Initialize GPS data model.

        Args:
            max_positions: Maximum number of positions to store
        """
        self.max_positions = max_positions
        self._positions = deque(maxlen=max_positions)
        self._observers: List[Callable[[GPSPosition], None]] = []
        self._lock = threading.RLock()
        self._stats = {
            'total_received': 0,
            'total_distance': 0.0,
            'average_speed': 0.0
        }

        logger.info(f"GPS Data Model initialized (max positions: {max_positions})")

    def add_position(self, position: GPSPosition) -> None:
        """
        Add new GPS position.

        Args:
            position: GPS position to add
        """
        with self._lock:
            # Calculate distance if we have a previous position
            if len(self._positions) > 0:
                prev_pos = self._positions[-1]
                distance = prev_pos.distance_to(position)
                self._stats['total_distance'] += distance

                # Calculate speed if not provided
                if position.speed is None:
                    time_diff = (position.timestamp - prev_pos.timestamp).total_seconds()
                    if time_diff > 0:
                        position.speed = distance / time_diff

            self._positions.append(position)
            self._stats['total_received'] += 1

            # Update average speed
            if position.speed is not None:
                speeds = [p.speed for p in self._positions if p.speed is not None]
                if speeds:
                    self._stats['average_speed'] = sum(speeds) / len(speeds)

            logger.debug(f"Added position: {position.latitude:.6f}, {position.longitude:.6f}")

        # Notify observers outside lock to prevent deadlock
        self._notify_observers(position)

    def get_positions(self, count: Optional[int] = None) -> List[GPSPosition]:
        """
        Get stored positions.

        Args:
            count: Number of recent positions to return (None for all)

        Returns:
            List of GPS positions
        """
        with self._lock:
            if count is None:
                return list(self._positions)
            else:
                return list(self._positions)[-count:]

    def get_latest_position(self) -> Optional[GPSPosition]:
        """
        Get most recent position.

        Returns:
            Latest GPS position or None if no positions
        """
        with self._lock:
            return self._positions[-1] if self._positions else None

    def get_position_count(self) -> int:
        """Get number of stored positions."""
        with self._lock:
            return len(self._positions)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about GPS data.

        Returns:
            Dictionary with statistics
        """
        with self._lock:
            stats = self._stats.copy()
            stats['stored_positions'] = len(self._positions)

            if self._positions:
                stats['first_timestamp'] = self._positions[0].timestamp
                stats['last_timestamp'] = self._positions[-1].timestamp

                # Calculate time span
                time_span = (self._positions[-1].timestamp -
                             self._positions[0].timestamp).total_seconds()
                stats['time_span_seconds'] = time_span

            return stats

    def clear(self) -> None:
        """Clear all stored positions."""
        with self._lock:
            self._positions.clear()
            self._stats['total_distance'] = 0.0
            self._stats['average_speed'] = 0.0
            logger.info("GPS data cleared")

    def register_observer(self, callback: Callable[[GPSPosition], None]) -> None:
        """
        Register observer for position updates.

        Args:
            callback: Function to call when new position is added
        """
        with self._lock:
            if callback not in self._observers:
                self._observers.append(callback)
                logger.debug(f"Observer registered: {callback.__name__}")

    def unregister_observer(self, callback: Callable[[GPSPosition], None]) -> None:
        """
        Unregister observer.

        Args:
            callback: Observer to remove
        """
        with self._lock:
            if callback in self._observers:
                self._observers.remove(callback)
                logger.debug(f"Observer unregistered: {callback.__name__}")

    def _notify_observers(self, position: GPSPosition) -> None:
        """
        Notify all observers of new position.

        Args:
            position: New GPS position
        """
        # Create copy of observers list to avoid issues during iteration
        with self._lock:
            observers = self._observers.copy()

        for observer in observers:
            try:
                observer(position)
            except Exception as e:
                logger.error(f"Error notifying observer {observer.__name__}: {e}")

    def get_latitude_data(self) -> List[float]:
        """Get list of latitude values."""
        with self._lock:
            return [pos.latitude for pos in self._positions]

    def get_longitude_data(self) -> List[float]:
        """Get list of longitude values."""
        with self._lock:
            return [pos.longitude for pos in self._positions]

    def get_altitude_data(self) -> List[float]:
        """Get list of altitude values."""
        with self._lock:
            return [pos.altitude for pos in self._positions]

    def get_timestamps(self) -> List[datetime]:
        """Get list of timestamps."""
        with self._lock:
            return [pos.timestamp for pos in self._positions]

    def export_to_dict_list(self) -> List[Dict[str, Any]]:
        """
        Export all positions as list of dictionaries.

        Returns:
            List of position dictionaries
        """
        with self._lock:
            return [pos.to_dict() for pos in self._positions]


class GPSTrack:
    """
    Represents a GPS track with multiple positions.

    Provides analysis and statistics for a sequence of GPS positions.
    """

    def __init__(self, name: str = "GPS Track"):
        """
        Initialize GPS track.

        Args:
            name: Track name
        """
        self.name = name
        self.positions: List[GPSPosition] = []
        self.created_at = datetime.now()

    def add_position(self, position: GPSPosition) -> None:
        """Add position to track."""
        self.positions.append(position)

    def get_total_distance(self) -> float:
        """
        Calculate total track distance.

        Returns:
            Total distance in meters
        """
        if len(self.positions) < 2:
            return 0.0

        total = 0.0
        for i in range(1, len(self.positions)):
            total += self.positions[i - 1].distance_to(self.positions[i])

        return total

    def get_duration(self) -> float:
        """
        Get track duration.

        Returns:
            Duration in seconds
        """
        if len(self.positions) < 2:
            return 0.0

        return (self.positions[-1].timestamp -
                self.positions[0].timestamp).total_seconds()

    def get_average_speed(self) -> float:
        """
        Calculate average speed.

        Returns:
            Average speed in m/s
        """
        duration = self.get_duration()
        if duration == 0:
            return 0.0

        return self.get_total_distance() / duration

    def get_bounds(self) -> Dict[str, float]:
        """
        Get bounding box of track.

        Returns:
            Dictionary with min/max lat/lon
        """
        if not self.positions:
            return {'min_lat': 0, 'max_lat': 0, 'min_lon': 0, 'max_lon': 0}

        lats = [p.latitude for p in self.positions]
        lons = [p.longitude for p in self.positions]

        return {
            'min_lat': min(lats),
            'max_lat': max(lats),
            'min_lon': min(lons),
            'max_lon': max(lons)
        }


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)

    print("=== Testing GPS Data Model ===\n")

    # Create model
    model = GPSDataModel(max_positions=100)


    # Add observer
    def on_new_position(pos: GPSPosition):
        print(f"New position: {pos.latitude:.6f}, {pos.longitude:.6f}")


    model.register_observer(on_new_position)

    # Add positions
    pos1 = GPSPosition(48.0, 11.0, 100.0)
    pos2 = GPSPosition(48.1, 11.1, 110.0)
    pos3 = GPSPosition(48.2, 11.2, 120.0)

    model.add_position(pos1)
    model.add_position(pos2)
    model.add_position(pos3)

    # Get statistics
    print("\nStatistics:")
    stats = model.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Test track
    print("\n=== Testing GPS Track ===\n")
    track = GPSTrack("Test Track")
    track.add_position(pos1)
    track.add_position(pos2)
    track.add_position(pos3)

    print(f"Track: {track.name}")
    print(f"Distance: {track.get_total_distance():.2f} m")
    print(f"Duration: {track.get_duration():.2f} s")
    print(f"Avg Speed: {track.get_average_speed():.2f} m/s")
    print(f"Bounds: {track.get_bounds()}")
