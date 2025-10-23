"""Unit tests for rate limiter."""

import asyncio
import pytest
import time

from src.sonarqube_client.rate_limiter import RateLimiter


class TestRateLimiter:
    """Test cases for RateLimiter."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(max_requests=10, time_window=60)
        
        assert limiter.max_requests == 10
        assert limiter.time_window == 60
        assert limiter.burst_size == 10
        assert limiter.tokens == 10

    def test_rate_limiter_custom_burst(self):
        """Test rate limiter with custom burst size."""
        limiter = RateLimiter(max_requests=10, time_window=60, burst_size=20)
        
        assert limiter.max_requests == 10
        assert limiter.burst_size == 20
        assert limiter.tokens == 20

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

    @pytest.mark.asyncio
    async def test_token_refill(self):
        """Test token refill over time."""
        limiter = RateLimiter(max_requests=10, time_window=1)  # 1 second window
        
        # Exhaust tokens
        await limiter.acquire(10)
        assert limiter.tokens == 0
        
        # Wait for refill (simulate time passage)
        limiter.last_refill = time.time() - 0.5  # 0.5 seconds ago
        await limiter._refill_tokens()
        
        # Should have some tokens back
        assert limiter.tokens > 0

    @pytest.mark.asyncio
    async def test_wait_for_tokens(self):
        """Test waiting for tokens to become available."""
        limiter = RateLimiter(max_requests=100, time_window=1)  # Fast refill
        
        # Exhaust tokens
        await limiter.acquire(100)
        
        # This should wait and then succeed
        start_time = time.time()
        await limiter.wait_for_tokens(1)
        end_time = time.time()
        
        # Should have waited some time
        assert end_time > start_time

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

    def test_calculate_wait_time(self):
        """Test wait time calculation."""
        limiter = RateLimiter(max_requests=10, time_window=60)
        
        # Exhaust tokens
        limiter.tokens = 0
        
        # Calculate wait time for 5 tokens
        wait_time = limiter._calculate_wait_time(5)
        
        # Should be 30 seconds (5/10 * 60)
        assert wait_time == 30.0

    def test_calculate_wait_time_no_wait(self):
        """Test wait time calculation when no wait needed."""
        limiter = RateLimiter(max_requests=10, time_window=60)
        
        # Have enough tokens
        limiter.tokens = 10
        
        # Calculate wait time for 5 tokens
        wait_time = limiter._calculate_wait_time(5)
        
        # Should be 0 (no wait needed)
        assert wait_time == 0.0