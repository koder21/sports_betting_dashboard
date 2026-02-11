"""
Metrics logging for scraper performance monitoring.
Tracks execution times, success rates, and error patterns.
"""

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field, asdict


logger = logging.getLogger(__name__)


@dataclass
class MetricEvent:
    """Single metric event."""
    operation: str
    duration_seconds: float
    success: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class MetricsCollector:
    """Collect and report metrics on scraper performance."""
    
    def __init__(self):
        self.events: list[MetricEvent] = []
        self.operations_summary: dict[str, dict] = {}
    
    @asynccontextmanager
    async def measure(
        self,
        operation: str,
        metadata: Optional[dict] = None,
    ):
        """
        Context manager to measure operation performance.
        
        Usage:
            async with metrics.measure("scrape_nba_games", {"sport": "NBA"}):
                # ... operation code ...
        """
        start_time = time.time()
        metadata = metadata or {}
        
        try:
            yield
            duration = time.time() - start_time
            event = MetricEvent(
                operation=operation,
                duration_seconds=duration,
                success=True,
                metadata=metadata,
            )
            self._record_event(event)
            logger.info(
                f"✓ {operation} completed in {duration:.2f}s",
                extra={"metric": event.to_dict()}
            )
        except Exception as e:
            duration = time.time() - start_time
            event = MetricEvent(
                operation=operation,
                duration_seconds=duration,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e),
                metadata=metadata,
            )
            self._record_event(event)
            logger.error(
                f"✗ {operation} failed after {duration:.2f}s: {type(e).__name__}: {e}",
                extra={"metric": event.to_dict()}
            )
            raise
    
    def _record_event(self, event: MetricEvent):
        """Record metric event and update summary."""
        self.events.append(event)
        self._update_summary(event)
    
    def _update_summary(self, event: MetricEvent):
        """Update operation summary statistics."""
        op = event.operation
        if op not in self.operations_summary:
            self.operations_summary[op] = {
                "count": 0,
                "success": 0,
                "failed": 0,
                "total_duration": 0.0,
                "avg_duration": 0.0,
                "min_duration": float('inf'),
                "max_duration": 0.0,
            }
        
        summary = self.operations_summary[op]
        summary["count"] += 1
        summary["total_duration"] += event.duration_seconds
        summary["avg_duration"] = summary["total_duration"] / summary["count"]
        summary["min_duration"] = min(summary["min_duration"], event.duration_seconds)
        summary["max_duration"] = max(summary["max_duration"], event.duration_seconds)
        
        if event.success:
            summary["success"] += 1
        else:
            summary["failed"] += 1
    
    def get_summary(self) -> dict:
        """Get performance summary for all operations."""
        return {
            op: {
                **summary,
                "success_rate": f"{(summary['success'] / summary['count'] * 100):.1f}%"
                if summary['count'] > 0 else "N/A",
            }
            for op, summary in self.operations_summary.items()
        }
    
    def get_operation_summary(self, operation: str) -> Optional[dict]:
        """Get summary for specific operation."""
        if operation not in self.operations_summary:
            return None
        
        summary = self.operations_summary[operation]
        return {
            **summary,
            "success_rate": f"{(summary['success'] / summary['count'] * 100):.1f}%"
            if summary['count'] > 0 else "N/A",
        }
    
    def log_summary(self):
        """Log performance summary to logger."""
        logger.info("=" * 60)
        logger.info("SCRAPER PERFORMANCE SUMMARY")
        logger.info("=" * 60)
        
        summary = self.get_summary()
        for op, stats in summary.items():
            logger.info(
                f"{op}: "
                f"Calls={stats['count']}, "
                f"Success={stats['success']}, "
                f"Failed={stats['failed']}, "
                f"AvgTime={stats['avg_duration']:.2f}s, "
                f"MinTime={stats['min_duration']:.2f}s, "
                f"MaxTime={stats['max_duration']:.2f}s, "
                f"SuccessRate={stats['success_rate']}"
            )
        
        logger.info("=" * 60)


# Global metrics collector
metrics_collector = MetricsCollector()
