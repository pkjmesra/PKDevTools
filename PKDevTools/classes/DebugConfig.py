# -*- coding: utf-8 -*-
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
"""

"""
Debug Configuration Manager for Selective Logging
=================================================

This module provides a comprehensive configuration management system for
selective debug logging across multiple packages (PKBrokers, PKScreener,
PKNSETools, etc.). It allows debug filters to be defined in configuration
files and applied to the logging system at runtime.

Key Features:
------------
- **Multiple Config Formats**: Support for JSON, YAML, and INI configuration files
- **Environment Variable Overrides**: Override any config setting via environment variables
- **Hot Reloading**: Automatically detect and apply config file changes at runtime
- **Dynamic Updates**: Programmatically update configuration on the fly
- **Filter Categories**: Filter debug logs by package, module, class, function, or file
- **Export Functionality**: Save current configuration to any supported format
"""

import os
import json
import time
import threading
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Union, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    import configparser
    INI_AVAILABLE = True
except ImportError:
    INI_AVAILABLE = False

from PKDevTools.classes.log import (
    enable_debug_for, 
    disable_debug_for, 
    reset_debug_filters,
    set_selective_debug,
    default_logger
)


class ConfigFormat(Enum):
    """Supported configuration file formats."""
    JSON = 'json'
    YAML = 'yaml'
    YML = 'yml'
    INI = 'ini'
    ENV = 'env'


@dataclass
class DebugFilters:
    """
    Data class representing debug filter configuration.
    
    Attributes:
        packages: Set of top-level package names (e.g., 'PKBrokers', 'PKScreener')
        modules: Set of full module paths (e.g., 'PKBrokers.bot.tickbot')
        classes: Set of class names (e.g., 'KiteTokenWatcher')
        functions: Set of function names (e.g., 'process_tick')
        files: Set of source file names (e.g., 'kiteTokenWatcher.py')
    """
    packages: Set[str] = field(default_factory=set)
    modules: Set[str] = field(default_factory=set)
    classes: Set[str] = field(default_factory=set)
    functions: Set[str] = field(default_factory=set)
    files: Set[str] = field(default_factory=set)
    
    def is_empty(self) -> bool:
        """Check if all filters are empty."""
        return not (self.packages or self.modules or self.classes or 
                   self.functions or self.files)
    
    def add_from_dict(self, data: Dict[str, List[str]]):
        """
        Add filters from a dictionary.
        
        Args:
            data: Dictionary with keys matching filter types
        """
        for key, values in data.items():
            if key in ['packages', 'modules', 'classes', 'functions', 'files']:
                current_set = getattr(self, key)
                if isinstance(values, list):
                    current_set.update(values)
                elif isinstance(values, str):
                    current_set.add(values)
    
    def to_dict(self) -> Dict[str, List[str]]:
        """Convert to dictionary for serialization."""
        return {
            'packages': sorted(list(self.packages)),
            'modules': sorted(list(self.modules)),
            'classes': sorted(list(self.classes)),
            'functions': sorted(list(self.functions)),
            'files': sorted(list(self.files)),
        }


@dataclass
class DebugConfig:
    """
    Complete debug configuration for selective logging.
    
    Attributes:
        enabled: Master switch to enable/disable all debug logging
        selective_debug: When True, only filtered components show debug logs
        filters: DebugFilters instance containing all filter definitions
        watch_for_changes: Enable automatic reloading when config file changes
        watch_interval: Seconds between checks for file changes (default: 5)
        config_file: Path to the configuration file (if loaded from file)
    """
    enabled: bool = True
    selective_debug: bool = True
    filters: DebugFilters = field(default_factory=DebugFilters)
    watch_for_changes: bool = False
    watch_interval: int = 5  # seconds
    config_file: Optional[str] = None
    
    def apply(self):
        """
        Apply this configuration to the logging system.
        
        This method activates the configuration by:
        1. Setting the selective debug mode
        2. Resetting any existing filters
        3. Enabling debug for all configured filter targets
        """
        # Set selective debug mode
        set_selective_debug(self.selective_debug)
        
        # Reset existing filters
        reset_debug_filters()
        
        # Apply new filters if debug is enabled
        if self.enabled:
            filters = self.filters
            
            # Apply each filter type
            for package in filters.packages:
                enable_debug_for('package', package)
            
            for module in filters.modules:
                enable_debug_for('module', module)
            
            for class_name in filters.classes:
                enable_debug_for('class', class_name)
            
            for function in filters.functions:
                enable_debug_for('function', function)
            
            for file_name in filters.files:
                enable_debug_for('file', file_name)
            
            logger = default_logger()
            logger.debug(f"Applied debug filters: {filters.to_dict()}")


class DebugConfigManager:
    """
    Manages debug configuration from various sources with hot-reloading support.
    
    Features:
    - Load config from JSON/YAML/INI files
    - Environment variable overrides at runtime
    - Hot reloading with file watching thread
    - Dynamic configuration updates
    - Config export to any supported format
    - Thread-safe operations with proper locking
    
    Environment Variables:
    ---------------------
    - `PK_DEBUG_ENABLED`: Override enabled flag (true/false/1/0/yes/no)
    - `PK_DEBUG_SELECTIVE`: Override selective_debug flag (true/false)
    - `PK_DEBUG_PACKAGES`: Comma-separated list of packages
    - `PK_DEBUG_MODULES`: Comma-separated list of modules
    - `PK_DEBUG_CLASSES`: Comma-separated list of classes
    - `PK_DEBUG_FUNCTIONS`: Comma-separated list of functions
    - `PK_DEBUG_FILES`: Comma-separated list of files
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the config manager.
        
        Args:
            config_path: Path to configuration file (optional). If provided,
                        the configuration will be loaded immediately.
        """
        self.config_path = config_path
        self.config = DebugConfig()
        self._watch_thread: Optional[threading.Thread] = None
        self._stop_watching = threading.Event()
        self._lock = threading.Lock()
        self.logger = default_logger()
        
        # Load initial config if path provided
        if config_path:
            self.load_from_file(config_path)
    
    def load_from_file(self, file_path: str) -> DebugConfig:
        """
        Load configuration from a file.
        
        Args:
            file_path: Path to config file (JSON, YAML, or INI)
            
        Returns:
            Loaded DebugConfig instance
            
        Raises:
            ValueError: If file format not supported or file not found
            ImportError: If required library for format is not installed
        """
        file_path = os.path.expanduser(file_path)
        if not os.path.exists(file_path):
            raise ValueError(f"Config file not found: {file_path}")
        
        # Determine format from extension
        ext = Path(file_path).suffix.lower().lstrip('.')
        try:
            format_type = ConfigFormat(ext)
        except ValueError:
            raise ValueError(f"Unsupported config file format: {ext}")
        
        # Load based on format
        with open(file_path, 'r') as f:
            if format_type == ConfigFormat.JSON:
                data = json.load(f)
            elif format_type in [ConfigFormat.YAML, ConfigFormat.YML]:
                if not YAML_AVAILABLE:
                    raise ImportError("PyYAML is required for YAML config files. Install with: pip install pyyaml")
                data = yaml.safe_load(f)
            elif format_type == ConfigFormat.INI:
                if not INI_AVAILABLE:
                    raise ImportError("configparser is required for INI config files")
                config_parser = configparser.ConfigParser()
                config_parser.read_file(f)
                data = self._parse_ini(config_parser)
            else:
                raise ValueError(f"Unsupported format: {format_type}")
        
        # Convert to DebugConfig
        config = self._parse_config_dict(data)
        config.config_file = file_path
        
        with self._lock:
            self.config = config
        
        # Apply the configuration
        config.apply()
        
        # Start watching if enabled
        if config.watch_for_changes:
            self.start_watching()
        
        return config
    
    def _parse_ini(self, config_parser: 'configparser.ConfigParser') -> Dict[str, Any]:
        """
        Parse INI format into a dictionary.
        
        Args:
            config_parser: Loaded ConfigParser instance
            
        Returns:
            Dictionary representation of config
        """
        result = {}
        
        # Main debug section
        if config_parser.has_section('debug'):
            result['enabled'] = config_parser.getboolean('debug', 'enabled', fallback=True)
            result['selective_debug'] = config_parser.getboolean('debug', 'selective_debug', fallback=True)
            result['watch_for_changes'] = config_parser.getboolean('debug', 'watch_for_changes', fallback=False)
            result['watch_interval'] = config_parser.getint('debug', 'watch_interval', fallback=5)
        
        # Filters section
        filters = {}
        if config_parser.has_section('filters'):
            for key in ['packages', 'modules', 'classes', 'functions', 'files']:
                if config_parser.has_option('filters', key):
                    value = config_parser.get('filters', key)
                    # Parse comma-separated list
                    if value.strip():
                        filters[key] = [item.strip() for item in value.split(',')]
                    else:
                        filters[key] = []
        
        if filters:
            result['filters'] = filters
        
        return result
    
    def _parse_config_dict(self, data: Dict[str, Any]) -> DebugConfig:
        """
        Parse dictionary into DebugConfig.
        
        Args:
            data: Dictionary with config data
            
        Returns:
            DebugConfig instance
        """
        config = DebugConfig()
        
        # Basic settings
        config.enabled = data.get('enabled', True)
        config.selective_debug = data.get('selective_debug', True)
        config.watch_for_changes = data.get('watch_for_changes', False)
        config.watch_interval = data.get('watch_interval', 5)
        
        # Filters
        filters_data = data.get('filters', {})
        config.filters.add_from_dict(filters_data)
        
        # Environment variable overrides
        self._apply_env_overrides(config)
        
        return config
    
    def _apply_env_overrides(self, config: DebugConfig):
        """
        Apply environment variable overrides to config.
        
        Environment variables take precedence over file configuration.
        Boolean values accept: true/false, 1/0, yes/no
        List values are comma-separated strings.
            PK_DEBUG_ENABLED: Override enabled flag (true/false)
            PK_DEBUG_SELECTIVE: Override selective_debug flag (true/false)
            PK_DEBUG_PACKAGES: Comma-separated list of packages
            PK_DEBUG_MODULES: Comma-separated list of modules
            PK_DEBUG_CLASSES: Comma-separated list of classes
            PK_DEBUG_FUNCTIONS: Comma-separated list of functions
            PK_DEBUG_FILES: Comma-separated list of files
        """
        # Boolean overrides
        env_enabled = os.environ.get('PK_DEBUG_ENABLED')
        if env_enabled is not None:
            config.enabled = env_enabled.lower() in ('true', '1', 'yes')
        
        env_selective = os.environ.get('PK_DEBUG_SELECTIVE')
        if env_selective is not None:
            config.selective_debug = env_selective.lower() in ('true', '1', 'yes')
        
        # List overrides
        env_packages = os.environ.get('PK_DEBUG_PACKAGES')
        if env_packages:
            config.filters.packages.update(p.strip() for p in env_packages.split(',') if p.strip())
        
        env_modules = os.environ.get('PK_DEBUG_MODULES')
        if env_modules:
            config.filters.modules.update(m.strip() for m in env_modules.split(',') if m.strip())
        
        env_classes = os.environ.get('PK_DEBUG_CLASSES')
        if env_classes:
            config.filters.classes.update(c.strip() for c in env_classes.split(',') if c.strip())
        
        env_functions = os.environ.get('PK_DEBUG_FUNCTIONS')
        if env_functions:
            config.filters.functions.update(f.strip() for f in env_functions.split(',') if f.strip())
        
        env_files = os.environ.get('PK_DEBUG_FILES')
        if env_files:
            config.filters.files.update(f.strip() for f in env_files.split(',') if f.strip())
    
    def start_watching(self, interval: Optional[int] = None):
        """
        Start watching config file for changes.
        
        Launches a background thread that periodically checks the config file's
        modification time and reloads it when changes are detected.
        
        Args:
            interval: Watch interval in seconds (overrides config.watch_interval)
        """
        if not self.config.config_file:
            self.logger.warning("No config file to watch")
            return
        
        if self._watch_thread and self._watch_thread.is_alive():
            self.logger.debug("Watch thread already running")
            return
        
        watch_interval = interval or self.config.watch_interval
        
        self._stop_watching.clear()
        self._watch_thread = threading.Thread(
            target=self._watch_loop,
            args=(self.config.config_file, watch_interval),
            daemon=True,
            name="DebugConfigWatcher"
        )
        self._watch_thread.start()
        self.logger.info(f"Started watching config file: {self.config.config_file}")
    
    def stop_watching(self):
        """Stop watching config file for changes."""
        if self._watch_thread:
            self._stop_watching.set()
            self._watch_thread.join(timeout=2)
            self.logger.info("Stopped watching config file")
    
    def _watch_loop(self, file_path: str, interval: int):
        """
        Main watch loop that checks for file changes.
        
        Args:
            file_path: Path to config file
            interval: Check interval in seconds
        """
        last_mtime = os.path.getmtime(file_path)
        
        while not self._stop_watching.is_set():
            time.sleep(interval)
            
            try:
                current_mtime = os.path.getmtime(file_path)
                if current_mtime != last_mtime:
                    self.logger.info(f"Config file changed: {file_path}")
                    try:
                        # Reload config
                        new_config = self.load_from_file(file_path)
                        last_mtime = current_mtime
                        self.logger.debug("Config reloaded successfully")
                    except Exception as e:
                        self.logger.error(f"Failed to reload config: {e}")
            except Exception as e:
                self.logger.error(f"Error watching config file: {e}")
    
    def get_current_config(self) -> DebugConfig:
        """Get the current configuration."""
        with self._lock:
            return self.config
    
    def update_config(self, **kwargs) -> DebugConfig:
        """
        Update configuration dynamically.
        
        This method allows programmatic updates to the configuration at runtime.
        Changes are applied immediately.
        
        Args:
            **kwargs: Configuration attributes to update.
                     Supported keys: enabled, selective_debug, watch_for_changes,
                     watch_interval
            
        Returns:
            Updated DebugConfig instance
        """
        with self._lock:
            # Update basic attributes
            for key, value in kwargs.items():
                if hasattr(self.config, key) and key != 'filters':
                    setattr(self.config, key, value)
            
            # Apply the updated config
            self.config.apply()
            
            return self.config
    
    def save_config(self, file_path: Optional[str] = None, format: str = 'json'):
        """
        Save current configuration to a file.
        
        Exports the current configuration to a file in the specified format.
        The directory will be created if it doesn't exist.
        
        Args:
            file_path: Path to save to (defaults to loaded config path)
            format: Output format ('json', 'yaml', 'ini')
            
        Raises:
            ValueError: If no save path specified and no config file loaded
            ImportError: If required library for format is not installed
        """
        save_path = file_path or self.config.config_file
        if not save_path:
            raise ValueError("No save path specified")
        
        config_dict = {
            'enabled': self.config.enabled,
            'selective_debug': self.config.selective_debug,
            'watch_for_changes': self.config.watch_for_changes,
            'watch_interval': self.config.watch_interval,
            'filters': self.config.filters.to_dict(),
        }
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        
        # Write based on format
        with open(save_path, 'w') as f:
            if format == 'json':
                json.dump(config_dict, f, indent=2)
            elif format in ['yaml', 'yml']:
                if not YAML_AVAILABLE:
                    raise ImportError("PyYAML is required for YAML output. Install with: pip install pyyaml")
                yaml.dump(config_dict, f, default_flow_style=False)
            elif format == 'ini':
                self._save_as_ini(config_dict, f)
            else:
                raise ValueError(f"Unsupported format: {format}")
        
        self.logger.info(f"Saved config to: {save_path}")
    
    def _save_as_ini(self, config_dict: Dict, file_handle):
        """
        Save config as INI format.
        
        Args:
            config_dict: Configuration dictionary
            file_handle: Open file handle to write to
        """
        config_parser = configparser.ConfigParser()
        
        # Debug section
        config_parser.add_section('debug')
        config_parser.set('debug', 'enabled', str(config_dict['enabled']))
        config_parser.set('debug', 'selective_debug', str(config_dict['selective_debug']))
        config_parser.set('debug', 'watch_for_changes', str(config_dict['watch_for_changes']))
        config_parser.set('debug', 'watch_interval', str(config_dict['watch_interval']))
        
        # Filters section
        if config_dict['filters']:
            config_parser.add_section('filters')
            for key, values in config_dict['filters'].items():
                if values:
                    config_parser.set('filters', key, ', '.join(values))
                else:
                    config_parser.set('filters', key, '')
        
        config_parser.write(file_handle)


# Global config manager instance
_debug_config_manager: Optional[DebugConfigManager] = None


def get_debug_config_manager(config_path: Optional[str] = None) -> DebugConfigManager:
    """
    Get or create the global debug config manager.
    
    This function implements a singleton pattern for the DebugConfigManager.
    The first call with a config_path will set the path for all future calls.
    
    Args:
        config_path: Path to config file (used only on first call)
        
    Returns:
        DebugConfigManager singleton instance
    """
    global _debug_config_manager
    if _debug_config_manager is None:
        _debug_config_manager = DebugConfigManager(config_path)
    return _debug_config_manager


def load_debug_config(config_path: str) -> DebugConfig:
    """
    Convenience function to load debug config and apply filters.
    
    This is a simplified interface for the most common use case: loading
    a configuration file and applying it to the logging system.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Loaded DebugConfig instance
    """
    manager = get_debug_config_manager(config_path)
    return manager.config


# Example configuration files (commented out for reference):

# JSON config (debug_config.json):
"""
{
    "enabled": true,
    "selective_debug": true,
    "watch_for_changes": true,
    "watch_interval": 5,
    "filters": {
        "packages": ["PKBrokers", "PKScreener"],
        "modules": ["PKBrokers.bot.tickbot", "PKScreener.classes.AssetsManager"],
        "classes": ["KiteTokenWatcher", "InMemoryCandleStore"],
        "functions": ["process_tick", "export_daily_candles"],
        "files": ["kiteTokenWatcher.py", "dataSharingManager.py"]
    }
}
"""

# YAML config (debug_config.yaml):
"""
enabled: true
selective_debug: true
watch_for_changes: true
watch_interval: 5
filters:
  packages:
    - PKBrokers
    - PKScreener
  modules:
    - PKBrokers.bot.tickbot
    - PKScreener.classes.AssetsManager
  classes:
    - KiteTokenWatcher
    - InMemoryCandleStore
  functions:
    - process_tick
    - export_daily_candles
  files:
    - kiteTokenWatcher.py
    - dataSharingManager.py
