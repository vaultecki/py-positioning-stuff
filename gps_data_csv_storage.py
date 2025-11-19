"""
CSV storage module for GPS position data.
Provides efficient CSV export with append mode and multiple formats.
"""

import csv
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)


class CSVStorageError(Exception):
    """Raised when CSV operations fail."""
    pass


class GPSDataCSVStorage:
    """
    Manages GPS data storage in CSV format with multiple export options.
    Supports append mode, incremental saves, and format conversions.
    """

    def __init__(self, output_dir: str = "config"):
        """
        Initialize CSV storage.

        Args:
            output_dir: Directory for CSV files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"CSV storage initialized: {self.output_dir}")

    def save_positions(self, positions: List[Dict[str, Any]],
                      filename: str = "gps_positions.csv",
                      append: bool = False) -> str:
        """
        Save GPS positions to CSV file.

        Args:
            positions: List of position dictionaries
            filename: Output filename
            append: If True, append to existing file

        Returns:
            Path to saved file

        Raises:
            CSVStorageError: If save operation fails
        """
        try:
            if not positions:
                logger.warning("No positions to save")
                return ""

            filepath = self.output_dir / filename
            mode = 'a' if (append and filepath.exists()) else 'w'
            write_header = not (append and filepath.exists())

            df = pd.DataFrame(positions)

            # Ensure correct column order
            columns = [
                'timestamp', 'latitude', 'longitude', 'altitude',
                'speed', 'course', 'satellites', 'quality'
            ]
            df = df[[col for col in columns if col in df.columns]]

            # Save to CSV
            df.to_csv(filepath, mode=mode, header=write_header,
                     index=False, date_format='%Y-%m-%d %H:%M:%S.%f')

            logger.info(f"Saved {len(positions)} positions to {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error saving CSV: {e}", exc_info=True)
            raise CSVStorageError(f"Failed to save CSV: {e}")

    def load_positions(self, filename: str) -> List[Dict[str, Any]]:
        """
        Load GPS positions from CSV file.

        Args:
            filename: CSV filename to load

        Returns:
            List of position dictionaries
        """
        try:
            filepath = self.output_dir / filename

            if not filepath.exists():
                logger.warning(f"File not found: {filepath}")
                return []

            df = pd.read_csv(filepath)
            positions = df.to_dict('records')

            logger.info(f"Loaded {len(positions)} positions from {filepath}")
            return positions

        except Exception as e:
            logger.error(f"Error loading CSV: {e}", exc_info=True)
            return []

    def append_positions(self, positions: List[Dict[str, Any]],
                        filename: str = "gps_positions.csv") -> str:
        """
        Append positions to existing CSV file.

        Args:
            positions: List of position dictionaries
            filename: CSV filename

        Returns:
            Path to updated file
        """
        return self.save_positions(positions, filename, append=True)



    def get_statistics(self, filename: str) -> Dict[str, Any]:
        """
        Get statistics from CSV file.

        Args:
            filename: CSV filename

        Returns:
            Dictionary with statistics
        """
        try:
            df = pd.read_csv(self.output_dir / filename)

            stats = {
                'record_count': len(df),
                'time_span': None,
                'avg_latitude': float(df['latitude'].mean()) if 'latitude' in df else None,
                'avg_longitude': float(df['longitude'].mean()) if 'longitude' in df else None,
                'avg_altitude': float(df['altitude'].mean()) if 'altitude' in df else None,
                'min_latitude': float(df['latitude'].min()) if 'latitude' in df else None,
                'max_latitude': float(df['latitude'].max()) if 'latitude' in df else None,
                'min_longitude': float(df['longitude'].min()) if 'longitude' in df else None,
                'max_longitude': float(df['longitude'].max()) if 'longitude' in df else None,
            }

            if 'timestamp' in df:
                try:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    stats['time_span'] = (df['timestamp'].max() -
                                        df['timestamp'].min()).total_seconds()
                except:
                    pass

            return stats

        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            return {}

    def filter_by_date_range(self, filename: str,
                            start_date: datetime,
                            end_date: datetime) -> List[Dict[str, Any]]:
        """
        Filter positions by date range.

        Args:
            filename: CSV filename
            start_date: Start datetime
            end_date: End datetime

        Returns:
            Filtered list of positions
        """
        try:
            df = pd.read_csv(self.output_dir / filename)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            mask = (df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)
            filtered_df = df[mask]

            return filtered_df.to_dict('records')

        except Exception as e:
            logger.error(f"Error filtering by date: {e}")
            return []

    def delete_old_records(self, filename: str,
                          days: int = 30) -> int:
        """
        Delete records older than specified days.

        Args:
            filename: CSV filename
            days: Age threshold in days

        Returns:
            Number of deleted records
        """
        try:
            df = pd.read_csv(self.output_dir / filename)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            cutoff = datetime.now() - pd.Timedelta(days=days)
            original_count = len(df)

            df = df[df['timestamp'] >= cutoff]

            df.to_csv(self.output_dir / filename, index=False)

            deleted = original_count - len(df)
            logger.info(f"Deleted {deleted} records older than {days} days")

            return deleted

        except Exception as e:
            logger.error(f"Error deleting old records: {e}")
            return 0

    def list_files(self) -> List[str]:
        """
        List all CSV files in storage directory.

        Returns:
            List of CSV filenames
        """
        return [f.name for f in self.output_dir.glob("*.csv")]
