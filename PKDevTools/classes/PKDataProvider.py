"""
The MIT License (MIT)

Copyright (c) 2023 pkjmesra

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

PKDataProvider - Unified High-Performance Stock Data Provider
==============================================================

This module provides a unified interface for fetching stock data from multiple
sources with priority order:

1. In-memory candle store (PKBrokers) - Real-time, highest priority
2. Local pickle files - Cached historical data
3. Remote GitHub pickle files - Fallback for historical data

This removes dependency on Yahoo Finance and provides instant access to data
during market hours via the in-memory candle store.

Example:
    >>> from PKDevTools.classes.PKDataProvider import PKDataProvider
    >>> 
    >>> provider = PKDataProvider()
    >>> 
    >>> # Get daily data for a stock
    >>> df = provider.get_stock_data("RELIANCE", interval="day", count=100)
    >>> 
    >>> # Get intraday data
    >>> df = provider.get_stock_data("RELIANCE", interval="5m", count=50)
    >>> 
    >>> # Check if real-time data is available
    >>> if provider.is_realtime_available():
    ...     df = provider.get_realtime_data("RELIANCE", "5m")
"""

import os
import pickle
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from PKDevTools.classes import Archiver
from PKDevTools.classes.log import default_logger
from PKDevTools.classes.PKDateUtilities import PKDateUtilities

# Try to import PKBrokers components
_PKBROKERS_AVAILABLE = False
_candle_store = None
_data_provider = None

try:
    from pkbrokers.kite.inMemoryCandleStore import get_candle_store
    from pkbrokers.kite.tickProcessor import HighPerformanceDataProvider
    _PKBROKERS_AVAILABLE = True
except ImportError:
    pass


def _get_candle_store():
    """Get the singleton candle store instance."""
    global _candle_store
    if _PKBROKERS_AVAILABLE and _candle_store is None:
        try:
            _candle_store = get_candle_store()
        except Exception:
            pass
    return _candle_store


def _get_data_provider():
    """Get the singleton data provider instance."""
    global _data_provider
    if _PKBROKERS_AVAILABLE and _data_provider is None:
        try:
            _data_provider = HighPerformanceDataProvider()
        except Exception:
            pass
    return _data_provider