"""

# INI config (debug_config.ini):
"""
[debug]
enabled = true
selective_debug = true
watch_for_changes = true
watch_interval = 5

[filters]
packages = PKBrokers, PKScreener
modules = PKBrokers.bot.tickbot, PKScreener.classes.AssetsManager
classes = KiteTokenWatcher, InMemoryCandleStore
functions = process_tick, export_daily_candles
files = kiteTokenWatcher.py, dataSharingManager.py
"""

"""
# Usage examples:
if __name__ == "__main__":
    # Example 1: Load from JSON
    manager = DebugConfigManager()
    config = manager.load_from_file("debug_config.json")
    
    # Example 2: Load from YAML
    # config = manager.load_from_file("debug_config.yaml")
    
    # Example 3: Load from INI
    # config = manager.load_from_file("debug_config.ini")
    
    print(f"Loaded config: {config}")
    print(f"Filters: {config.filters.to_dict()}")
    
    # Example 4: Update config dynamically
    manager.update_config(enabled=False)
    
    # Example 5: Save current config
    # manager.save_config("debug_config_backup.json")
    
    # Example 6: Environment variable overrides
    # $ export PK_DEBUG_PACKAGES="PKBrokers,PKNSETools"
    # $ export PK_DEBUG_FUNCTIONS="process_tick,calculate_rsi"
    
    # Keep the script running to watch for changes
    if config.watch_for_changes:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            manager.stop_watching()
"""