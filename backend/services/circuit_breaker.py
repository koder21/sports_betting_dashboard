"""
Circuit breaker pattern implementation for resilient API calls.
Prevents cascading failures by stopping requests to failing endpoints.
"""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Any


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"      # Endpoint failing, requests rejected
    HALF_OPEN = "half_open"  # Testing if endpoint recovered


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Too many failures, reject requests
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before testing recovery (HALF_OPEN)
            expected_exception: Exception type to catch and count as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.last_open_time: datetime | None = None
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try recovering."""
        if self.last_open_time is None:
            return False
        elapsed = (datetime.now() - self.last_open_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Async function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Function result or None if circuit is open
            
        Raises:
            Exception: If circuit is open (service unavailable)
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception(f"Circuit breaker OPEN for {recovery_timeout}s")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.last_open_time = datetime.now()
    
    def get_status(self) -> dict:
        """Get current circuit breaker status."""
        return {
            "state": self.state.value,
            "failures": self.failure_count,
            "threshold": self.failure_threshold,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
        }


class CircuitBreakerManager:
    """Manage multiple circuit breakers for different endpoints."""
    
    def __init__(self):
        self.breakers: dict[str, CircuitBreaker] = {}
    
    def get_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
    ) -> CircuitBreaker:
        """Get or create circuit breaker for endpoint."""
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
            )
        return self.breakers[name]
    
    async def call(
        self,
        breaker_name: str,
        func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """Call function with circuit breaker protection."""
        breaker = self.get_breaker(breaker_name)
        return await breaker.call(func, *args, **kwargs)
    
    def get_all_status(self) -> dict[str, dict]:
        """Get status of all circuit breakers."""
        return {
            name: breaker.get_status()
            for name, breaker in self.breakers.items()
        }


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()
