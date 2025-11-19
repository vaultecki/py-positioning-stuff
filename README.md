# GPS Position System - Production Ready

A comprehensive GPS position tracking system with robust error handling, MVC architecture, async I/O, and extensive monitoring capabilities.

## 🎯 Overview

The system consists of multiple interconnected components for acquiring, transmitting, storing, and visualizing GPS data:

- **SendPosition**: Streams GPS positions from MATLAB files as NMEA sentences via UDP
- **ReceivePosition**: Receives, validates, and visualizes GPS data with PyQt6 GUI
- **Async Network Stack**: Non-blocking UDP I/O using asyncio
- **Resilient Communication**: Circuit breaker pattern with exponential backoff retry logic
- **CSV Storage**: Efficient position data persistence with Pandas
- **Performance Metrics**: Real-time system monitoring without external dependencies
- **Structured Logging**: JSON-based logging with contextual support
- **CLI Tools**: Command-line interface for recording, filtering, and managing GPS data
- **Map Provider Abstraction**: Pluggable architecture for multiple map tile servers

## ✨ Key Features

### Architecture
- **MVC Pattern**: Clean separation of Model, View, and Controller
- **Thread-Safe**: Concurrent access with proper locking mechanisms
- **Async/Await**: Non-blocking network I/O for better scalability
- **Configuration Management**: Centralized JSON-based configuration
- **Plugin System**: Extensible map providers and custom modules

### Network & Communication
- **Async UDP Receiver**: Non-blocking position reception
- **Circuit Breaker**: Prevents cascade failures on unreliable networks
- **Exponential Backoff**: Intelligent retry strategy with jitter
- **Network Statistics**: Packet tracking, error counting, latency monitoring
- **Checksum Validation**: Full NMEA sentence validation and parsing

### Data Management
- **CSV Storage**: Efficient append-mode position storage
- **Date Range Filtering**: Query positions by time window
- **Automatic Cleanup**: Remove records older than specified days
- **Statistics Calculation**: Distance, speed, bounds, duration analysis
- **Thread-Safe Model**: Concurrent observer pattern for updates

### Monitoring & Observability
- **Metrics Collection**: Min/max/avg/count tracking without external deps
- **Timer Support**: Operation duration measurement
- **Performance Counters**: System event counting
- **JSON Export**: Metrics export for analysis
- **Live Summary**: Formatted metrics display

### Logging
- **Structured JSON Logging**: ELK Stack compatible
- **Context Support**: Add contextual information to logs
- **Log Aggregation**: Centralized log collection
- **Multiple Handlers**: Console and file output
- **CSV Export**: Export logs for analysis

### Map Visualization
- **Provider Abstraction**: Support multiple tile servers
- **Built-in Providers**: OpenStreetMap, Carto Dark
- **Tile Caching**: Reduce network requests with LRU cache
- **Async Loading**: Non-blocking map tile fetching
- **Update Throttling**: Configurable map update thresholds

### CLI Management
- **Recording**: Capture GPS stream to CSV
- **Analysis**: View statistics and bounds
- **Filtering**: Extract date-range subsets
- **Maintenance**: Cleanup old records
- **Configuration**: Validate and display settings
- **Data Inspection**: Browse position data

## 📋 Requirements

- Python 3.8+
- PyQt6 for GUI
- Pandas for CSV operations
- Scipy for MAT file support
- pynmea2 for NMEA parsing
- Click for CLI tools
- Pillow for image processing

## 🚀 Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd gps-position-system
```

### 2. Create Virtual Environment (Recommended)
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Application
Edit `config.json` to match your environment:

```json
{
  "network": {
    "udp_address": "127.0.0.1",
    "udp_port": 19711,
    "receive_port": 19710,
    "timeout": 5.0
  },
  "gps": {
    "data_file": "data/AguasVivasGPSData.mat",
    "max_stored_positions": 1000
  },
  "map": {
    "zoom_level": 13,
    "update_threshold_km": 1.0
  }
}
```

## 🎮 Usage

### Start GPS Sender
```bash
python SendPosition.py
```

Starts streaming GPS positions as NMEA RMC sentences to configured UDP address.

**Features:**
- Loads positions from MATLAB MAT files
- Configurable emission interval
- Full logging and error reporting
- Signal-based position emission

### Start GPS Receiver GUI
```bash
python ReceivePosition.py
```

Launches PyQt6 GUI with real-time visualization.

**Features:**
- Position reception and validation
- Real-time plot display
- OpenStreetMap integration
- Statistics tracking
- CSV export with append mode
- Thread-safe updates

### CLI Tools

#### Record GPS Data
```bash
python gps_cli.py record --duration 300 --port 19710 --output session.csv
```

Record GPS stream to CSV file for specified duration.

#### View Statistics
```bash
python gps_cli.py stats --file session.csv
```

Display dataset statistics: record count, time span, bounds, averages.

#### Filter by Date
```bash
python gps_cli.py filter-by-date \
  --file session.csv \
  --start "2024-01-01 00:00:00" \
  --end "2024-01-31 23:59:59" \
  --output filtered.csv
