"""
Improved GPS Position Receiver with MVC architecture.
Receives and visualizes NMEA GPS data with thread-safe GUI updates.
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional, List
from collections import deque

import numpy as np
import pandas as pd
import PIL.ImageQt
import pyqtgraph as pg

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import pyqtSignal, QObject

try:
    from config_loader import get_config
    from coordinates import Coordinate, Position
    from nmea_validator import NMEAValidator
    from gps_data_model import GPSDataModel, GPSPosition
    import bert_utils.helper_udp
    import bert_utils.helper_maps
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


class MapManager(QObject):
    """
    Manages map image loading and caching.
    Thread-safe map operations with update throttling.
    """

    map_loaded = pyqtSignal(object)  # Emits PIL Image

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = get_config()
        self.last_map_position: Optional[Position] = None
        self.map_cache = {}
        self.loading = False

        # Map parameters from config
        self.delta_lat = self.config.get('map.delta_lat', 0.075)
        self.delta_lon = self.config.get('map.delta_lon', 0.15)
        self.zoom_level = self.config.get('map.zoom_level', 13)
        self.update_threshold_km = self.config.get('map.update_threshold_km', 1.0)

    def should_update_map(self, position: Position) -> bool:
        """
        Check if map should be updated based on position change.

        Args:
            position: Current GPS position

        Returns:
            True if map update is needed
        """
        if self.last_map_position is None:
            return True

        # Calculate distance moved
        distance_km = self.last_map_position.distance_to(position)

        return distance_km >= self.update_threshold_km

    def load_map_async(self, position: Position) -> None:
        """
        Load map image asynchronously.

        Args:
            position: GPS position for map center
        """
        if self.loading:
            logger.debug("Map load already in progress")
            return

        if not self.should_update_map(position):
            logger.debug("Map update not needed")
            return

        self.loading = True

        # Start loading in background thread
        import threading
        thread = threading.Thread(
            target=self._load_map_worker,
            args=(position,),
            daemon=True
        )
        thread.start()

    def _load_map_worker(self, position: Position) -> None:
        """
        Worker thread for map loading.

        Args:
            position: GPS position for map center
        """
        try:
            lat, lon, _ = position.to_decimal_tuple()

            logger.info(f"Loading map for position: {lat:.6f}, {lon:.6f}")

            # Load map image
            img = bert_utils.helper_maps.get_image_osm_tile(
                lat, lon,
                self.delta_lat, self.delta_lon,
                self.zoom_level
            )

            # Emit signal with loaded image
            self.map_loaded.emit(img)
            self.last_map_position = position

            logger.info("Map loaded successfully")

        except Exception as e:
            logger.error(f"Error loading map: {e}", exc_info=True)
        finally:
            self.loading = False


class GPSPlotView(QObject):
    """
    View component for GPS plot visualization.
    Manages plot widget and data display.
    """

    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)

        # Create plot widget
        self.plot_widget = pg.PlotWidget(parent)
        self.plot_widget.setTitle("GPS Position Track")
        self.plot_widget.setLabel('left', 'Latitude (°)')
        self.plot_widget.setLabel('bottom', 'Longitude (°)')
        self.plot_widget.addLegend()
        self.plot_widget.showGrid(x=True, y=True)

        # Create plot lines
        pen_lat = pg.mkPen(color=(255, 0, 0), width=2)
        pen_lon = pg.mkPen(color=(0, 255, 0), width=2)

        self.lat_line = self.plot_widget.plot(
            [], [], name="Latitude", pen=pen_lat, symbol='o', symbolSize=5
        )
        self.lon_line = self.plot_widget.plot(
            [], [], name="Longitude", pen=pen_lon, symbol='s', symbolSize=5
        )

        # Data storage
        self.lon_data = deque(maxlen=1000)
        self.lat_data = deque(maxlen=1000)

    def update_plot(self, positions: List[GPSPosition]) -> None:
        """
        Update plot with new position data.

        Args:
            positions: List of GPS positions to plot
        """
        if not positions:
            return

        try:
            # Extract coordinates
            lons = [pos.longitude for pos in positions]
            lats = [pos.latitude for pos in positions]

            # Update plot data
            self.lat_line.setData(lons, lats)

            logger.debug(f"Plot updated with {len(positions)} positions")

        except Exception as e:
            logger.error(f"Error updating plot: {e}")

    def clear(self) -> None:
        """Clear plot data."""
        self.lat_line.setData([], [])
        self.lon_data.clear()
        self.lat_data.clear()


class ReceiveNmea(QtWidgets.QMainWindow):
    """
    Main window for GPS position receiver.
    Implements MVC pattern with thread-safe updates.
    """

    # Qt signals for thread-safe GUI updates
    position_received = pyqtSignal(object)  # GPSPosition
    update_plot_signal = pyqtSignal()
    update_map_signal = pyqtSignal(object)  # Position
    update_stats_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        self.config = get_config()

        # Initialize data model
        max_positions = self.config.get('gps.max_stored_positions', 1000)
        self.gps_model = GPSDataModel(max_positions=max_positions)
        self.gps_model.register_observer(self.on_model_updated)

        # Initialize UI
        self.init_ui()

        # Initialize map manager
        self.map_manager = MapManager(self)
        self.map_manager.map_loaded.connect(self.on_map_loaded)

        # Initialize UDP receiver
        self.init_network()

        # Connect signals
        self.position_received.connect(self.on_position_received_main_thread)
        self.update_plot_signal.connect(self.update_plot)
        self.update_map_signal.connect(self.request_map_update)
        self.update_stats_signal.connect(self.update_statistics_display)

        # Statistics
        self.received_count = 0
        self.error_count = 0

        logger.info("ReceiveNmea initialized successfully")

    def init_ui(self) -> None:
        """Initialize user interface."""
        # Main widget and layout
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QtWidgets.QVBoxLayout(main_widget)

        # Window title
        window_title = self.config.get('ui.window_title', 'GPS Position Receiver')
        self.setWindowTitle(window_title)

        # Statistics label
        self.stats_label = QtWidgets.QLabel("Waiting for GPS data...")
        self.stats_label.setStyleSheet("font-weight: bold; padding: 5px;")
        main_layout.addWidget(self.stats_label)

        # Map widget
        map_width = self.config.get('ui.map_widget_width', 500)
        map_height = self.config.get('ui.map_widget_height', 300)
        self.map_widget = QtWidgets.QLabel()
        self.map_widget.setMaximumSize(map_width, map_height)
        self.map_widget.setScaledContents(True)
        self.map_widget.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.map_widget.setStyleSheet("border: 1px solid gray;")
        main_layout.addWidget(self.map_widget)

        # GPS plot view
        self.plot_view = GPSPlotView(self)
        main_layout.addWidget(self.plot_view.plot_widget)

        # Bottom controls
        button_layout = QtWidgets.QHBoxLayout()

        self.save_btn = QtWidgets.QPushButton("Save Data")
        self.save_btn.clicked.connect(self.on_save_clicked)
        button_layout.addWidget(self.save_btn)

        self.clear_btn = QtWidgets.QPushButton("Clear Data")
        self.clear_btn.clicked.connect(self.on_clear_clicked)
        button_layout.addWidget(self.clear_btn)

        self.save_checkbox = QtWidgets.QCheckBox("Append to existing file")
        button_layout.addWidget(self.save_checkbox)

        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # Set window size
        self.resize(800, 700)

    def init_network(self) -> None:
        """Initialize network receiver."""
        try:
            recv_port = self.config.get('network.receive_port', 19711)
            self.sock = bert_utils.helper_udp.UDPSocketClass(recv_port=recv_port)
            self.sock.udp_recv_data.connect(self.on_receive_nmea)
            logger.info(f"Listening on port {recv_port}")
        except Exception as e:
            logger.error(f"Failed to initialize network: {e}")
            QtWidgets.QMessageBox.critical(
                self, "Network Error",
                f"Failed to initialize UDP receiver: {e}"
            )
            raise

    def on_receive_nmea(self, nmea_str: str, addr: tuple) -> None:
        """
        Handle received NMEA data (called from network thread).

        Args:
            nmea_str: NMEA sentence string
            addr: Sender address tuple
        """
        try:
            # Validate and parse NMEA
            parsed = NMEAValidator.safe_parse(nmea_str, validate=True)

            if parsed is None:
                self.error_count += 1
                logger.warning(f"Invalid NMEA received: {nmea_str}")
                return

            # Extract position info
            pos_info = NMEAValidator.extract_position_info(parsed)

            if pos_info is None:
                logger.debug("NMEA sentence contains no position data")
                return

            # Create GPSPosition object
            position = GPSPosition(
                latitude=pos_info['latitude'],
                longitude=pos_info['longitude'],
                altitude=pos_info.get('altitude', 0.0),
                timestamp=pos_info.get('timestamp', datetime.now()),
                satellites=pos_info.get('num_satellites'),
                quality=pos_info.get('gps_quality')
            )

            # Emit signal for main thread processing
            self.position_received.emit(position)

        except Exception as e:
            self.error_count += 1
            logger.error(f"Error processing NMEA: {e}", exc_info=True)

    def on_position_received_main_thread(self, position: GPSPosition) -> None:
        """
        Handle position in main GUI thread.

        Args:
            position: GPS position object
        """
        self.received_count += 1

        # Add to model (will trigger observer)
        self.gps_model.add_position(position)

        # Update statistics display
        self.update_stats_signal.emit(self.gps_model.get_statistics())

        # Update plot
        self.update_plot_signal.emit()

        # Request map update (throttled)
        pos = Position.from_decimal(
            position.latitude,
            position.longitude,
            position.altitude
        )
        self.update_map_signal.emit(pos)

    def on_model_updated(self, position: GPSPosition) -> None:
        """
        Observer callback when model is updated.

        Args:
            position: New GPS position
        """
        logger.debug(f"Model updated with position: "
                     f"{position.latitude:.6f}, {position.longitude:.6f}")

    def update_plot(self) -> None:
        """Update plot with current data."""
        positions = self.gps_model.get_positions()
        self.plot_view.update_plot(positions)

    def request_map_update(self, position: Position) -> None:
        """
        Request map update for position.

        Args:
            position: GPS position
        """
        self.map_manager.load_map_async(position)

    def on_map_loaded(self, img) -> None:
        """
        Handle loaded map image.

        Args:
            img: PIL Image object
        """
        try:
            # Convert PIL image to QPixmap
            pixmap = QtGui.QPixmap.fromImage(PIL.ImageQt.ImageQt(img))
            self.map_widget.setPixmap(pixmap)
            logger.debug("Map image displayed")
        except Exception as e:
            logger.error(f"Error displaying map: {e}")

    def update_statistics_display(self, stats: dict) -> None:
        """
        Update statistics label.

        Args:
            stats: Statistics dictionary
        """
        try:
            stored = stats.get('stored_positions', 0)
            total = stats.get('total_received', 0)
            distance = stats.get('total_distance', 0.0)
            avg_speed = stats.get('average_speed', 0.0)

            text = (f"Positions: {stored} stored, {self.received_count} received, "
                    f"{self.error_count} errors | "
                    f"Distance: {distance:.1f}m | "
                    f"Avg Speed: {avg_speed * 3.6:.1f} km/h")

            self.stats_label.setText(text)

        except Exception as e:
            logger.error(f"Error updating statistics: {e}")

    def on_save_clicked(self) -> None:
        """Handle save button click."""
        try:
            positions = self.gps_model.get_positions()

            if not positions:
                QtWidgets.QMessageBox.warning(
                    self, "No Data",
                    "No GPS positions to save"
                )
                return

            # Prepare data for export
            data = {
                'Timestamp': [p.timestamp.isoformat() for p in positions],
                'Latitude': [p.latitude for p in positions],
                'Longitude': [p.longitude for p in positions],
                'Altitude (m)': [p.altitude for p in positions],
                'Speed (m/s)': [p.speed if p.speed is not None else '' for p in positions],
                'Satellites': [p.satellites if p.satellites is not None else '' for p in positions],
                'Quality': [p.quality if p.quality is not None else '' for p in positions]
            }

            df = pd.DataFrame(data)

            # Determine filename
            output_dir = self.config.get('data.output_dir', 'config')
            base_filename = self.config.get('data.default_filename',
                                            'car_position_nmea_0183.xlsx')
            filename = os.path.join(output_dir, base_filename)

            # Handle append mode
            if self.save_checkbox.isChecked() and os.path.exists(filename):
                try:
                    df_old = pd.read_excel(filename, engine='openpyxl')
                    df = pd.concat([df_old, df], ignore_index=True)
                    logger.info(f"Appending to existing file: {filename}")
                except Exception as e:
                    logger.error(f"Error reading existing file: {e}")
            else:
                # Create new filename if file exists
                if os.path.exists(filename):
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(filename):
                        filename = f"{base}_{counter}{ext}"
                        counter += 1

            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)

            # Save to Excel
            df.to_excel(filename, index=False, engine='openpyxl')

            logger.info(f"Data saved to: {filename}")

            QtWidgets.QMessageBox.information(
                self, "Success",
                f"Data saved successfully to:\n{filename}\n\n"
                f"{len(positions)} positions saved"
            )

        except Exception as e:
            logger.error(f"Error saving data: {e}", exc_info=True)
            QtWidgets.QMessageBox.critical(
                self, "Save Error",
                f"Failed to save data:\n{e}"
            )

    def on_clear_clicked(self) -> None:
        """Handle clear button click."""
        reply = QtWidgets.QMessageBox.question(
            self, "Clear Data",
            "Are you sure you want to clear all GPS data?",
            QtWidgets.QMessageBox.StandardButton.Yes |
            QtWidgets.QMessageBox.StandardButton.No
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.gps_model.clear()
            self.plot_view.clear()
            self.received_count = 0
            self.error_count = 0
            self.stats_label.setText("Data cleared. Waiting for GPS data...")
            logger.info("Data cleared")

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        logger.info("Application closing")
        event.accept()


def main():
    """Main entry point."""
    try:
        app = QtWidgets.QApplication(sys.argv)

        # Set application style
        app.setStyle('Fusion')

        # Create and show main window
        window = ReceiveNmea()
        window.show()

        logger.info("Application started")

        return app.exec()

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
