"""
Improved GPS MAT file player.
Reads and plays back GPS data from MATLAB files with proper error handling.
"""

import threading
import time
import logging
from typing import Optional, Callable
import scipy.io
import os

try:
    import PySignal
except ImportError:
    # Fallback if PySignal not available
    class ClassSignal:
        def __init__(self):
            self.callbacks = []

        def connect(self, callback):
            if callback not in self.callbacks:
                self.callbacks.append(callback)

        def emit(self, *args, **kwargs):
            for callback in self.callbacks:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logging.error(f"Error in signal callback: {e}")


    class PySignal:
        ClassSignal = ClassSignal

logger = logging.getLogger(__name__)


class GPSDataError(Exception):
    """Raised when GPS data loading or processing fails."""
    pass


class PlayGPSMat:
    """
    Plays back GPS position data from MATLAB .mat files.

    Reads Easting/Northing coordinates and emits them at specified intervals.
    Thread-safe with proper error handling.
    """

    new_gps_pos = PySignal.ClassSignal()

    def __init__(self, filename: str, start_timeout: float = 5.0,
                 time_between_gps_pos: float = 1.0):
        """
        Initialize GPS MAT player.

        Args:
            filename: Path to .mat file containing GPS data
            start_timeout: Delay before starting playback (seconds)
            time_between_gps_pos: Time between position emissions (seconds)

        Raises:
            FileNotFoundError: If MAT file doesn't exist
            GPSDataError: If MAT file format is invalid
        """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"GPS data file not found: {filename}")

        self.filename = filename
        self.timeout = time_between_gps_pos
        self.start_timeout = start_timeout

        # Load and validate GPS data
        try:
            self.gps_data = scipy.io.loadmat(filename)
            self._validate_gps_data()
            logger.info(f"Loaded GPS data from: {filename}")
        except Exception as e:
            raise GPSDataError(f"Failed to load GPS data: {e}")

        # Playback control
        self._playing = False
        self._paused = False
        self._current_index = 0
        self._playback_thread: Optional[threading.Thread] = None

        # Statistics
        self.positions_sent = 0

        # Start playback timer
        if start_timeout > 0:
            timer = threading.Timer(start_timeout, self.start)
            timer.daemon = True
            timer.start()
            logger.info(f"Playback will start in {start_timeout} seconds")
        else:
            self.start()

    def _validate_gps_data(self) -> None:
        """
        Validate loaded GPS data structure.

        Raises:
            GPSDataError: If required fields are missing or invalid
        """
        # Check for required fields
        if 'Easting' not in self.gps_data:
            raise GPSDataError("GPS data missing 'Easting' field")

        if 'Northing' not in self.gps_data:
            raise GPSDataError("GPS data missing 'Northing' field")

        # Get coordinate arrays
        easting = self.gps_data['Easting']
        northing = self.gps_data['Northing']

        # Validate shapes
        if easting.shape != northing.shape:
            raise GPSDataError(
                f"Easting and Northing arrays have different shapes: "
                f"{easting.shape} vs {northing.shape}"
            )

        if easting.size == 0:
            raise GPSDataError("GPS data arrays are empty")

        logger.info(f"GPS data validated: {easting.size} positions")

    def start(self) -> None:
        """Start GPS data playback."""
        if self._playing:
            logger.warning("Playback already started")
            return

        self._playing = True
        self._paused = False

        # Start playback thread
        self._playback_thread = threading.Thread(
            target=self._playback_loop,
            daemon=True
        )
        self._playback_thread.start()

        logger.info("GPS playback started")

    def stop(self) -> None:
        """Stop GPS data playback."""
        self._playing = False
        self._paused = False

        if self._playback_thread:
            self._playback_thread.join(timeout=2.0)

        logger.info("GPS playback stopped")

    def pause(self) -> None:
        """Pause GPS data playback."""
        self._paused = True
        logger.info("GPS playback paused")

    def resume(self) -> None:
        """Resume GPS data playback."""
        self._paused = False
        logger.info("GPS playback resumed")

    def reset(self) -> None:
        """Reset playback to beginning."""
        self._current_index = 0
        self.positions_sent = 0
        logger.info("GPS playback reset")

    def _playback_loop(self) -> None:
        """Main playback loop (runs in separate thread)."""
        try:
            easting = self.gps_data['Easting']
            northing = self.gps_data['Northing']

            # Flatten arrays if needed
            if easting.ndim > 1:
                easting = easting.flatten()
            if northing.ndim > 1:
                northing = northing.flatten()

            total_positions = len(easting)

            for i in range(self._current_index, total_positions):
                # Check if stopped
                if not self._playing:
                    break

                # Handle pause
                while self._paused and self._playing:
                    time.sleep(0.1)

                if not self._playing:
                    break

                # Get current position
                try:
                    east = float(easting[i])
                    north = float(northing[i])

                    # Emit position
                    self.new_gps_pos.emit(east, north)
                    self.positions_sent += 1
                    self._current_index = i

                    logger.debug(f"Position {i + 1}/{total_positions}: "
                                 f"E={east:.2f}, N={north:.2f}")

                except Exception as e:
                    logger.error(f"Error emitting position {i}: {e}")

                # Wait before next position
                time.sleep(self.timeout)

            logger.info(f"GPS playback completed: {self.positions_sent} positions sent")
            self._playing = False

        except Exception as e:
            logger.error(f"Error in playback loop: {e}", exc_info=True)
            self._playing = False

    def get_statistics(self) -> dict:
        """
        Get playback statistics.

        Returns:
            Dictionary with playback statistics
        """
        easting = self.gps_data.get('Easting', [])
        if hasattr(easting, 'size'):
            total = easting.size
        else:
            total = len(easting)

        return {
            'filename': self.filename,
            'total_positions': total,
            'positions_sent': self.positions_sent,
            'current_index': self._current_index,
            'is_playing': self._playing,
            'is_paused': self._paused,
            'progress_percent': (self._current_index / total * 100) if total > 0 else 0
        }

    def get_position_at(self, index: int) -> tuple:
        """
        Get position at specific index.

        Args:
            index: Position index

        Returns:
            Tuple of (easting, northing)

        Raises:
            IndexError: If index is out of range
        """
        easting = self.gps_data['Easting']
        northing = self.gps_data['Northing']

        if easting.ndim > 1:
            easting = easting.flatten()
        if northing.ndim > 1:
            northing = northing.flatten()

        if not (0 <= index < len(easting)):
            raise IndexError(f"Position index {index} out of range [0, {len(easting)})")

        return (float(easting[index]), float(northing[index]))

    def __del__(self):
        """Cleanup on deletion."""
        if self._playing:
            self.stop()


# Callback example for testing
def example_position_callback(easting: float, northing: float) -> None:
    """Example callback for position updates."""
    print(f"New position - Easting: {easting:.2f}, Northing: {northing:.2f}")


def main():
    """Test GPS MAT player."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test file path
    filename = os.path.join(os.getcwd(), "data/AguasVivasGPSData.mat")

    if not os.path.exists(filename):
        logger.error(f"Test file not found: {filename}")
        return 1

    try:
        # Create player
        player = PlayGPSMat(
            filename,
            start_timeout=2.0,
            time_between_gps_pos=0.5
        )

        # Connect callback
        player.new_gps_pos.connect(example_position_callback)

        # Let it run for a while
        time.sleep(10)

        # Print statistics
        stats = player.get_statistics()
        print("\nPlayback Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

        # Stop playback
        player.stop()

        return 0

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
