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

PKScalableDataFetcher - Scalable Data Fetcher using GitHub as Data Layer
=========================================================================

This module provides a scalable data fetching mechanism that uses GitHub
as the primary data source instead of Telegram bot-to-bot communication.

Benefits:
    - No Telegram rate limits or file size limits
    - Parallel access from multiple workflows
    - 2-5 second latency vs 30-60 seconds
    - Git-backed durability
    - Works for GitHub Actions, Docker, and local CLI

Data Source Priority:
    1. Local cache (if fresh < 5 min)
    2. GitHub raw content (fastest, no rate limits)
    3. GitHub API (fallback)
    4. Telegram bot (last resort)

Example:
    >>> from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher
    >>> 
    >>> fetcher = PKScalableDataFetcher()
    >>> 
    >>> # Get latest candle data
    >>> data = fetcher.get_latest_candles()
    >>> 
    >>> # Get specific interval data
    >>> df = fetcher.get_candles_dataframe("RELIANCE", "5m")
"""

import gzip
import json
import os
import pickle
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

from PKDevTools.classes import Archiver
from PKDevTools.classes.log import default_logger


class PKScalableDataFetcher:
    """
    Scalable data fetcher that uses GitHub as primary data source.
    
    This class eliminates Telegram dependency for data transfer by using
    GitHub raw content URLs which have no rate limits and are accessible
    from anywhere.
    
    Attributes:
        GITHUB_RAW_BASE: Base URL for GitHub raw content
        CACHE_TTL_SECONDS: Cache time-to-live in seconds
        cache_dir: Local cache directory path
    """
    
    # GitHub raw content URLs (no API rate limits)
    GITHUB_RAW_BASE = "https://raw.githubusercontent.com/pkjmesra/PKScreener/actions-data-download"
    GITHUB_DATA_PATH = "results/Data"
    
    # Cache settings
    CACHE_TTL_SECONDS = 300  # 5 minutes
    STALE_CACHE_MAX_SECONDS = 3600  # 1 hour - use stale cache if fresh fetch fails
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, cache_dir: str = None):
        """
        Initialize the scalable data fetcher.
        
        Args:
            cache_dir: Directory for local cache (default: ~/.pkscreener/cache)
        """
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._initialized = True
        self.cache_dir = cache_dir or os.path.join(
            Archiver.get_user_data_dir(), "scalable_cache"
        )
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.logger = default_logger()
        self._metadata_cache: Optional[Dict] = None
        self._metadata_fetch_time: float = 0
        self._candles_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        
        # Statistics
        self.stats = {
            'github_hits': 0,
            'cache_hits': 0,
            'failures': 0,
            'last_fetch_time': 0,
        }
    
    # =========================================================================
    # Primary Data Access Methods
    # =========================================================================
    
    def get_latest_candles(self) -> Optional[Dict[str, Any]]:
        """
        Get latest candle data from the most efficient source.
        
        Returns:
            Dictionary with candle data for all instruments, or None
        """
        cache_key = "candles_latest"
        
        # 1. Check local cache
        cached = self._get_from_memory_cache(cache_key)
        if cached is not None:
            self.stats['cache_hits'] += 1
            return cached
        
        # 2. Check disk cache
        cached = self._get_from_disk_cache("candles_latest.json")
        if cached and self._is_fresh(cached.get("_cache_time", 0)):
            self._candles_cache[cache_key] = cached
            self._cache_timestamps[cache_key] = cached.get("_cache_time", time.time())
            self.stats['cache_hits'] += 1
            return cached
        
        # 3. Fetch from GitHub
        data = self._fetch_candles_from_github()
        if data:
            data["_cache_time"] = time.time()
            self._candles_cache[cache_key] = data
            self._cache_timestamps[cache_key] = time.time()
            self._save_to_disk_cache("candles_latest.json", data)
            self.stats['github_hits'] += 1
            self.stats['last_fetch_time'] = time.time()
            return data
        
        # 4. Return stale cache if available
        if cached and self._is_stale_usable(cached.get("_cache_time", 0)):
            self.logger.warning("Using stale cache data")
            return cached
        
        self.stats['failures'] += 1
        return None
    
    def get_ticks_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get current day's OHLCV summary for all instruments.
        
        Returns:
            Dictionary mapping instrument token/symbol to OHLCV data
        """
        return self._fetch_from_github_path("ticks.json", compressed=False)
    
    def get_stock_data(
        self,
        symbol: str,
        interval: str = "day",
        count: int = 100
    ) -> Optional[pd.DataFrame]:
        """
        Get stock data as DataFrame.
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE")
            interval: Candle interval (1m, 5m, 15m, 60m, day)
            count: Number of candles to return
            
        Returns:
            DataFrame with OHLCV columns or None
        """
        candles = self.get_latest_candles()
        if candles is None:
            return None
        
        # Find symbol in data
        symbol_data = candles.get(symbol) or candles.get(symbol.upper())
        if symbol_data is None:
            # Try searching by symbol in nested structure
            for key, data in candles.items():
                if isinstance(data, dict) and data.get("symbol") == symbol:
                    symbol_data = data
                    break
        
        if symbol_data is None:
            return None
        
        # Extract candles for the interval
        interval_candles = None
        if isinstance(symbol_data, dict):
            if "candles" in symbol_data:
                interval_candles = symbol_data["candles"].get(interval, [])
            elif interval in symbol_data:
                interval_candles = symbol_data[interval]
            else:
                interval_candles = [symbol_data]  # Single candle (day summary)
        elif isinstance(symbol_data, list):
            interval_candles = symbol_data
        
        if not interval_candles:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(interval_candles[-count:])
        
        # Ensure standard column names
        column_map = {
            'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume',
            'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'
        }
        df = df.rename(columns=column_map)
        
        # Set datetime index if timestamp available
        if 'timestamp' in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
            df = df.set_index('datetime')
        
        return df
    
    def get_multiple_stocks(
        self,
        symbols: List[str],
        interval: str = "day",
        count: int = 100
    ) -> Dict[str, pd.DataFrame]:
        """
        Get data for multiple stocks efficiently.
        
        Args:
            symbols: List of stock symbols
            interval: Candle interval
            count: Number of candles per stock
            
        Returns:
            Dictionary mapping symbol to DataFrame
        """
        result = {}
        
        # Single fetch for all data
        candles = self.get_latest_candles()
        if candles is None:
            return result
        
        for symbol in symbols:
            df = self.get_stock_data(symbol, interval, count)
            if df is not None and not df.empty:
                result[symbol] = df
        
        return result
    
    def get_metadata(self) -> Optional[Dict[str, Any]]:
        """
        Get data repository metadata.
        
        Returns:
            Metadata dictionary with last_update, version, etc.
        """
        if self._metadata_cache and self._is_fresh(self._metadata_fetch_time):
            return self._metadata_cache
        
        self._metadata_cache = self._fetch_from_github_path(
            "metadata.json", 
            compressed=False
        )
        self._metadata_fetch_time = time.time()
        return self._metadata_cache
    
    def is_data_fresh(self, max_age_seconds: int = 900) -> bool:
        """
        Check if the latest data is fresh enough.
        
        Args:
            max_age_seconds: Maximum acceptable age in seconds (default 15 min)
            
        Returns:
            bool: True if data is fresh
        """
        metadata = self.get_metadata()
        if not metadata:
            return False
        
        last_update = metadata.get("last_update")
        if not last_update:
            return False
        
        try:
            update_time = datetime.fromisoformat(last_update.replace("Z", "+00:00"))
            age = (datetime.now(update_time.tzinfo) - update_time).total_seconds()
            return age < max_age_seconds
        except (ValueError, TypeError):
            return False
    
    # =========================================================================
    # GitHub Fetch Methods
    # =========================================================================
    
    def _fetch_candles_from_github(self) -> Optional[Dict[str, Any]]:
        """Fetch candle data from GitHub."""
        # Try compressed version first
        data = self._fetch_from_github_path("candles_latest.json.gz", compressed=True)
        if data:
            return data
        
        # Try uncompressed
        data = self._fetch_from_github_path("candles_latest.json", compressed=False)
        if data:
            return data
        
        # Try pickle format
        return self._fetch_pickle_from_github()
    
    def _fetch_from_github_path(
        self,
        path: str,
        compressed: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch data from GitHub raw content.
        
        Args:
            path: File path relative to data directory
            compressed: Whether file is gzipped
            
        Returns:
            Parsed JSON data or None
        """
        url = f"{self.GITHUB_RAW_BASE}/{self.GITHUB_DATA_PATH}/{path}"
        
        try:
            request = Request(url, headers={
                "User-Agent": "PKScreener/2.0",
                "Accept": "application/json",
            })
            
            with urlopen(request, timeout=30) as response:
                content = response.read()
                
                if compressed and path.endswith(".gz"):
                    content = gzip.decompress(content)
                
                return json.loads(content.decode("utf-8"))
                
        except HTTPError as e:
            if e.code != 404:
                self.logger.debug(f"GitHub HTTP error for {path}: {e}")
        except URLError as e:
            self.logger.debug(f"GitHub URL error for {path}: {e}")
        except (json.JSONDecodeError, gzip.BadGzipFile) as e:
            self.logger.debug(f"GitHub parse error for {path}: {e}")
        except Exception as e:
            self.logger.debug(f"GitHub fetch error for {path}: {e}")
        
        return None
    
    def _fetch_pickle_from_github(self) -> Optional[Dict[str, Any]]:
        """Fetch pickle format data from GitHub for 24x7 availability."""
        # Try to get today's date-suffixed pickle
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Paths where pickle files are stored by w9-workflow-download-data.yml
        # The workflow saves to actions-data-download/ directory
        paths_to_try = [
            # Primary location: actions-data-download directory
            f"actions-data-download/stock_data_{today}.pkl",
            "actions-data-download/stock_data_1y_OHLC.pkl",
            # Fallback to results/Data
            f"{self.GITHUB_DATA_PATH}/stock_data_{today}.pkl",
            f"{self.GITHUB_DATA_PATH}/stock_data_latest.pkl",
        ]
        
        for path in paths_to_try:
            url = f"{self.GITHUB_RAW_BASE}/{path}"
            
            try:
                request = Request(url, headers={"User-Agent": "PKScreener/2.0"})
                
                with urlopen(request, timeout=60) as response:
                    content = response.read()
                    data = pickle.loads(content)
                    
                    if isinstance(data, dict) and len(data) > 0:
                        self.logger.debug(f"Loaded {len(data)} instruments from GitHub pickle: {path}")
                        return data
                    
            except Exception as e:
                self.logger.debug(f"Could not fetch pickle from {path}: {e}")
                continue
        
        return None
    
    # =========================================================================
    # Cache Methods
    # =========================================================================
    
    def _get_from_memory_cache(self, key: str) -> Optional[Any]:
        """Get data from in-memory cache if fresh."""
        if key in self._candles_cache:
            cache_time = self._cache_timestamps.get(key, 0)
            if self._is_fresh(cache_time):
                return self._candles_cache[key]
        return None
    
    def _get_from_disk_cache(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load data from disk cache."""
        cache_path = os.path.join(self.cache_dir, filename)
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        return None
    
    def _save_to_disk_cache(self, filename: str, data: Dict[str, Any]):
        """Save data to disk cache."""
        cache_path = os.path.join(self.cache_dir, filename)
        
        try:
            with open(cache_path, "w") as f:
                json.dump(data, f)
        except IOError as e:
            self.logger.debug(f"Cache save failed: {e}")
    
    def _is_fresh(self, cache_time: float) -> bool:
        """Check if cached data is still fresh."""
        return (time.time() - cache_time) < self.CACHE_TTL_SECONDS
    
    def _is_stale_usable(self, cache_time: float) -> bool:
        """Check if stale cached data is still usable as fallback."""
        return (time.time() - cache_time) < self.STALE_CACHE_MAX_SECONDS
    
    def clear_cache(self):
        """Clear all caches."""
        self._candles_cache.clear()
        self._cache_timestamps.clear()
        self._metadata_cache = None
        
        # Clear disk cache
        for filename in os.listdir(self.cache_dir):
            try:
                os.remove(os.path.join(self.cache_dir, filename))
            except OSError:
                pass
    
    # =========================================================================
    # Statistics and Diagnostics
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get fetcher statistics."""
        return {
            **self.stats,
            'cache_size': len(self._candles_cache),
            'disk_cache_files': len(os.listdir(self.cache_dir)),
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on data sources.
        
        Returns:
            Dictionary with health status for each source
        """
        health = {
            'github_raw': False,
            'github_api': False,
            'cache_available': False,
            'data_age_seconds': None,
        }
        
        # Check GitHub raw
        try:
            metadata = self._fetch_from_github_path("metadata.json", compressed=False)
            health['github_raw'] = metadata is not None
            
            if metadata and 'last_update' in metadata:
                try:
                    update_time = datetime.fromisoformat(
                        metadata['last_update'].replace("Z", "+00:00")
                    )
                    health['data_age_seconds'] = (
                        datetime.now(update_time.tzinfo) - update_time
                    ).total_seconds()
                except (ValueError, TypeError):
                    pass
        except Exception:
            pass
        
        # Check cache
        cached = self._get_from_disk_cache("candles_latest.json")
        health['cache_available'] = cached is not None
        
        return health


# Singleton accessor
def get_scalable_fetcher() -> PKScalableDataFetcher:
    """Get the global scalable data fetcher instance."""
    return PKScalableDataFetcher()
