"""
NMEA sentence validation and parsing utilities.
Provides robust validation and error handling for NMEA data.
"""

import re
import logging
from typing import Optional, Dict, Any
import pynmea2

logger = logging.getLogger(__name__)


class NMEAValidationError(Exception):
    """Raised when NMEA sentence validation fails."""
    pass


class NMEAValidator:
    """
    Validates and parses NMEA sentences.

    Provides checksum validation, format checking, and safe parsing
    with detailed error reporting.
    """

    # NMEA sentence pattern: $XXYYY,data*CC
    NMEA_PATTERN = re.compile(
        r'^\$[A-Z]{2}[A-Z]{3},[^*]*\*[0-9A-F]{2}$',
        re.IGNORECASE
    )

    # Supported sentence types for GPS
    SUPPORTED_SENTENCES = {
        'GPRMC',  # Recommended Minimum Specific GPS/Transit Data
        'GPGGA',  # Global Positioning System Fix Data
        'GPGLL',  # Geographic Position - Latitude/Longitude
        'GPGSA',  # GPS DOP and Active Satellites
        'GPGSV',  # GPS Satellites in View
        'GPVTG',  # Track Made Good and Ground Speed
    }

    @staticmethod
    def calculate_checksum(sentence: str) -> str:
        """
        Calculate NMEA checksum for sentence.

        Args:
            sentence: NMEA sentence without $ and *checksum

        Returns:
            Two-character hex checksum

        Example:
            >>> NMEAValidator.calculate_checksum('GPRMC,123456.00,A,4807.404,N')
            '3F'
        """
        checksum = 0
        for char in sentence:
            checksum ^= ord(char)
        return f"{checksum:02X}"

    @staticmethod
    def validate_checksum(nmea_string: str) -> bool:
        """
        Verify NMEA sentence checksum.

        Args:
            nmea_string: Complete NMEA sentence with checksum

        Returns:
            True if checksum is valid

        Example:
            >>> NMEAValidator.validate_checksum('$GPRMC,data*3F')
            True
        """
        if '*' not in nmea_string:
            logger.warning("NMEA sentence missing checksum")
            return False

        try:
            # Split sentence and checksum
            sentence, provided_checksum = nmea_string.split('*')

            # Remove leading $
            if sentence.startswith('$'):
                sentence = sentence[1:]

            # Calculate expected checksum
            calculated_checksum = NMEAValidator.calculate_checksum(sentence)

            # Compare (case-insensitive)
            return calculated_checksum.upper() == provided_checksum.upper()

        except ValueError as e:
            logger.error(f"Error parsing checksum: {e}")
            return False

    @staticmethod
    def validate_format(nmea_string: str) -> bool:
        """
        Validate NMEA sentence format.

        Args:
            nmea_string: NMEA sentence to validate

        Returns:
            True if format is valid
        """
        return bool(NMEAValidator.NMEA_PATTERN.match(nmea_string.strip()))

    @staticmethod
    def get_sentence_type(nmea_string: str) -> Optional[str]:
        """
        Extract sentence type from NMEA string.

        Args:
            nmea_string: NMEA sentence

        Returns:
            Sentence type (e.g., 'GPRMC') or None if invalid
        """
        try:
            if nmea_string.startswith('$'):
                # Extract sentence type (first 6 characters after $)
                return nmea_string[1:7].upper()
        except IndexError:
            pass
        return None

    @staticmethod
    def is_supported_sentence(nmea_string: str) -> bool:
        """
        Check if sentence type is supported.

        Args:
            nmea_string: NMEA sentence

        Returns:
            True if sentence type is supported
        """
        sentence_type = NMEAValidator.get_sentence_type(nmea_string)
        return sentence_type in NMEAValidator.SUPPORTED_SENTENCES

    @staticmethod
    def is_valid_nmea(nmea_string: str, check_checksum: bool = True) -> bool:
        """
        Comprehensive NMEA sentence validation.

        Args:
            nmea_string: NMEA sentence to validate
            check_checksum: Whether to verify checksum

        Returns:
            True if sentence is valid
        """
        # Check format
        if not NMEAValidator.validate_format(nmea_string):
            logger.debug(f"Invalid NMEA format: {nmea_string}")
            return False

        # Check checksum if requested
        if check_checksum and not NMEAValidator.validate_checksum(nmea_string):
            logger.debug(f"Invalid NMEA checksum: {nmea_string}")
            return False

        return True

    @staticmethod
    def safe_parse(nmea_string: str, validate: bool = True) -> Optional[pynmea2.NMEASentence]:
        """
        Safely parse NMEA sentence with validation.

        Args:
            nmea_string: NMEA sentence to parse
            validate: Whether to validate before parsing

        Returns:
            Parsed NMEA sentence object or None if parsing fails
        """
        try:
            # Validate if requested
            if validate and not NMEAValidator.is_valid_nmea(nmea_string):
                logger.warning(f"NMEA validation failed: {nmea_string}")
                return None

            # Parse sentence
            parsed = pynmea2.parse(nmea_string.strip())

            # Additional validation for position data
            if hasattr(parsed, 'latitude') and hasattr(parsed, 'longitude'):
                if not NMEAValidator._validate_position_data(parsed):
                    logger.warning(f"Invalid position data in NMEA: {nmea_string}")
                    return None

            return parsed

        except pynmea2.ParseError as e:
            logger.error(f"NMEA parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing NMEA: {e}")
            return None

    @staticmethod
    def _validate_position_data(parsed: pynmea2.NMEASentence) -> bool:
        """
        Validate position data in parsed NMEA sentence.

        Args:
            parsed: Parsed NMEA sentence

        Returns:
            True if position data is valid
        """
        try:
            # Check if position fields exist
            if not hasattr(parsed, 'latitude') or not hasattr(parsed, 'longitude'):
                return True  # No position data to validate

            # Get latitude and longitude
            lat = parsed.latitude
            lon = parsed.longitude

            # Check for None values
            if lat is None or lon is None:
                return False

            # Validate ranges
            if not (-90.0 <= lat <= 90.0):
                logger.warning(f"Latitude out of range: {lat}")
                return False

            if not (-180.0 <= lon <= 180.0):
                logger.warning(f"Longitude out of range: {lon}")
                return False

            return True

        except (AttributeError, TypeError, ValueError) as e:
            logger.error(f"Error validating position data: {e}")
            return False

    @staticmethod
    def extract_position_info(parsed: pynmea2.NMEASentence) -> Optional[Dict[str, Any]]:
        """
        Extract position information from parsed NMEA sentence.

        Args:
            parsed: Parsed NMEA sentence

        Returns:
            Dictionary with position info or None if not available
        """
        if not hasattr(parsed, 'latitude') or not hasattr(parsed, 'longitude'):
            return None

        try:
            info = {
                'latitude': parsed.latitude,
                'longitude': parsed.longitude,
                'lat_dir': getattr(parsed, 'lat_dir', 'N'),
                'lon_dir': getattr(parsed, 'lon_dir', 'E'),
            }

            # Add optional fields if available
            if hasattr(parsed, 'timestamp'):
                info['timestamp'] = parsed.timestamp

            if hasattr(parsed, 'altitude'):
                info['altitude'] = parsed.altitude

            if hasattr(parsed, 'num_sats'):
                info['num_satellites'] = parsed.num_sats

            if hasattr(parsed, 'gps_qual'):
                info['gps_quality'] = parsed.gps_qual

            return info

        except Exception as e:
            logger.error(f"Error extracting position info: {e}")
            return None


