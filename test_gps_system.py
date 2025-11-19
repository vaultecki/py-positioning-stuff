"""
Comprehensive test suite for GPS Position System.
Tests all major components with proper mocking and assertions.
"""

import pytest
import logging
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# Import modules to test
try:
    from coordinates import Coordinate, Position, CoordinateConverter, CoordinateError
    from nmea_validator import NMEAValidator, NMEAGenerator
    from gps_data_model import GPSDataModel, GPSPosition, GPSTrack
    from config_loader import Config
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all modules are in the Python path")
    raise

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)


class TestCoordinates:
    """Test suite for coordinate system."""

    def test_coordinate_creation(self):
        """Test basic coordinate creation."""
        lat = Coordinate(48.1234, 'N')
        assert lat.decimal_degrees == 48.1234
        assert lat.hemisphere == 'N'

    def test_coordinate_validation_latitude(self):
        """Test latitude range validation."""
        # Valid latitudes
        Coordinate(90.0, 'N')
        Coordinate(0.0, 'N')
        Coordinate(45.0, 'S')

        # Invalid latitude
        with pytest.raises(CoordinateError):
            Coordinate(91.0, 'N')

        with pytest.raises(CoordinateError):
            Coordinate(-91.0, 'S')

    def test_coordinate_validation_longitude(self):
        """Test longitude range validation."""
        # Valid longitudes
        Coordinate(180.0, 'E')
        Coordinate(0.0, 'E')
        Coordinate(90.0, 'W')

        # Invalid longitude
        with pytest.raises(CoordinateError):
            Coordinate(181.0, 'E')

    def test_coordinate_from_nmea(self):
        """Test NMEA format parsing."""
        # Latitude: 48°07.404' = 48.1234°
        lat = Coordinate.from_nmea('4807.404', 'N')
        assert abs(lat.decimal_degrees - 48.1234) < 0.0001

        # Longitude: 11°31.324' = 11.5221°
        lon = Coordinate.from_nmea('01131.324', 'E')
        assert abs(lon.decimal_degrees - 11.5221) < 0.0001

    def test_coordinate_to_degrees_minutes(self):
        """Test conversion to degrees/minutes format."""
        lat = Coordinate(48.1234, 'N')
        dm = lat.degrees_minutes

        # Should be 4807.404
        expected = 48 * 100 + 0.1234 * 60
        assert abs(dm - expected) < 0.01

    def test_coordinate_signed_decimal(self):
        """Test signed decimal conversion."""
        lat_n = Coordinate(48.0, 'N')
        assert lat_n.signed_decimal == 48.0

        lat_s = Coordinate(48.0, 'S')
        assert lat_s.signed_decimal == -48.0

        lon_e = Coordinate(11.0, 'E')
        assert lon_e.signed_decimal == 11.0

        lon_w = Coordinate(11.0, 'W')
        assert lon_w.signed_decimal == -11.0

    def test_position_creation(self):
        """Test position creation."""
        pos = Position.from_decimal(48.1234, 11.5678, 100.0)

        assert abs(pos.latitude.decimal_degrees - 48.1234) < 0.0001
        assert abs(pos.longitude.decimal_degrees - 11.5678) < 0.0001
        assert pos.altitude == 100.0

    def test_position_distance(self):
        """Test distance calculation between positions."""
        pos1 = Position.from_decimal(48.0, 11.0, 0.0)
        pos2 = Position.from_decimal(48.1, 11.0, 0.0)

        distance = pos1.distance_to(pos2)

        # Distance should be approximately 11.1 km
        assert 10.0 < distance < 12.0

    def test_coordinate_converter(self):
        """Test coordinate converter utilities."""
        # Test DMS conversion
        dms = CoordinateConverter.decimal_to_dms(48.1234)
        assert dms[0] == 48  # degrees
        assert abs(dms[1] - 7) < 1  # minutes
        assert abs(dms[2] - 24.24) < 1  # seconds

        # Test validation
        assert CoordinateConverter.validate_latitude(45.0)
        assert not CoordinateConverter.validate_latitude(95.0)
        assert CoordinateConverter.validate_longitude(170.0)
        assert not CoordinateConverter.validate_longitude(200.0)


class TestNMEAValidator:
    """Test suite for NMEA validation."""

    def test_checksum_calculation(self):
        """Test NMEA checksum calculation."""
        sentence = "GPRMC,123456.00,A,4807.404,N,01131.324,E,0.0,0.0,191124,,,A"
        checksum = NMEAValidator.calculate_checksum(sentence)

        # Should return 2-digit hex string
        assert len(checksum) == 2
        assert all(c in '0123456789ABCDEF' for c in checksum)

    def test_checksum_validation(self):
        """Test NMEA checksum validation."""
        valid_nmea = "$GPRMC,123456.00,A,4807.404,N,01131.324,E,0.0,0.0,191124,,,A*6C"
        assert NMEAValidator.validate_checksum(valid_nmea)

        invalid_nmea = "$GPRMC,123456.00,A,4807.404,N,01131.324,E,0.0,0.0,191124,,,A*FF"
        assert not NMEAValidator.validate_checksum(invalid_nmea)

    def test_format_validation(self):
        """Test NMEA format validation."""
        valid_nmea = "$GPRMC,123456.00,A,4807.404,N,01131.324,E,0.0,0.0,191124,,,A*6C"
        assert NMEAValidator.validate_format(valid_nmea)

        invalid_format = "GPRMC,123456.00,A,4807.404,N"
        assert not NMEAValidator.validate_format(invalid_format)

    def test_sentence_type_extraction(self):
        """Test sentence type extraction."""
        nmea = "$GPRMC,123456.00,A,4807.404,N,01131.324,E,0.0,0.0,191124,,,A*6C"
        sentence_type = NMEAValidator.get_sentence_type(nmea)
        assert sentence_type == "GPRMC"

    def test_safe_parse_valid(self):
        """Test safe parsing of valid NMEA."""
        nmea = "$GPRMC,123456.00,A,4807.404,N,01131.324,E,0.0,0.0,191124,,,A*6C"

        with patch('pynmea2.parse') as mock_parse:
            mock_parsed = Mock()
            mock_parsed.latitude = 48.1234
            mock_parsed.longitude = 11.5221
            mock_parse.return_value = mock_parsed

            result = NMEAValidator.safe_parse(nmea, validate=False)
            assert result is not None

    def test_safe_parse_invalid(self):
        """Test safe parsing of invalid NMEA."""
        invalid_nmea = "$INVALID*FF"
        result = NMEAValidator.safe_parse(invalid_nmea)

        # Should return None without raising exception
        assert result is None

    def test_nmea_generator(self):
        """Test NMEA sentence generation."""
        nmea = NMEAGenerator.generate_rmc(48.1234, 11.5678)

        # Should start with $GPRMC
        assert nmea.startswith('$GPRMC')

        # Should have valid checksum
        assert NMEAValidator.validate_checksum(nmea)

        # Should be valid format
        assert NMEAValidator.is_valid_nmea(nmea)


