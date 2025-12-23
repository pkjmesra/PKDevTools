"""
The MIT License (MIT)

Copyright (c) 2023 pkjmesra

Tests for PKDataProvider class.
"""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd


class TestPKDataProvider:
    """Tests for PKDataProvider class."""
    
    @pytest.fixture
    def provider(self):
        """Create a fresh provider instance."""
        from PKDevTools.classes.PKDataProvider import PKDataProvider
        
        # Reset singleton for testing
        PKDataProvider._instance = None
        return PKDataProvider()
    
    def test_singleton_pattern(self):
        """Test that PKDataProvider is a singleton."""
        from PKDevTools.classes.PKDataProvider import PKDataProvider
        
        PKDataProvider._instance = None
        provider1 = PKDataProvider()
        provider2 = PKDataProvider()
        
        assert provider1 is provider2
    
    def test_is_realtime_available_no_pkbrokers(self, provider):
        """Test is_realtime_available when PKBrokers not available."""
        with patch('PKDevTools.classes.PKDataProvider._get_candle_store', return_value=None):
            available = provider.is_realtime_available()
            
            assert available is False
    
    def test_is_realtime_available_with_empty_store(self, provider):
        """Test is_realtime_available when store has no instruments."""
        mock_store = MagicMock()
        mock_store.get_stats.return_value = {'instrument_count': 0}
        
        with patch('PKDevTools.classes.PKDataProvider._get_candle_store', return_value=mock_store):
            available = provider.is_realtime_available()
            
            assert available is False
    
    def test_get_stock_data_from_cache(self, provider):
        """Test get_stock_data uses cache."""
        cached_df = pd.DataFrame({'close': [100, 105]})
        
        # Manually populate cache
        import time
        cache_key = "SBIN_day_100"
        provider._cache[cache_key] = cached_df
        provider._cache_timestamps[cache_key] = time.time()
        
        result = provider.get_stock_data("SBIN", "day", 100)
        
        assert result is not None
        assert provider.stats['cache_hits'] >= 1
    
    def test_get_stock_data_no_sources(self, provider):
        """Test get_stock_data returns None when no data sources available."""
        with patch.object(provider, 'is_realtime_available', return_value=False):
            with patch.object(provider, '_get_from_pickle', return_value=None):
                result = provider.get_stock_data("SBIN", "day", 100, use_cache=False)
                
                assert result is None
                assert provider.stats['misses'] >= 1
    
    def test_get_multiple_stocks(self, provider):
        """Test get_multiple_stocks method."""
        mock_df = pd.DataFrame({'close': [100]})
        
        with patch.object(provider, 'get_stock_data', return_value=mock_df):
            result = provider.get_multiple_stocks(["SBIN", "INFY"], "day", 100)
            
            assert "SBIN" in result
            assert "INFY" in result
    
    def test_get_latest_price_no_realtime(self, provider):
        """Test get_latest_price falls back to stock data."""
        mock_df = pd.DataFrame({'close': [500.50]})
        
        with patch.object(provider, 'is_realtime_available', return_value=False):
            with patch.object(provider, 'get_stock_data', return_value=mock_df):
                price = provider.get_latest_price("SBIN")
                
                assert price == 500.50
    
    def test_get_latest_price_no_data(self, provider):
        """Test get_latest_price returns None when no data."""
        with patch.object(provider, 'is_realtime_available', return_value=False):
            with patch.object(provider, 'get_stock_data', return_value=None):
                price = provider.get_latest_price("SBIN")
                
                assert price is None
    
    def test_get_realtime_ohlcv_not_available(self, provider):
        """Test get_realtime_ohlcv when not available."""
        with patch.object(provider, 'is_realtime_available', return_value=False):
            result = provider.get_realtime_ohlcv("SBIN")
            
            assert result is None
    
    def test_get_all_realtime_data_not_available(self, provider):
        """Test get_all_realtime_data when not available."""
        with patch.object(provider, 'is_realtime_available', return_value=False):
            result = provider.get_all_realtime_data()
            
            assert result == {}
    
    def test_clear_cache(self, provider):
        """Test clear_cache method."""
        provider._cache['test'] = 'value'
        provider._cache_timestamps['test'] = 123
        
        provider.clear_cache()
        
        assert len(provider._cache) == 0
        assert len(provider._cache_timestamps) == 0
    
    def test_get_stats(self, provider):
        """Test get_stats method."""
        stats = provider.get_stats()
        
        assert 'realtime_hits' in stats
        assert 'pickle_hits' in stats
        assert 'cache_hits' in stats
        assert 'misses' in stats
        assert 'realtime_available' in stats
        assert 'pkbrokers_available' in stats
        assert 'cache_size' in stats
    
    def test_check_cache_expired(self, provider):
        """Test _check_cache with expired entry."""
        import time
        
        provider._cache['test'] = 'value'
        provider._cache_timestamps['test'] = time.time() - 1000  # Expired
        
        result = provider._check_cache('test')
        
        assert result is False
    
    def test_check_cache_valid(self, provider):
        """Test _check_cache with valid entry."""
        import time
        
        provider._cache['test'] = 'value'
        provider._cache_timestamps['test'] = time.time()
        
        result = provider._check_cache('test')
        
        assert result is True
    
    def test_check_cache_missing(self, provider):
        """Test _check_cache with missing entry."""
        result = provider._check_cache('nonexistent')
        
        assert result is False
    
    def test_update_cache(self, provider):
        """Test _update_cache method."""
        df = pd.DataFrame({'close': [100]})
        
        provider._update_cache('test_key', df)
        
        assert 'test_key' in provider._cache
        assert 'test_key' in provider._cache_timestamps
    
    def test_get_data_provider_function(self):
        """Test get_data_provider function."""
        from PKDevTools.classes.PKDataProvider import get_data_provider, PKDataProvider
        
        PKDataProvider._instance = None
        provider = get_data_provider()
        
        assert isinstance(provider, PKDataProvider)
    
    def test_load_from_ticks_json_not_found(self, provider):
        """Test _load_from_ticks_json when symbol not found."""
        import tempfile
        import json
        import os
        
        # Create temp ticks.json without our symbol
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'123': {'trading_symbol': 'OTHER', 'ohlcv': {}}}, f)
            temp_path = f.name
        
        try:
            result = provider._load_from_ticks_json('SBIN', temp_path)
            
            assert result is None
        finally:
            os.unlink(temp_path)
    
    def test_load_from_ticks_json_found(self, provider):
        """Test _load_from_ticks_json when symbol found."""
        import tempfile
        import json
        import os
        
        # Create temp ticks.json with our symbol
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                '123': {
                    'trading_symbol': 'SBIN',
                    'ohlcv': {
                        'open': 500,
                        'high': 510,
                        'low': 495,
                        'close': 505,
                        'volume': 100000
                    }
                }
            }, f)
            temp_path = f.name
        
        try:
            result = provider._load_from_ticks_json('SBIN', temp_path)
            
            assert result is not None
            assert 'open' in result.columns
            assert 'close' in result.columns
        finally:
            os.unlink(temp_path)


class TestPKDataProviderIntegration:
    """Integration tests for PKDataProvider."""
    
    def test_import_module(self):
        """Test module can be imported."""
        from PKDevTools.classes.PKDataProvider import PKDataProvider
        
        assert PKDataProvider is not None
    
    def test_pkbrokers_available_flag(self):
        """Test _PKBROKERS_AVAILABLE flag."""
        import importlib
        module = importlib.import_module('PKDevTools.classes.PKDataProvider')
        
        # Should be True or False based on installation (module-level variable)
        assert hasattr(module, '_PKBROKERS_AVAILABLE')
        assert isinstance(module._PKBROKERS_AVAILABLE, bool)
