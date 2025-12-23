"""
Tests for PKScalableDataFetcher

This module tests the scalable data fetcher that uses GitHub as the primary
data source for stock data.
"""

import json
import os
import tempfile
import time
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class TestPKScalableDataFetcher:
    """Tests for PKScalableDataFetcher class."""
    
    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        import importlib
        module = importlib.import_module('PKDevTools.classes.PKScalableDataFetcher')
        module.PKScalableDataFetcher._instance = None
        yield
        module.PKScalableDataFetcher._instance = None
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_singleton_pattern(self, temp_cache_dir):
        """Test that PKScalableDataFetcher follows singleton pattern."""
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        fetcher1 = PKScalableDataFetcher(cache_dir=temp_cache_dir)
        fetcher2 = PKScalableDataFetcher(cache_dir=temp_cache_dir)
        
        assert fetcher1 is fetcher2
    
    def test_get_scalable_fetcher(self, temp_cache_dir):
        """Test the get_scalable_fetcher accessor."""
        from PKDevTools.classes.PKScalableDataFetcher import (
            PKScalableDataFetcher,
            get_scalable_fetcher,
        )
        
        fetcher = get_scalable_fetcher()
        assert fetcher is not None
        assert isinstance(fetcher, PKScalableDataFetcher)
    
    def test_cache_directory_created(self, temp_cache_dir):
        """Test that cache directory is created on init."""
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        cache_path = os.path.join(temp_cache_dir, "subcache")
        fetcher = PKScalableDataFetcher(cache_dir=cache_path)
        
        assert os.path.exists(cache_path)
    
    def test_is_fresh(self, temp_cache_dir):
        """Test _is_fresh method."""
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        fetcher = PKScalableDataFetcher(cache_dir=temp_cache_dir)
        
        # Recent timestamp should be fresh
        assert fetcher._is_fresh(time.time())
        
        # Old timestamp should not be fresh
        old_time = time.time() - 600  # 10 minutes ago
        assert not fetcher._is_fresh(old_time)
    
    def test_is_stale_usable(self, temp_cache_dir):
        """Test _is_stale_usable method."""
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        fetcher = PKScalableDataFetcher(cache_dir=temp_cache_dir)
        
        # Recent stale data should be usable
        stale_time = time.time() - 600  # 10 minutes ago
        assert fetcher._is_stale_usable(stale_time)
        
        # Very old data should not be usable
        very_old_time = time.time() - 7200  # 2 hours ago
        assert not fetcher._is_stale_usable(very_old_time)
    
    def test_save_and_get_from_disk_cache(self, temp_cache_dir):
        """Test disk cache save and load."""
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        fetcher = PKScalableDataFetcher(cache_dir=temp_cache_dir)
        
        test_data = {"symbol": "RELIANCE", "price": 2500.0}
        fetcher._save_to_disk_cache("test.json", test_data)
        
        loaded = fetcher._get_from_disk_cache("test.json")
        assert loaded is not None
        assert loaded["symbol"] == "RELIANCE"
        assert loaded["price"] == 2500.0
    
    def test_get_from_disk_cache_not_found(self, temp_cache_dir):
        """Test disk cache returns None for non-existent file."""
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        fetcher = PKScalableDataFetcher(cache_dir=temp_cache_dir)
        
        result = fetcher._get_from_disk_cache("nonexistent.json")
        assert result is None
    
    def test_get_from_memory_cache_fresh(self, temp_cache_dir):
        """Test memory cache returns fresh data."""
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        fetcher = PKScalableDataFetcher(cache_dir=temp_cache_dir)
        
        test_data = {"symbol": "TCS", "price": 3800.0}
        fetcher._candles_cache["test_key"] = test_data
        fetcher._cache_timestamps["test_key"] = time.time()
        
        result = fetcher._get_from_memory_cache("test_key")
        assert result is not None
        assert result["symbol"] == "TCS"
    
    def test_get_from_memory_cache_stale(self, temp_cache_dir):
        """Test memory cache returns None for stale data."""
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        fetcher = PKScalableDataFetcher(cache_dir=temp_cache_dir)
        
        test_data = {"symbol": "INFY", "price": 1600.0}
        fetcher._candles_cache["test_key"] = test_data
        fetcher._cache_timestamps["test_key"] = time.time() - 600  # 10 min ago
        
        result = fetcher._get_from_memory_cache("test_key")
        assert result is None
    
    def test_clear_cache(self, temp_cache_dir):
        """Test cache clearing."""
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        fetcher = PKScalableDataFetcher(cache_dir=temp_cache_dir)
        
        # Add data to caches
        fetcher._candles_cache["key1"] = {"data": 1}
        fetcher._cache_timestamps["key1"] = time.time()
        fetcher._metadata_cache = {"version": "1.0"}
        fetcher._save_to_disk_cache("disk_test.json", {"disk": "data"})
        
        # Clear
        fetcher.clear_cache()
        
        assert len(fetcher._candles_cache) == 0
        assert len(fetcher._cache_timestamps) == 0
        assert fetcher._metadata_cache is None
    
    def test_get_stats(self, temp_cache_dir):
        """Test statistics retrieval."""
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        fetcher = PKScalableDataFetcher(cache_dir=temp_cache_dir)
        
        stats = fetcher.get_stats()
        
        assert "github_hits" in stats
        assert "cache_hits" in stats
        assert "failures" in stats
        assert "cache_size" in stats
    
    @patch('PKDevTools.classes.PKScalableDataFetcher.urlopen')
    def test_fetch_from_github_path_success(self, mock_urlopen, temp_cache_dir):
        """Test successful GitHub fetch."""
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"test": "data"}).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        fetcher = PKScalableDataFetcher(cache_dir=temp_cache_dir)
        result = fetcher._fetch_from_github_path("test.json", compressed=False)
        
        assert result is not None
        assert result["test"] == "data"
    
    @patch('PKDevTools.classes.PKScalableDataFetcher.urlopen')
    def test_fetch_from_github_path_error(self, mock_urlopen, temp_cache_dir):
        """Test GitHub fetch error handling."""
        from urllib.error import URLError
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        mock_urlopen.side_effect = URLError("Connection failed")
        
        fetcher = PKScalableDataFetcher(cache_dir=temp_cache_dir)
        result = fetcher._fetch_from_github_path("test.json", compressed=False)
        
        assert result is None
    
    def test_get_stock_data_returns_dataframe(self, temp_cache_dir):
        """Test get_stock_data returns DataFrame for valid data."""
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        fetcher = PKScalableDataFetcher(cache_dir=temp_cache_dir)
        
        # Mock the get_latest_candles method
        fetcher._candles_cache["candles_latest"] = {
            "_cache_time": time.time(),
            "RELIANCE": {
                "symbol": "RELIANCE",
                "candles": {
                    "day": [
                        {"open": 2500, "high": 2550, "low": 2480, "close": 2530, "volume": 1000000}
                    ]
                }
            }
        }
        fetcher._cache_timestamps["candles_latest"] = time.time()
        
        df = fetcher.get_stock_data("RELIANCE", interval="day", count=1)
        
        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert "open" in df.columns or "Open" in df.columns
    
    def test_get_stock_data_symbol_not_found(self, temp_cache_dir):
        """Test get_stock_data returns None for unknown symbol."""
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        fetcher = PKScalableDataFetcher(cache_dir=temp_cache_dir)
        
        # Empty candle cache
        fetcher._candles_cache["candles_latest"] = {
            "_cache_time": time.time(),
        }
        fetcher._cache_timestamps["candles_latest"] = time.time()
        
        df = fetcher.get_stock_data("UNKNOWN_SYMBOL", interval="day", count=1)
        
        assert df is None
    
    def test_get_multiple_stocks(self, temp_cache_dir):
        """Test get_multiple_stocks returns dict of DataFrames."""
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        fetcher = PKScalableDataFetcher(cache_dir=temp_cache_dir)
        
        # Mock candle data
        fetcher._candles_cache["candles_latest"] = {
            "_cache_time": time.time(),
            "RELIANCE": {
                "candles": {
                    "day": [{"open": 2500, "high": 2550, "low": 2480, "close": 2530, "volume": 1000000}]
                }
            },
            "TCS": {
                "candles": {
                    "day": [{"open": 3800, "high": 3850, "low": 3780, "close": 3820, "volume": 500000}]
                }
            }
        }
        fetcher._cache_timestamps["candles_latest"] = time.time()
        
        result = fetcher.get_multiple_stocks(["RELIANCE", "TCS"], interval="day", count=1)
        
        assert isinstance(result, dict)
        assert "RELIANCE" in result or "TCS" in result
    
    def test_health_check(self, temp_cache_dir):
        """Test health check method."""
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        fetcher = PKScalableDataFetcher(cache_dir=temp_cache_dir)
        
        # Create a disk cache file to test
        fetcher._save_to_disk_cache("candles_latest.json", {"_cache_time": time.time()})
        
        health = fetcher.health_check()
        
        assert "github_raw" in health
        assert "cache_available" in health
        assert health["cache_available"] is True
    
    def test_is_data_fresh_no_metadata(self, temp_cache_dir):
        """Test is_data_fresh returns False when no metadata."""
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        fetcher = PKScalableDataFetcher(cache_dir=temp_cache_dir)
        
        # No metadata available
        result = fetcher.is_data_fresh(max_age_seconds=900)
        
        assert result is False
    
    def test_constants(self):
        """Test that module constants are defined correctly."""
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        assert PKScalableDataFetcher.CACHE_TTL_SECONDS == 300
        assert PKScalableDataFetcher.STALE_CACHE_MAX_SECONDS == 3600
        assert "github" in PKScalableDataFetcher.GITHUB_RAW_BASE.lower()


class TestIntegration:
    """Integration tests for PKScalableDataFetcher."""
    
    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        import importlib
        module = importlib.import_module('PKDevTools.classes.PKScalableDataFetcher')
        module.PKScalableDataFetcher._instance = None
        yield
        module.PKScalableDataFetcher._instance = None
    
    def test_full_cache_workflow(self):
        """Test full cache workflow: miss -> fetch -> hit."""
        import tempfile
        from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
        
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = PKScalableDataFetcher(cache_dir=tmpdir)
            
            # Initial stats
            initial_stats = fetcher.get_stats()
            
            # Simulate data fetch (would normally come from GitHub)
            test_data = {
                "_cache_time": time.time(),
                "SBIN": {
                    "candles": {
                        "day": [{"open": 600, "high": 620, "low": 590, "close": 610, "volume": 5000000}]
                    }
                }
            }
            
            # Save to cache
            fetcher._save_to_disk_cache("candles_latest.json", test_data)
            fetcher._candles_cache["candles_latest"] = test_data
            fetcher._cache_timestamps["candles_latest"] = time.time()
            
            # Fetch should hit cache
            df = fetcher.get_stock_data("SBIN", interval="day")
            
            assert df is not None