class TestGPSDataModel:
    """Test suite for GPS data model."""

    def test_model_creation(self):
        """Test model initialization."""
        model = GPSDataModel(max_positions=100)
        assert model.max_positions == 100
        assert model.get_position_count() == 0

    def test_add_position(self):
        """Test adding position to model."""
        model = GPSDataModel()
        pos = GPSPosition(48.0, 11.0, 100.0)

        model.add_position(pos)

        assert model.get_position_count() == 1
        assert model.get_latest_position() == pos

    def test_max_positions_limit(self):
        """Test maximum position limit."""
        model = GPSDataModel(max_positions=5)

        # Add more than max
        for i in range(10):
            pos = GPSPosition(48.0 + i * 0.01, 11.0, 0.0)
            model.add_position(pos)

        # Should only keep last 5
        assert model.get_position_count() == 5

    def test_observer_pattern(self):
        """Test observer notifications."""
        model = GPSDataModel()
        callback_called = []

        def observer(pos):
            callback_called.append(pos)

        model.register_observer(observer)

        pos = GPSPosition(48.0, 11.0, 100.0)
        model.add_position(pos)

        assert len(callback_called) == 1
        assert callback_called[0] == pos

    def test_get_statistics(self):
        """Test statistics calculation."""
        model = GPSDataModel()

        pos1 = GPSPosition(48.0, 11.0, 0.0, speed=10.0)
        pos2 = GPSPosition(48.1, 11.0, 0.0, speed=20.0)

        model.add_position(pos1)
        model.add_position(pos2)

        stats = model.get_statistics()

        assert stats['total_received'] == 2
        assert stats['stored_positions'] == 2
        assert stats['average_speed'] == 15.0

    def test_clear(self):
        """Test clearing model data."""
        model = GPSDataModel()

        pos = GPSPosition(48.0, 11.0, 100.0)
        model.add_position(pos)

        model.clear()

        assert model.get_position_count() == 0
        assert model.get_latest_position() is None

    def test_thread_safety(self):
        """Test thread-safe operations."""
        import threading

        model = GPSDataModel()
        errors = []

        def add_positions():
            try:
                for i in range(100):
                    pos = GPSPosition(48.0 + i * 0.001, 11.0, 0.0)
                    model.add_position(pos)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = [threading.Thread(target=add_positions) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have no errors
        assert len(errors) == 0

        # Should have all positions
        assert model.get_position_count() == 500


class TestGPSTrack:
    """Test suite for GPS track."""

    def test_track_creation(self):
        """Test track creation."""
        track = GPSTrack("Test Track")
        assert track.name == "Test Track"
        assert len(track.positions) == 0

    def test_track_distance(self):
        """Test total distance calculation."""
        track = GPSTrack()

        pos1 = GPSPosition(48.0, 11.0, 0.0)
        pos2 = GPSPosition(48.1, 11.0, 0.0)
        pos3 = GPSPosition(48.2, 11.0, 0.0)

        track.add_position(pos1)
        track.add_position(pos2)
        track.add_position(pos3)

        distance = track.get_total_distance()

        # Distance should be approximately 22.2 km
        assert 20.0 < distance < 25.0

    def test_track_bounds(self):
        """Test bounding box calculation."""
        track = GPSTrack()

        track.add_position(GPSPosition(48.0, 11.0, 0.0))
        track.add_position(GPSPosition(48.5, 11.5, 0.0))
        track.add_position(GPSPosition(48.2, 11.8, 0.0))

        bounds = track.get_bounds()

        assert bounds['min_lat'] == 48.0
        assert bounds['max_lat'] == 48.5
        assert bounds['min_lon'] == 11.0
        assert bounds['max_lon'] == 11.8


class TestConfiguration:
    """Test suite for configuration management."""

    def test_config_singleton(self):
        """Test config is singleton."""
        config1 = Config()
        config2 = Config()
        assert config1 is config2

    def test_config_get(self):
        """Test configuration access."""
        config = Config()

        # Should return value or default
        port = config.get('network.udp_port', 19711)
        assert isinstance(port, int)

    def test_config_get_section(self):
        """Test section retrieval."""
        config = Config()
        network_config = config.get_section('network')

        assert isinstance(network_config, dict)


def run_all_tests():
    """Run all tests with pytest."""
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == "__main__":
    run_all_tests()
