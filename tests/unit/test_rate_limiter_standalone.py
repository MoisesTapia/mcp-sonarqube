"""Standalone unit tests for rate limiter."""

import asyncio
import pytest
import time
import sys
from pathlib import Path

# Add src to path to import directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Import directly to avoid Pydantic issues
from sonarqube_client.rate_limiter import RateLimiter


class TestRateLimiter:
    """Test cases for RateLimiter."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(max_requests=10, time_window=60)
        
        assert limiter.max_requests == 10
        assert limiter.time_window == 60
        assert limiter.burst_size == 10
        assert limiter.tokens == 10

    @pytest.mark.asyncio
    async def test_acquire_tokens_success(self):
        """Test successful token acquisition."""
        limiter = RateLimiter(max_requests=10, time_window=60)
        
        # Should be able to acquire tokens
        result = await limiter.acquire(5)
        assert result is True
        assert limiter.tokens == 5

    @pytest.mark.asyncio
    async def test_acquire_tokens_insufficient(self):
        """Test token acquisition when insufficient tokens."""
        limiter = RateLimiter(max_requests=10, time_window=60)
        
        # Exhaust tokens
        await limiter.acquire(10)
        
        # Should fail to acquire more tokens
        result = await limiter.acquire(1)
        assert result is False
        assert limiter.tokens == 0

    def test_get_status(self):
        """Test getting rate limiter status."""
        limiter = RateLimiter(max_requests=10, time_window=60)
        
        status = limiter.get_status()
        
        assert "available_tokens" in status
        assert "max_tokens" in status
        assert "utilization_percent" in status
        assert "time_since_refill" in status
        
        assert status["available_tokens"] == 10
        assert status["max_tokens"] == 10
        assert status["utilization_percent"] == 0.0