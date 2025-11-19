"""
Improved GPS Position Sender.
Sends GPS positions as NMEA sentences via UDP with proper error handling.
"""

import os
import logging
import datetime
from typing import Tuple

try:
    from config_loader import get_config
    from coordinates import Coordinate, Position
    from nmea_validator import NMEAGenerator
    from gps_data_mat_play import PlayGPSMat
    import bert_utils.helper_udp
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all required modules are in the Python path")
    raise

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SendNmeaError(Exception):
    """Raised when NMEA sending fails."""
    pass


class SendNmea:
    """
    Sends GPS positions as NMEA sentences via UDP.

    Reads GPS data from MAT file and broadcasts as NMEA RMC sentences.
    """

    def __init__(self):
        """Initialize NMEA sender with configuration."""
        self.config = get_config()

        # Load configuration
        data_file = self.config.get('gps.data_file', 'data/AguasVivasGPSData.mat')
        filename = os.path.join(os.getcwd(), data_file)

        if not os.path.exists(filename):
            raise FileNotFoundError(f"GPS data file not found: {filename}")

        logger.info(f"Loading GPS data from: {filename}")

        # Initialize GPS data player
        start_timeout = self.config.get('gps.start_timeout', 5)
        time_between = self.config.get('gps.time_between_positions', 1.0)

        self.gps_mat = PlayGPSMat(
            filename,
            start_timeout=start_timeout,
            time_between_gps_pos=time_between
        )

        # Connect signal
        self.gps_mat.new_gps_pos.connect(self.on_new_pos)

        # Initialize UDP socket
        udp_addr = self.config.get('network.udp_address', '127.0.0.1')
        udp_port = self.config.get('network.udp_port', 19711)
        recv_port = self.config.get('network.receive_port', 19710)

        logger.info(f"Sending to: {udp_addr}:{udp_port}")

        try:
            self.sock = bert_utils.helper_udp.UDPSocketClass(
                addr=[[udp_addr, udp_port]],
                recv_port=recv_port
            )
        except Exception as e:
            raise SendNmeaError(f"Failed to initialize UDP socket: {e}")

        self.position_count = 0
        logger.info("SendNmea initialized successfully")

    def on_new_pos(self, easting: float, northing: float) -> None:
        """
        Handle new GPS position from MAT file.

        Args:
            easting: Easting coordinate (scaled)
            northing: Northing coordinate (scaled)
        """
        try:
            # Convert scaled values to decimal degrees
            # Assuming the values are scaled by 100000
            lat_decimal = float(northing) / 100000.0
            lon_decimal = float(easting) / 100000.0

            # Validate coordinates
            if not (-90 <= lat_decimal <= 90):
                logger.warning(f"Invalid latitude: {lat_decimal}")
                return

            if not (-180 <= lon_decimal <= 180):
                logger.warning(f"Invalid longitude: {lon_decimal}")
                return

            # Generate NMEA sentence
            nmea_str = self.generate_nmea(lat_decimal, lon_decimal)

            # Send via UDP
            self.send_nmea(nmea_str)

            self.position_count += 1
            logger.info(f"Sent position #{self.position_count}: "
                        f"Lat={lat_decimal:.6f}, Lon={lon_decimal:.6f}")

        except Exception as e:
            logger.error(f"Error processing new position: {e}", exc_info=True)

    def generate_nmea(self, latitude: float, longitude: float) -> str:
        """
        Generate NMEA RMC sentence from coordinates.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees

        Returns:
            Complete NMEA RMC sentence with checksum
        """
        try:
            # Use NMEAGenerator for proper formatting
            nmea_sentence = NMEAGenerator.generate_rmc(
                latitude=latitude,
                longitude=longitude,
                timestamp=datetime.datetime.utcnow(),
                speed=0.0,  # Could be calculated from position changes
                course=0.0,
                date=datetime.datetime.utcnow()
            )

            logger.debug(f"Generated NMEA: {nmea_sentence}")
            return nmea_sentence

        except Exception as e:
            logger.error(f"Error generating NMEA: {e}")
            raise SendNmeaError(f"NMEA generation failed: {e}")

    def send_nmea(self, nmea_string: str) -> None:
        """
        Send NMEA sentence via UDP.

        Args:
            nmea_string: NMEA sentence to send
        """
        try:
            self.sock.send_data(nmea_string)
            logger.debug(f"Sent NMEA: {nmea_string}")
        except Exception as e:
            logger.error(f"Error sending NMEA: {e}")
            raise SendNmeaError(f"UDP send failed: {e}")

    def get_statistics(self) -> dict:
        """
        Get sender statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            'positions_sent': self.position_count,
            'udp_address': self.config.get('network.udp_address'),
            'udp_port': self.config.get('network.udp_port')
        }


def main():
    """Main entry point."""
    try:
        logger.info("Starting GPS Position Sender...")
        sender = SendNmea()

        # Keep running
        logger.info("Sender is running. Press Ctrl+C to stop.")

        # In a real application, you might want to add a proper event loop
        # or signal handling here
        import time
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Sender stopped by user")
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
    except SendNmeaError as e:
        logger.error(f"Send error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
