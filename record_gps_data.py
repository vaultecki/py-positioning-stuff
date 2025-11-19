"""Example: Recording GPS data with async receiver."""

import asyncio
from gps_network_async import AsyncNMEAReceiver
from gps_data_csv_storage import GPSDataCSVStorage
from gps_structured_logging import setup_logging
from nmea_validator import NMEAValidator
from datetime import datetime


async def main():
    # Setup logging
    logger = setup_logging(log_level="INFO", json_format=True)

    # Initialize receiver and storage
    receiver = AsyncNMEAReceiver(host="0.0.0.0", port=19710)
    storage = GPSDataCSVStorage(output_dir="gps_data")
    positions = []

    # Callback for received NMEA
    async def on_nmea(nmea_str: str, addr):
        try:
            parsed = NMEAValidator.safe_parse(nmea_str)
            if parsed:
                info = NMEAValidator.extract_position_info(parsed)
                if info:
                    pos = {
                        'timestamp': datetime.now().isoformat(),
                        'latitude': info['latitude'],
                        'longitude': info['longitude'],
                        'altitude': info.get('altitude', 0.0),
                        'satellites': info.get('num_satellites'),
                        'quality': info.get('gps_quality')
                    }
                    positions.append(pos)
                    logger.info(
                        "position_received",
                        lat=info['latitude'],
                        lon=info['longitude'],
                        source=addr[0]
                    )
        except Exception as e:
            logger.error("nmea_parse_error", error=str(e))

    # Register callback
    receiver.register_callback(on_nmea)

    # Start receiver
    try:
        receiver_task = asyncio.create_task(receiver.start())

        # Record for 60 seconds
        await asyncio.sleep(60)

        # Stop and save
        await receiver.stop()

        if positions:
            storage.save_positions(positions, "recorded_data.csv")
            logger.info("data_saved", count=len(positions))

    except KeyboardInterrupt:
        logger.info("recording_stopped")
        await receiver.stop()


if __name__ == "__main__":
    asyncio.run(main())