class PKDataProvider:
    """
    Unified high-performance stock data provider.
    
    This class provides a single interface for fetching stock data from
    multiple sources with automatic fallback.
    
    Data Source Priority:
        1. In-memory candle store (real-time, during market hours)
        2. Local pickle files (cached historical data)
        3. Remote GitHub pickle files (fallback)
    
    Attributes:
        logger: Logger instance
        cache: Local cache for frequently accessed data
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the data provider."""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._initialized = True
        self.logger = default_logger()
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_ttl = 60  # Cache TTL in seconds
        
        # Statistics
        self.stats = {
            'realtime_hits': 0,
            'pickle_hits': 0,
            'cache_hits': 0,
            'misses': 0,
        }
    
    def is_realtime_available(self) -> bool:
        """
        Check if real-time data from candle store is available.
        
        Returns:
            bool: True if real-time data source is available
        """
        store = _get_candle_store()
        if store is None:
            return False
        
        # Check if store has recent data
        stats = store.get_stats()
        if stats.get('instrument_count', 0) == 0:
            return False
        
        # Check if last tick was recent (within 5 minutes)
        last_tick = stats.get('last_tick_time', 0)
        if last_tick > 0:
            import time
            age = time.time() - last_tick
            return age < 300  # 5 minutes
        
        return False
    
    def get_stock_data(
        self,
        symbol: str,
        interval: str = 'day',
        count: int = 100,
        start: datetime = None,
        end: datetime = None,
        use_cache: bool = True,
    ) -> Optional[pd.DataFrame]:
        """
        Get stock data from the best available source.
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE")
            interval: Candle interval ('1m', '2m', '3m', '4m', '5m', '10m', 
                      '15m', '30m', '60m', 'day')
            count: Number of candles to return
            start: Optional start date (for historical data)
            end: Optional end date (for historical data)
            use_cache: Whether to use local cache
            
        Returns:
            DataFrame with OHLCV data or None if not available
        """
        # Check cache first
        cache_key = f"{symbol}_{interval}_{count}"
        if use_cache and self._check_cache(cache_key):
            self.stats['cache_hits'] += 1
            return self._cache[cache_key]
        
        df = None
        
        # Try real-time source first (for intraday intervals)
        if self.is_realtime_available():
            df = self._get_from_realtime(symbol, interval, count)
            if df is not None and not df.empty:
                self.stats['realtime_hits'] += 1
                self._update_cache(cache_key, df)
                return df
        
        # Try local pickle files
        df = self._get_from_pickle(symbol, interval, count, start, end)
        if df is not None and not df.empty:
            self.stats['pickle_hits'] += 1
            self._update_cache(cache_key, df)
            return df
        
        self.stats['misses'] += 1
        return None
    
    def _get_from_realtime(
        self,
        symbol: str,
        interval: str,
        count: int,
    ) -> Optional[pd.DataFrame]:
        """Get data from real-time candle store."""
        provider = _get_data_provider()
        if provider is None:
            return None
        
        try:
            return provider.get_stock_data(symbol, interval, count)
        except Exception as e:
            self.logger.debug(f"Error getting realtime data for {symbol}: {e}")
            return None
    
    def _get_from_pickle(
        self,
        symbol: str,
        interval: str,
        count: int,
        start: datetime = None,
        end: datetime = None,
    ) -> Optional[pd.DataFrame]:
        """Get data from local or remote pickle files."""
        try:
            # Try local pickle first
            df = self._load_local_pickle(symbol, interval)
            
            if df is None or df.empty:
                # Try remote pickle
                df = self._load_remote_pickle(symbol, interval)
            
            if df is not None and not df.empty:
                # Filter by date range if specified
                if start is not None:
                    df = df[df.index >= start]
                if end is not None:
                    df = df[df.index <= end]
                
                # Return last 'count' rows
                return df.tail(count)
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error loading pickle for {symbol}: {e}")
            return None
    
    def _load_local_pickle(self, symbol: str, interval: str) -> Optional[pd.DataFrame]:
        """Load data from local pickle file."""
        try:
            # Try different pickle file patterns
            paths_to_try = []
            
            # Standard aftermarket data path
            exists, path = Archiver.afterMarketStockDataExists(date_suffix=True)
            if exists:
                paths_to_try.append(os.path.join(Archiver.get_user_data_dir(), path))
            
            # Check for ticks.json converted to DataFrame
            ticks_path = os.path.join(Archiver.get_user_data_dir(), "ticks.json")
            if os.path.exists(ticks_path):
                df = self._load_from_ticks_json(symbol, ticks_path)
                if df is not None:
                    return df
            
            # Try each path
            for file_path in paths_to_try:
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        data = pickle.load(f)
                    
                    if symbol in data:
                        stock_data = data[symbol]
                        
                        # Handle different data formats
                        if isinstance(stock_data, pd.DataFrame):
                            return stock_data
                        elif isinstance(stock_data, dict):
                            if 'data' in stock_data and 'columns' in stock_data:
                                df = pd.DataFrame(
                                    stock_data['data'],
                                    columns=stock_data['columns'],
                                    index=pd.to_datetime(stock_data.get('index', []))
                                )
                                return df
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error loading local pickle: {e}")
            return None
    
    def _load_from_ticks_json(self, symbol: str, file_path: str) -> Optional[pd.DataFrame]:
        """Load data from ticks.json file."""
        try:
            import json
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Find the symbol in ticks data
            for token_str, tick_data in data.items():
                if tick_data.get('trading_symbol') == symbol:
                    ohlcv = tick_data.get('ohlcv', {})
                    if ohlcv:
                        # Create single-row DataFrame with today's data
                        df = pd.DataFrame([{
                            'open': ohlcv.get('open', 0),
                            'high': ohlcv.get('high', 0),
                            'low': ohlcv.get('low', 0),
                            'close': ohlcv.get('close', 0),
                            'volume': ohlcv.get('volume', 0),
                        }], index=[pd.Timestamp.now()])
                        return df
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error loading ticks.json: {e}")
            return None
    
    def _load_remote_pickle(self, symbol: str, interval: str) -> Optional[pd.DataFrame]:
        """Load data from remote GitHub pickle file."""
        try:
            from PKDevTools.classes.Fetcher import fetcher
            
            # Construct GitHub raw URL
            date_str = PKDateUtilities.currentDateTime().strftime("%Y-%m-%d")
            base_url = "https://raw.githubusercontent.com/pkjmesra/PKScreener/actions-data-download/results/Data/"
            file_name = f"stock_data_{date_str}.pkl"
            url = f"{base_url}{file_name}"
            
            f = fetcher()
            response = f.fetchURL(url, timeout=10)
            
            if response is not None and response.status_code == 200:
                data = pickle.loads(response.content)
                
                if symbol in data:
                    stock_data = data[symbol]
                    if isinstance(stock_data, pd.DataFrame):
                        return stock_data
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error loading remote pickle: {e}")
            return None
    
    def _check_cache(self, key: str) -> bool:
        """Check if cache entry is valid."""
        import time
        
        if key not in self._cache:
            return False
        
        if key not in self._cache_timestamps:
            return False
        
        age = time.time() - self._cache_timestamps[key]
        return age < self._cache_ttl
    
    def _update_cache(self, key: str, df: pd.DataFrame):
        """Update cache with new data."""
        import time
        
        self._cache[key] = df.copy()
        self._cache_timestamps[key] = time.time()
    
    def clear_cache(self):
        """Clear the data cache."""
        self._cache.clear()
        self._cache_timestamps.clear()
    
    def get_multiple_stocks(
        self,
        symbols: List[str],
        interval: str = 'day',
        count: int = 100,
    ) -> Dict[str, pd.DataFrame]:
        """
        Get data for multiple stocks.
        
        Args:
            symbols: List of stock symbols
            interval: Candle interval
            count: Number of candles per stock
            
        Returns:
            Dictionary mapping symbol to DataFrame
        """
        result = {}
        for symbol in symbols:
            df = self.get_stock_data(symbol, interval, count)
            if df is not None and not df.empty:
                result[symbol] = df
        return result
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get the latest price for a stock."""
        if self.is_realtime_available():
            provider = _get_data_provider()
            if provider is not None:
                try:
                    return provider.get_current_price(symbol)
                except Exception:
                    pass
        
        # Fallback to getting from stock data
        df = self.get_stock_data(symbol, 'day', 1)
        if df is not None and not df.empty:
            return float(df['close'].iloc[-1])
        
        return None
    
    def get_realtime_ohlcv(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time OHLCV for a stock.
        
        Returns:
            Dictionary with open, high, low, close, volume or None
        """
        if not self.is_realtime_available():
            return None
        
        provider = _get_data_provider()
        if provider is None:
            return None
        
        try:
            return provider.get_current_ohlcv(symbol)
        except Exception:
            return None
    
    def get_all_realtime_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Get real-time OHLCV for all available stocks.
        
        Returns:
            Dictionary mapping symbol to OHLCV data
        """
        if not self.is_realtime_available():
            return {}
        
        provider = _get_data_provider()
        if provider is None:
            return {}
        
        try:
            return provider.get_market_data()
        except Exception:
            return {}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get provider statistics."""
        return {
            **self.stats,
            'realtime_available': self.is_realtime_available(),
            'pkbrokers_available': _PKBROKERS_AVAILABLE,
            'cache_size': len(self._cache),
        }


# Singleton accessor
def get_data_provider() -> PKDataProvider:
    """Get the global data provider instance."""
    return PKDataProvider()