class NMEAGenerator:
    """Generate valid NMEA sentences."""

    @staticmethod
    def generate_rmc(latitude: float, longitude: float,
                     timestamp: Optional[Any] = None,
                     speed: float = 0.0, course: float = 0.0,
                     date: Optional[Any] = None) -> str:
        """
        Generate GPRMC (Recommended Minimum) sentence.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            timestamp: Time (datetime object or None for current)
            speed: Speed over ground in knots
            course: Course over ground in degrees
            date: Date (datetime object or None for current)

        Returns:
            Complete NMEA RMC sentence with checksum
        """
        import datetime

        if timestamp is None:
            timestamp = datetime.datetime.utcnow()
        if date is None:
            date = datetime.datetime.utcnow()

        # Convert coordinates to NMEA format
        lat_deg = int(abs(latitude))
        lat_min = (abs(latitude) - lat_deg) * 60
        lat_nmea = f"{lat_deg:02d}{lat_min:07.4f}"
        lat_dir = 'N' if latitude >= 0 else 'S'

        lon_deg = int(abs(longitude))
        lon_min = (abs(longitude) - lon_deg) * 60
        lon_nmea = f"{lon_deg:03d}{lon_min:07.4f}"
        lon_dir = 'E' if longitude >= 0 else 'W'

        # Format time and date
        time_str = timestamp.strftime("%H%M%S.%f")[:9]
        date_str = date.strftime("%d%m%y")

        # Build sentence (without $ and checksum)
        sentence = (f"GPRMC,{time_str},A,{lat_nmea},{lat_dir},{lon_nmea},{lon_dir},"
                    f"{speed:.1f},{course:.1f},{date_str},,A")

        # Calculate and append checksum
        checksum = NMEAValidator.calculate_checksum(sentence)

        return f"${sentence}*{checksum}"


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)

    print("=== Testing NMEA Validator ===\n")

    # Test valid NMEA sentence
    valid_nmea = "$GPRMC,123456.00,A,4807.404,N,01131.324,E,0.0,0.0,191124,,,A*6C"
    print(f"Testing: {valid_nmea}")
    print(f"Format valid: {NMEAValidator.validate_format(valid_nmea)}")
    print(f"Checksum valid: {NMEAValidator.validate_checksum(valid_nmea)}")
    print(f"Is valid: {NMEAValidator.is_valid_nmea(valid_nmea)}")

    # Parse sentence
    parsed = NMEAValidator.safe_parse(valid_nmea)
    if parsed:
        print(f"Parsed successfully: {parsed}")
        info = NMEAValidator.extract_position_info(parsed)
        print(f"Position info: {info}")
    print()

    # Test invalid checksum
    invalid_checksum = "$GPRMC,123456.00,A,4807.404,N,01131.324,E,0.0,0.0,191124,,,A*FF"
    print(f"Testing invalid checksum: {invalid_checksum}")
    print(f"Is valid: {NMEAValidator.is_valid_nmea(invalid_checksum)}")
    print()

    # Generate NMEA sentence
    generated = NMEAGenerator.generate_rmc(48.1234, 11.5678)
    print(f"Generated NMEA: {generated}")
    print(f"Generated is valid: {NMEAValidator.is_valid_nmea(generated)}")
