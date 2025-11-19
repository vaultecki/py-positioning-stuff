"""
Asynchronous GPS NMEA receiver using asyncio.
Provides efficient non-blocking UDP reception with proper error handling.
"""

import asyncio
import logging
import socket
from typing import Callable, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class NetworkStats:
    """Network statistics."""
    packets_received: int = 0
    packets_dropped: int = 0
    bytes_received: int = 0
    errors: int = 0
    avg_latency_ms: float = 0.0


class AsyncNMEAReceiver:
    """
    Asynchronous NMEA data receiver using asyncio.

    Provides efficient non-blocking UDP socket handling with
    automatic reconnection and statistics tracking.
    """

    def __init__(self, host: str = "127.0.0.1",
                 port: int = 19710,
                 buffer_size: int = 4096):
        """
        Initialize async receiver.

        Args:
            host: Listen address
            port: Listen port
            buffer_size: UDP buffer size
        """
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.socket: Optional[socket.socket] = None
        self.is_running = False
        self.stats = NetworkStats()
        self.callbacks: list[Callable] = []

    def register_callback(self, callback: Callable) -> None:
        """
        Register callback for received NMEA data.

        Args:
            callback: Async function to call on data reception
        """
        self.callbacks.append(callback)

    async def start(self) -> None:
        """Start the async receiver."""
        self.is_running = True
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.setblocking(False)

            logger.info(f"Async receiver started on {self.host}:{self.port}")

            await self.receive_loop()

        except Exception as e:
            logger.error(f"Receiver error: {e}", exc_info=True)
            self.stats.errors += 1
        finally:
            await self.stop()

    async def receive_loop(self) -> None:
        """Main receive loop."""
        loop = asyncio.get_event_loop()

        while self.is_running:
            try:
                # Non-blocking receive
                data, addr = await loop.sock_recvfrom(
                    self.socket, self.buffer_size
                )

                self.stats.packets_received += 1
                self.stats.bytes_received += len(data)

                # Decode and process
                try:
                    nmea_str = data.decode('utf-8').strip()

                    # Call registered callbacks
                    for callback in self.callbacks:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(nmea_str, addr)
                        else:
                            callback(nmea_str, addr)

                except UnicodeDecodeError:
                    logger.warning(f"Invalid UTF-8 from {addr}")
                    self.stats.errors += 1

            except BlockingIOError:
                await asyncio.sleep(0.001)

            except Exception as e:
                logger.error(f"Receive loop error: {e}")
                self.stats.errors += 1
                await asyncio.sleep(0.1)

    async def stop(self) -> None:
        """Stop the receiver."""
        self.is_running = False

        if self.socket:
            self.socket.close()

        logger.info("Async receiver stopped")

    async def send_data(self, data: str,
                        host: str = "127.0.0.1",
                        port: int = 19711) -> None:
        """
        Send UDP data asynchronously.

        Args:
            data: Data to send
            host: Destination host
            port: Destination port
        """
        try:
            loop = asyncio.get_event_loop()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            message = data.encode('utf-8')
            await loop.sock_sendto(sock, message, (host, port))

            sock.close()
            logger.debug(f"Sent {len(message)} bytes to {host}:{port}")

        except Exception as e:
            logger.error(f"Send error: {e}")
            self.stats.errors += 1

    def get_stats(self) -> NetworkStats:
        """Get network statistics."""
        return self.stats

    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = NetworkStats()


class AsyncNMEASender:
    """
    Asynchronous NMEA sender using asyncio.
    """

    def __init__(self, host: str = "127.0.0.1",
                 port: int = 19711):
        """
        Initialize async sender.

        Args:
            host: Destination host
            port: Destination port
        """
        self.host = host
        self.port = port
        self.stats = NetworkStats()

    async def send_message(self, message: str) -> bool:
        """
        Send NMEA message asynchronously.

        Args:
            message: NMEA sentence to send

        Returns:
            True if successful
        """
        try:
            loop = asyncio.get_event_loop()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            data = message.encode('utf-8')
            await loop.sock_sendto(sock, data, (self.host, self.port))

            sock.close()

            self.stats.packets_received += 1
            self.stats.bytes_received += len(data)

            return True

        except Exception as e:
            logger.error(f"Send error: {e}")
            self.stats.errors += 1
            return False

    async def send_burst(self, messages: list[str],
                         delay_ms: float = 100) -> int:
        """
        Send multiple messages with delay between them.

        Args:
            messages: List of NMEA sentences
            delay_ms: Delay between sends in milliseconds

        Returns:
            Number of successfully sent messages
        """
        sent = 0

        for message in messages:
            if await self.send_message(message):
                sent += 1
            await asyncio.sleep(delay_ms / 1000.0)

        return sent
