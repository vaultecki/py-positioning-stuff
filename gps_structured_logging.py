"""
Structured logging for GPS system.
Provides JSON logging, contextual logging, and log aggregation support.
"""

import logging
import json
import sys
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Outputs logs as JSON for easy parsing and aggregation.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add custom fields from extras
        if hasattr(record, 'context'):
            log_data.update(record.context)

        return json.dumps(log_data)


class ContextLogger:
    """
    Logger with context support for structured logging.

    Allows adding contextual information to all subsequent logs.
    """

    def __init__(self, name: str):
        """
        Initialize context logger.

        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
        self.context: Dict[str, Any] = {}

    def set_context(self, **kwargs) -> None:
        """
        Set logging context.

        Args:
            **kwargs: Context key-value pairs
        """
        self.context.update(kwargs)

    def clear_context(self) -> None:
        """Clear logging context."""
        self.context.clear()

    def _log(self, level: int, msg: str, **kwargs) -> None:
        """Internal logging method with context."""
        extra = {'context': {**self.context, **kwargs}}
        self.logger.log(level, msg, extra=extra)

    def debug(self, msg: str, **kwargs) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs) -> None:
        """Log info message."""
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs) -> None:
        """Log warning message."""
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs) -> None:
        """Log error message."""
        self._log(logging.ERROR, msg, **kwargs)

    def critical(self, msg: str, **kwargs) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, msg, **kwargs)


class LogAggregator:
    """
    Aggregates logs for analysis and monitoring.
    """

    def __init__(self):
        """Initialize log aggregator."""
        self.logs: list[Dict[str, Any]] = []
        self.handler = logging.StreamHandler()
        self.handler.setFormatter(JSONFormatter())

    def attach_to_logger(self, logger_name: str) -> None:
        """
        Attach aggregator to logger.

        Args:
            logger_name: Logger name
        """
        logger = logging.getLogger(logger_name)
        logger.addHandler(self.handler)

    def get_logs_by_level(self, level: str) -> list[Dict]:
        """Get logs by level."""
        return [log for log in self.logs if log.get('level') == level]

    def get_logs_by_module(self, module: str) -> list[Dict]:
        """Get logs by module."""
        return [log for log in self.logs if log.get('module') == module]

    def export_json(self) -> str:
        """Export logs as JSON."""
        return json.dumps(self.logs, indent=2, default=str)

    def export_csv(self, filepath: str) -> None:
        """Export logs as CSV."""
        import csv

        if not self.logs:
            return

        keys = self.logs[0].keys()

        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(self.logs)


def setup_logging(log_level: str = "INFO",
                  json_format: bool = False,
                  log_file: Optional[str] = None) -> ContextLogger:
    """
    Setup structured logging for GPS system.

    Args:
        log_level: Logging level
        json_format: Use JSON format
        log_file: Optional log file path

    Returns:
        Configured context logger
    """
    # Create logger
    logger = ContextLogger('gps-system')

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)

    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)

    console_handler.setLevel(log_level)
    logging.getLogger().addHandler(console_handler)
    logging.getLogger().setLevel(log_level)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)

        if json_format:
            file_handler.setFormatter(JSONFormatter())
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)

        file_handler.setLevel(log_level)
        logging.getLogger().addHandler(file_handler)

    return logger
