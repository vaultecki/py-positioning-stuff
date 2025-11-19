"""
Resilient network communication with retry logic and circuit breaker pattern.
Provides robust error handling for unreliable connections.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Callable, Optional, Any, TypeVar, Coroutine
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 3
    initial_delay_ms: int = 100
    max_delay_ms: int = 5000
    exponential_base: float = 2.0
    jitter_enabled: bool = True


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout_ms: int = 30000
    half_open_max_requests: int = 1


@dataclass
class RetryStats:
    """Statistics for retry operations."""
    total_attempts: int = 0
    successful: int = 0
    failed: int = 0
    retries_triggered: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None


class CircuitBreaker:
    """
    Circuit breaker implementation for preventing cascade failures.

    States:
    - CLOSED: Normal operation
    - OPEN: Reject requests after threshold failures
    - HALF_OPEN: Test if service recovered
    """

    def __init__(self, config: CircuitBreakerConfig):
        """
        Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration
        """
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change = datetime.now()

    def record_success(self) -> None:
        """Record successful operation."""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker: HALF_OPEN -> CLOSED")
            self.state = CircuitState.CLOSED
            self.last_state_change = datetime.now()

    def record_failure(self) -> None:
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if (self.state == CircuitState.CLOSED and
                self.failure_count >= self.config.failure_threshold):
            logger.warning("Circuit breaker: CLOSED -> OPEN")
            self.state = CircuitState.OPEN
            self.last_state_change = datetime.now()

    def can_attempt(self) -> bool:
        """Check if operation can be attempted."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout expired
            elapsed = (datetime.now() - self.last_state_change).total_seconds() * 1000
            if elapsed >= self.config.recovery_timeout_ms:
                logger.info("Circuit breaker: OPEN -> HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.failure_count = 0
                self.last_state_change = datetime.now()
                return True
            return False

        # HALF_OPEN state
        return self.success_count < self.config.half_open_max_requests

    def get_state(self) -> str:
        """Get current circuit breaker state."""
        return self.state.value


class ResilientNetworkClient:
    """
    Network client with retry logic and circuit breaker.

    Implements exponential backoff, jitter, and circuit breaker pattern
    for reliable communication over unreliable networks.
    """

    def __init__(self,
                 retry_config: Optional[RetryConfig] = None,
                 circuit_config: Optional[CircuitBreakerConfig] = None):
        """
        Initialize resilient client.

        Args:
            retry_config: Retry configuration
            circuit_config: Circuit breaker configuration
        """
        self.retry_config = retry_config or RetryConfig()
        self.circuit_config = circuit_config or CircuitBreakerConfig()
        self.circuit_breaker = CircuitBreaker(self.circuit_config)
        self.stats = RetryStats()

    async def execute_with_retry(self,
                                 operation: Callable[..., Coroutine],
                                 *args,
                                 **kwargs) -> Any:
        """
        Execute operation with retry logic and circuit breaker.

        Args:
            operation: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Operation result
        """
        if not self.circuit_breaker.can_attempt():
            logger.error(f"Circuit breaker OPEN: rejecting request")
            raise RuntimeError("Circuit breaker is open")

        last_error = None

        for attempt in range(self.retry_config.max_retries):
            try:
                self.stats.total_attempts += 1

                # Execute operation
                result = await operation(*args, **kwargs)

                self.stats.successful += 1
                self.circuit_breaker.record_success()

                if attempt > 0:
                    logger.info(f"Operation succeeded on attempt {attempt + 1}")

                return result

            except Exception as e:
                last_error = e
                self.stats.failed += 1
                self.circuit_breaker.record_failure()

                if attempt < self.retry_config.max_retries - 1:
                    delay = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay}ms..."
                    )
                    self.stats.retries_triggered += 1
                    await asyncio.sleep(delay / 1000.0)
                else:
                    logger.error(
                        f"Operation failed after {self.retry_config.max_retries} attempts"
                    )

        self.stats.last_error = str(last_error)
        self.stats.last_error_time = datetime.now()
        raise last_error

    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff with optional jitter.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in milliseconds
        """
        delay = (
                self.retry_config.initial_delay_ms *
                (self.retry_config.exponential_base ** attempt)
        )

        # Cap maximum delay
        delay = min(delay, self.retry_config.max_delay_ms)

        # Add jitter
        if self.retry_config.jitter_enabled:
            import random
            jitter = random.uniform(0, delay * 0.1)
            delay += jitter

        return delay

    def get_stats(self) -> RetryStats:
        """Get retry statistics."""
        return self.stats

    def get_circuit_state(self) -> str:
        """Get circuit breaker state."""
        return self.circuit_breaker.get_state()

    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = RetryStats()
