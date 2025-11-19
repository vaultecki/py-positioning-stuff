"""
Performance monitoring and metrics collection for GPS system.
Provides system-wide metrics collection without external dependencies.
"""

import logging
import time
from typing import Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import json

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    """Aggregated metric data."""
    name: str
    unit: str
    current_value: float = 0.0
    min_value: float = float('inf')
    max_value: float = float('-inf')
    avg_value: float = 0.0
    total_count: int = 0
    points: deque = field(default_factory=lambda: deque(maxlen=1000))

    def add_value(self, value: float) -> None:
        """Add metric value."""
        self.current_value = value
        self.min_value = min(self.min_value, value)
        self.max_value = max(self.max_value, value)
        self.total_count += 1

        # Update average
        self.avg_value = (
                (self.avg_value * (self.total_count - 1) + value) / self.total_count
        )

        self.points.append(
            MetricPoint(datetime.now(), value)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'unit': self.unit,
            'current': self.current_value,
            'min': self.min_value,
            'max': self.max_value,
            'avg': self.avg_value,
            'count': self.total_count
        }


class MetricsCollector:
    """
    Collects and aggregates system metrics.

    Tracks performance metrics for network I/O, data processing,
    and system resources without external dependencies.
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: Dict[str, Metric] = {}
        self.counters: Dict[str, int] = {}
        self.timers: Dict[str, List[float]] = {}
        self.start_time = datetime.now()

    def record_metric(self, name: str, value: float,
                      unit: str = "") -> None:
        """
        Record metric value.

        Args:
            name: Metric name
            value: Metric value
            unit: Unit of measurement
        """
        if name not in self.metrics:
            self.metrics[name] = Metric(name, unit)

        self.metrics[name].add_value(value)
        logger.debug(f"Metric {name}: {value} {unit}")

    def increment_counter(self, name: str, amount: int = 1) -> None:
        """
        Increment counter.

        Args:
            name: Counter name
            amount: Amount to increment
        """
        self.counters[name] = self.counters.get(name, 0) + amount

    def start_timer(self, name: str) -> float:
        """
        Start a timer.

        Args:
            name: Timer name

        Returns:
            Start time (use with stop_timer)
        """
        return time.time()

    def stop_timer(self, name: str, start_time: float) -> float:
        """
        Stop a timer and record duration.

        Args:
            name: Timer name
            start_time: Start time from start_timer

        Returns:
            Elapsed time in milliseconds
        """
        elapsed = (time.time() - start_time) * 1000.0  # Convert to ms

        if name not in self.timers:
            self.timers[name] = []

        self.timers[name].append(elapsed)

        # Keep only last 1000 measurements
        if len(self.timers[name]) > 1000:
            self.timers[name] = self.timers[name][-1000:]

        self.record_metric(f"{name}_ms", elapsed, "ms")

        return elapsed

    def get_metric(self, name: str) -> Dict[str, Any]:
        """Get metric data."""
        if name in self.metrics:
            return self.metrics[name].to_dict()
        return {}

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics."""
        return {
            'metrics': {name: m.to_dict() for name, m in self.metrics.items()},
            'counters': self.counters,
            'timers_avg': {
                name: sum(times) / len(times)
                for name, times in self.timers.items()
                if times
            },
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds()
        }

    def get_summary(self) -> str:
        """Get metrics summary as formatted string."""
        summary = "=== GPS System Metrics ===\n"

        for name, metric in self.metrics.items():
            summary += (
                f"{name}: current={metric.current_value:.2f}, "
                f"avg={metric.avg_value:.2f}, "
                f"min={metric.min_value:.2f}, "
                f"max={metric.max_value:.2f} {metric.unit}\n"
            )

        summary += "\nCounters:\n"
        for name, value in self.counters.items():
            summary += f"{name}: {value}\n"

        summary += "\nTimers (avg ms):\n"
        for name, times in self.timers.items():
            if times:
                avg = sum(times) / len(times)
                summary += f"{name}: {avg:.2f}ms (min={min(times):.2f}, max={max(times):.2f})\n"

        return summary

    def export_json(self) -> str:
        """Export metrics as JSON."""
        return json.dumps(self.get_all_metrics(), indent=2, default=str)

    def reset(self) -> None:
        """Reset all metrics."""
        self.metrics.clear()
        self.counters.clear()
        self.timers.clear()
        self.start_time = datetime.now()


# Global metrics instance
_metrics_instance: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsCollector()
    return _metrics_instance