```

Extract position records within date range.

#### View Data
```bash
python gps_cli.py view --file session.csv --lines 20
```

Display sample positions from file.

#### Cleanup Old Records
```bash
python gps_cli.py cleanup --file session.csv --days 30 --confirm
```

Remove records older than N days.

#### Send NMEA Position
```bash
python gps_cli.py send --lat 48.1234 --lon 11.5678 --speed 5.0
```

Transmit single NMEA position sentence.

#### Validate Configuration
```bash
python gps_cli.py validate-config --config config.json
```

Check configuration validity and display settings.

## 📁 Project Structure

```
gps-position-system/
├── config.json                          # Configuration file
├── config_loader.py                     # Configuration management
├── coordinates.py                       # Coordinate system (NMEA, decimal, DMS)
├── nmea_validator.py                    # NMEA parsing & validation
├── gps_data_model.py                    # Data model (MVC)
├── gps_data_csv_storage.py              # CSV storage operations
├── gps_data_mat_play.py                 # MATLAB file playback
├── gps_network_async.py                 # Async UDP I/O
├── gps_network_resilience.py            # Circuit breaker & retry logic
├── gps_metrics.py                       # Performance metrics collection
├── gps_structured_logging.py            # JSON structured logging
├── gps_map_providers.py                 # Map provider abstraction
├── gps_cli.py                           # CLI management tool
├── SendPosition.py                      # GPS sender application
├── ReceivePosition.py                   # GPS receiver GUI application
├── record_gps_data.py                   # Example: async recording
├── test_gps_system.py                   # Test suite
├── helper_maps.py                       # Map tile downloading
├── helper_map_ned.py                    # NED coordinate conversions
├── requirements.txt                     # Python dependencies
└── README.md                            # This file
```

## 🏗️ Architecture

### MVC Pattern

**Model** (`gps_data_model.py`):
- `GPSDataModel`: Thread-safe position storage with observer pattern
- `GPSPosition`: Single position record with metadata
- `GPSTrack`: Track analysis and statistics

**View** (`ReceivePosition.py`):
- `GPSPlotView`: Real-time position plotting
- `MapManager`: Async map tile management
- Qt widgets for UI elements

**Controller** (`ReceivePosition.py`):
- `ReceiveNmea`: Main event controller
- Signal/slot communication with Qt
- Data flow orchestration

### Network Stack

**Async Layer** (`gps_network_async.py`):
- Non-blocking UDP reception with asyncio
- Callback-based position handling
- Network statistics tracking

**Resilience Layer** (`gps_network_resilience.py`):
- Circuit breaker (CLOSED → OPEN → HALF_OPEN)
- Exponential backoff with jitter
- Automatic failure detection

### Data Pipeline

```
MATLAB File → PlayGPSMat → NMEA Generator → UDP Send
                                ↓
                          Network (UDP)
                                ↓
                        AsyncNMEAReceiver
                                ↓
                          NMEAValidator
                                ↓
                        GPSDataModel
                                ↓
                    GPSDataCSVStorage (Async)
```

## 📊 Monitoring

### Metrics Collection

```python
from gps_metrics import get_metrics

metrics = get_metrics()
metrics.record_metric('temperature', 23.5, 'C')
metrics.increment_counter('positions_processed')

start = metrics.start_timer('operation')
# ... do work ...
elapsed = metrics.stop_timer('operation', start)

print(metrics.get_summary())
```

### JSON Export

```python
json_data = metrics.export_json()
```

## 📝 Configuration

### network section
- `udp_address`: Destination IP address
- `broadcast_address`: Broadcast address
- `udp_port`: Send port (19711)
- `receive_port`: Receive port (19710)
- `timeout`: Socket timeout in seconds

### gps section
- `data_file`: Path to MATLAB GPS data file
- `start_timeout`: Delay before sending starts
- `time_between_positions`: Interval between positions
- `max_stored_positions`: Maximum in-memory positions

### map section
- `delta_lat`: Map vertical extent in degrees
- `delta_lon`: Map horizontal extent in degrees
- `zoom_level`: OSM zoom level (0-19)
- `update_threshold_km`: Minimum distance to trigger map update
- `cache_size`: Maximum cached tiles

### ui section
- `window_title`: GUI window title
- `map_widget_width`: Map display width
- `map_widget_height`: Map display height
- `plot_update_interval`: Plot refresh rate (ms)

### logging section
- `level`: Log level (DEBUG, INFO, WARNING, ERROR)
- `format`: Log message format string
- `file`: Log file path
- `max_bytes`: Max log file size before rotation
- `backup_count`: Number of backup log files

## 🧪 Testing

### Run All Tests
```bash
pytest test_gps_system.py -v
```

### With Coverage
```bash
pytest test_gps_system.py --cov=. --cov-report=html
```

### Specific Test Class
```bash
pytest test_gps_system.py::TestCoordinates -v
```

### Coverage Targets
- Coordinates: 100%
- NMEA Validator: 95%+
- GPS Data Model: 90%+
- CSV Storage: 85%+

## 🛠️ Code Quality

### Formatting
```bash
black *.py
```

### Linting
```bash
flake8 *.py --max-line-length=100
pylint *.py
```

### Type Checking
```bash
mypy *.py
```

## 📚 API Examples

### Coordinate System
```python
from coordinates import Coordinate, Position

