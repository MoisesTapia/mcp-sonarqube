"""Rate limiting utilities for SonarQube client."""

import asyncio
import time
from typing import Dict, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Token bucket rate limiter for API requests."""

    def __init__(
        self,
        max_requests: int = 100,
        time_window: int = 60,
        burst_size: Optional[int] = None,
    ):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
            burst_size: Maximum burst size (defaults to max_requests)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.burst_size = burst_size or max_requests
        
        # Token bucket implementation
        self.tokens = self.burst_size
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
        
        logger.info(
            f"Rate limiter initialized: {max_requests} req/{time_window}s, burst: {self.burst_size}"
        )

    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False if rate limited
        """
        async with self._lock:
            await self._refill_tokens()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                logger.debug(f"Rate limit: acquired {tokens} tokens, {self.tokens} remaining")
                return True
            else:
                logger.warning(f"Rate limit exceeded: need {tokens}, have {self.tokens}")
                return False

    async def wait_for_tokens(self, tokens: int = 1) -> None:
        """
        Wait until tokens are available.

        Args:
            tokens: Number of tokens needed
        """
        while not await self.acquire(tokens):
            # Calculate wait time until next refill
            wait_time = self._calculate_wait_time(tokens)
            logger.info(f"Rate limited, waiting {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)

    async def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        if elapsed > 0:
            # Calculate tokens to add based on rate
            tokens_to_add = (elapsed / self.time_window) * self.max_requests
            self.tokens = min(self.burst_size, self.tokens + tokens_to_add)
            self.last_refill = now

    def _calculate_wait_time(self, tokens_needed: int) -> float:
        """Calculate time to wait for tokens to be available."""
        tokens_deficit = tokens_needed - self.tokens
        if tokens_deficit <= 0:
            return 0.0
        
        # Time to generate the needed tokens
        return (tokens_deficit / self.max_requests) * self.time_window

    def get_status(self) -> Dict[str, float]:
        """Get current rate limiter status."""
        return {
            "available_tokens": self.tokens,
            "max_tokens": self.burst_size,
            "utilization_percent": ((self.burst_size - self.tokens) / self.burst_size) * 100,
            "time_since_refill": time.time() - self.last_refill,
        }