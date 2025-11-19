"""
Command-line interface for GPS Position System.
Provides tools for recording, exporting, and managing GPS data.
"""

import asyncio
import click
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from gps_data_csv_storage import GPSDataCSVStorage
from gps_network_async import AsyncNMEAReceiver, AsyncNMEASender
from gps_structured_logging import setup_logging
from config_loader import get_config

logger = logging.getLogger(__name__)


@click.group()
@click.option('--log-level', default='INFO',
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']))
@click.option('--json-logs', is_flag=True,
              help='Use JSON format for logs')
def cli(log_level: str, json_logs: bool):
    """GPS Position System CLI."""
    setup_logging(log_level=log_level, json_format=json_logs)


@cli.command()
@click.option('--duration', default=60,
              help='Recording duration in seconds')
@click.option('--port', default=19710,
              help='Listen port')
@click.option('--output', default='gps_positions.csv',
              help='Output CSV filename')
async def record(duration: int, port: int, output: str):
    """Record GPS data from UDP stream."""
    click.echo(f"Recording GPS data for {duration} seconds on port {port}...")
    click.echo(f"Output: {output}")

    config = get_config()
    storage = GPSDataCSVStorage()
    receiver = AsyncNMEAReceiver(port=port)
    positions = []

    def on_nmea(nmea_str: str, addr):
        """Handle NMEA data."""
        try:
            from nmea_validator import NMEAValidator

            parsed = NMEAValidator.safe_parse(nmea_str)
            if parsed:
                info = NMEAValidator.extract_position_info(parsed)
                if info:
                    positions.append({
                        'timestamp': datetime.now().isoformat(),
                        'latitude': info.get('latitude'),
                        'longitude': info.get('longitude'),
                        'altitude': info.get('altitude', 0.0),
                        'satellites': info.get('num_satellites'),
                        'quality': info.get('gps_quality')
                    })
                    click.echo(
                        f"Recorded: {info.get('latitude'):.6f}, "
                        f"{info.get('longitude'):.6f}"
                    )
        except Exception as e:
            click.echo(f"Error: {e}", err=True)

    receiver.register_callback(on_nmea)

    try:
        # Create receive task
        receive_task = asyncio.create_task(receiver.start())

        # Wait for duration
        await asyncio.sleep(duration)

        # Stop receiver
        await receiver.stop()

    except KeyboardInterrupt:
        click.echo("Recording stopped by user")
        await receiver.stop()

    # Save data
    if positions:
        filepath = storage.save_positions(positions, output)
        click.echo(f"Saved {len(positions)} positions to {filepath}")
    else:
        click.echo("No positions recorded")


@cli.command()
@click.option('--file', required=True, help='CSV file to analyze')
def stats(file: str):
    """Show statistics for GPS data file."""
    storage = GPSDataCSVStorage()

    try:
        stats_data = storage.get_statistics(file)

        click.echo("\n=== GPS Data Statistics ===\n")
        for key, value in stats_data.items():
            if isinstance(value, float):
                click.echo(f"{key}: {value:.6f}")
            else:
                click.echo(f"{key}: {value}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option('--file', required=True, help='CSV file to filter')
@click.option('--start', required=True,
              help='Start time (YYYY-MM-DD HH:MM:SS)')
@click.option('--end', required=True,
              help='End time (YYYY-MM-DD HH:MM:SS)')
@click.option('--output', help='Output file (optional)')
def filter_by_date(file: str, start: str, end: str,
                   output: Optional[str]):
    """Filter GPS data by date range."""
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)

        storage = GPSDataCSVStorage()
        filtered = storage.filter_by_date_range(file, start_dt, end_dt)

        click.echo(f"Filtered {len(filtered)} positions")

        if output and filtered:
            storage.save_positions(filtered, output)
            click.echo(f"Saved to: {output}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option('--file', required=True, help='CSV file')
@click.option('--days', default=30, help='Delete records older than N days')
@click.option('--confirm', is_flag=True, help='Confirm deletion')
def cleanup(file: str, days: int, confirm: bool):
    """Delete old GPS records."""
    storage = GPSDataCSVStorage()

    if not confirm:
        click.confirm(
            f"Delete records older than {days} days from {file}?",
            abort=True
        )

    try:
        deleted = storage.delete_old_records(file, days)
        click.echo(f"Deleted {deleted} records")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
def list_files():
    """List all GPS data files."""
    storage = GPSDataCSVStorage()
    files = storage.list_files()

    if files:
        click.echo("GPS Data Files:")
        for i, f in enumerate(files, 1):
            click.echo(f"  {i}. {f}")
    else:
        click.echo("No GPS data files found")


@cli.command()
@click.option('--host', default='127.0.0.1', help='Destination host')
@click.option('--port', default=19711, help='Destination port')
@click.option('--lat', required=True, type=float, help='Latitude')
@click.option('--lon', required=True, type=float, help='Longitude')
@click.option('--speed', default=0.0, type=float, help='Speed in m/s')
async def send(host: str, port: int, lat: float,
               lon: float, speed: float):
    """Send GPS position as NMEA."""
    from nmea_validator import NMEAGenerator

    try:
        nmea = NMEAGenerator.generate_rmc(lat, lon, speed=speed)

        sender = AsyncNMEASender(host, port)
        await sender.send_message(nmea)

        click.echo(f"Sent position: {lat}, {lon}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option('--config', default='config.json',
              help='Config file to validate')
def validate_config(config: str):
    """Validate configuration file."""
    try:
        cfg = get_config()
        cfg.validate()
        click.echo(f"✓ Configuration valid: {config}")

        # Show summary
        click.echo("\nNetwork:")
        click.echo(f"  UDP Port: {cfg.get('network.udp_port')}")
        click.echo(f"  Receive Port: {cfg.get('network.receive_port')}")

        click.echo("\nGPS:")
        click.echo(f"  Data File: {cfg.get('gps.data_file')}")
        click.echo(f"  Max Positions: {cfg.get('gps.max_stored_positions')}")

    except Exception as e:
        click.echo(f"✗ Configuration invalid: {e}", err=True)


@cli.command()
@click.option('--file', required=True, help='CSV file to view')
@click.option('--lines', default=10, help='Number of lines to display')
def view(file: str, lines: int):
    """View GPS data file."""
    storage = GPSDataCSVStorage()

    try:
        positions = storage.load_positions(file)

        click.echo(f"\n=== {file} ({len(positions)} total) ===\n")

        for i, pos in enumerate(positions[:lines], 1):
            click.echo(
                f"{i}. {pos.get('timestamp', 'N/A')} - "
                f"Lat: {pos.get('latitude', 'N/A'):.6f}, "
                f"Lon: {pos.get('longitude', 'N/A'):.6f}, "
                f"Alt: {pos.get('altitude', 'N/A')}m"
            )

        if len(positions) > lines:
            click.echo(f"\n... and {len(positions) - lines} more")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