# Create from decimal degrees
pos = Position.from_decimal(48.1234, 11.5678, 100.0)

# Convert to different formats
dms = pos.latitude.degrees_minutes_seconds
nmea_str = pos.latitude.to_nmea_string()

# Calculate distance
distance_km = pos.distance_to(other_position)
```

### NMEA Validation
```python
from nmea_validator import NMEAValidator, NMEAGenerator

# Validate NMEA sentence
is_valid = NMEAValidator.is_valid_nmea(nmea_string)

# Parse safely
parsed = NMEAValidator.safe_parse(nmea_string)
if parsed:
    info = NMEAValidator.extract_position_info(parsed)
    print(f"Lat: {info['latitude']}, Lon: {info['longitude']}")

# Generate NMEA
nmea = NMEAGenerator.generate_rmc(48.1234, 11.5678)
```

### GPS Data Model
```python
from gps_data_model import GPSDataModel, GPSPosition

model = GPSDataModel(max_positions=1000)

# Register observer
def on_position(pos):
    print(f"New position: {pos.latitude}, {pos.longitude}")

model.register_observer(on_position)

# Add position
position = GPSPosition(48.1234, 11.5678, 100.0)
model.add_position(position)

# Get statistics
stats = model.get_statistics()
print(f"Total distance: {stats['total_distance']} m")
```

### CSV Storage
```python
from gps_data_csv_storage import GPSDataCSVStorage

storage = GPSDataCSVStorage(output_dir="data")

# Save positions
filepath = storage.save_positions(positions, "track.csv")

# Load positions
loaded = storage.load_positions("track.csv")

# Get statistics
stats = storage.get_statistics("track.csv")

# Filter by date
filtered = storage.filter_by_date_range(
    "track.csv", 
    start_date, 
    end_date
)
```

### Async Network
```python
from gps_network_async import AsyncNMEAReceiver

receiver = AsyncNMEAReceiver(host="0.0.0.0", port=19710)

def on_nmea(nmea_str, addr):
    print(f"Received from {addr}: {nmea_str}")

receiver.register_callback(on_nmea)

# Start receiving (in async context)
await receiver.start()
```

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError"
**Solution:** Install all dependencies:
```bash
pip install -r requirements.txt
```

### Issue: UDP packets not received
**Solution:**
1. Check firewall rules
2. Verify IP and port in config.json
3. Test with loopback address first (127.0.0.1)

### Issue: Maps not loading
**Solution:**
1. Check internet connectivity
2. OSM servers may be temporarily unavailable
3. Verify User-Agent headers

### Issue: GUI freezes
**Solution:**
1. Reduce `max_stored_positions` in config
2. Increase `update_threshold_km` for maps
3. Check log files for errors

## ⚡ Performance Tips

1. **Limit Stored Positions**: Set `max_stored_positions: 500` for large datasets
2. **Increase Map Update Threshold**: Use `update_threshold_km: 2.0` to reduce requests
3. **Adjust Plot Update Rate**: Increase `plot_update_interval` for less frequent updates
4. **Disable Debug Logging**: Set `level: INFO` instead of `DEBUG`
5. **Enable Tile Caching**: Configure `cache_size` appropriately

## 📦 Dependencies

See `requirements.txt` for complete list. Key dependencies:

- **PyQt6** - GUI framework
- **Pandas** - CSV operations
- **Scipy** - MATLAB file support
- **pynmea2** - NMEA parsing
- **Click** - CLI framework
- **Pillow** - Image processing
- **Requests** - HTTP for map tiles

## 📄 License

- MIT License 

## 🤝 Contributing

Contributions welcome! Please:

1. Add tests for new features
2. Follow PEP 8 style guide
3. Use type hints
4. Update documentation

## 📞 Support

For issues or questions:
1. Check this README
2. Review test examples in `test_gps_system.py`
3. Check log files for error details
4. Review code docstrings

## 🗺️ Roadmap

Potential enhancements:
- Real hardware GPS receiver support
- Multi-user session management
- Track comparison and analysis
