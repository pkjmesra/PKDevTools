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

import atexit
import inspect
import logging
import os
import sys
import tempfile
import traceback
import time
import warnings
from collections import OrderedDict
from functools import wraps
from multiprocessing import Lock as ProcessLock
from multiprocessing import current_process
from threading import Lock, get_ident

try:
    from collections.abc import Iterable
except ImportError:
    from collections import Iterable

from itertools import *

__all__ = [
    "redForegroundText",
    "greenForegroundText",
    "line_break",
    "clear_screen",
    "set_cursor",
    "setup_custom_logger",
    "default_logger",
    "log_to",
    "tracelog",
    "suppress_stdout_stderr",
    "enable_debug_for",
    "disable_debug_for",
    "reset_debug_filters",
    "set_selective_debug",
    "get_debug_filters",
    "is_debug_enabled_for",
    "print_debug_filter_status",
]
__trace__ = False
__filter__ = None
__DEBUG__ = False

# Global process-safe lock for singleton instantiation
_process_lock = ProcessLock()
# Thread-safe lock for within-process operations
_thread_lock = Lock()

# Process-specific handler tracking
_process_handlers = {}
# Module-specific logger instances
_module_loggers = {}

# Debug filters - which components should show debug logs
_debug_filters = {
    'packages': set(),      # e.g., {'PKBrokers', 'PKScreener'}
    'modules': set(),       # e.g., {'PKBrokers.bot.tickbot', 'PKScreener.classes.AssetsManager'}
    'classes': set(),       # e.g., {'KiteTokenWatcher', 'InMemoryCandleStore'}
    'functions': set(),     # e.g., {'process_tick', 'export_daily_candles'}
    'files': set(),         # e.g., {'kiteTokenWatcher.py', 'dataSharingManager.py'}
}

# Global debug mode flag - when True, only filtered components show debug logs
_selective_debug = True


def _init_debug_filters_from_env():
    """
    Initialize debug filters from environment variables.
    
    Environment Variables:
    -----------------------
    PKDEVTOOLS_DEBUG_PACKAGES : Comma-separated list of package names to debug
        Example: PKDEVTOOLS_DEBUG_PACKAGES="PKBrokers,PKScreener"
    
    PKDEVTOOLS_DEBUG_MODULES : Comma-separated list of module names to debug
        Example: PKDEVTOOLS_DEBUG_MODULES="PKScreener.classes.AssetsManager,PKBrokers.bot.tickbot"
    
    PKDEVTOOLS_DEBUG_CLASSES : Comma-separated list of class names to debug
        Example: PKDEVTOOLS_DEBUG_CLASSES="KiteTokenWatcher,InMemoryCandleStore"
    
    PKDEVTOOLS_DEBUG_FUNCTIONS : Comma-separated list of function names to debug
        Example: PKDEVTOOLS_DEBUG_FUNCTIONS="process_tick,export_daily_candles,loadStockData"
    
    PKDEVTOOLS_DEBUG_FILES : Comma-separated list of file names to debug
        Example: PKDEVTOOLS_DEBUG_FILES="AssetsManager.py,KiteTokenWatcher.py"
    
    PKDEVTOOLS_DEBUG_ALL : Set to '1', 'true', 'yes', or 'on' to disable selective filtering
        Example: PKDEVTOOLS_DEBUG_ALL=1
    
    PKDEVTOOLS_LOG_LEVEL : Override the default log level (0-50)
        Example: PKDEVTOOLS_LOG_LEVEL=10  # DEBUG level
    
    PKDEVTOOLS_TRACE_ENABLED : Set to '1', 'true', 'yes', or 'on' to enable tracing
        Example: PKDEVTOOLS_TRACE_ENABLED=1
    
    PKDEVTOOLS_SELECTIVE_DEBUG : Set to '0', 'false', 'no', or 'off' to disable selective debug
        Example: PKDEVTOOLS_SELECTIVE_DEBUG=0
    
    Usage Examples:
    ----------------
    # Debug only PKBrokers package
    $ export PKDEVTOOLS_DEBUG_PACKAGES="PKBrokers"
    $ python your_script.py
    
    # Debug specific module and class
    $ export PKDEVTOOLS_DEBUG_MODULES="PKScreener.classes.AssetsManager"
    $ export PKDEVTOOLS_DEBUG_CLASSES="KiteTokenWatcher"
    $ python your_script.py
    
    # Debug multiple items
    $ export PKDEVTOOLS_DEBUG_PACKAGES="PKBrokers,PKScreener"
    $ export PKDEVTOOLS_DEBUG_FUNCTIONS="process_tick,export_daily_candles"
    $ python your_script.py
    
    # Debug specific file
    $ export PKDEVTOOLS_DEBUG_FILES="AssetsManager.py,KiteTokenWatcher.py"
    $ python your_script.py
    
    # Enable all debug (disables selective filtering)
    $ export PKDEVTOOLS_DEBUG_ALL=1
    $ python your_script.py
    
    # Combine environment variables with code-based filters
    $ export PKDEVTOOLS_DEBUG_PACKAGES="PKScreener"
    $ python -c "from PKDevTools.classes.log import enable_debug_for; enable_debug_for('function', 'my_function')"
    """
    global _debug_filters, _selective_debug
    
    # Check if we should enable all debug (disable selective mode)
    debug_all = os.environ.get("PKDEVTOOLS_DEBUG_ALL", "").lower()
    if debug_all in ('1', 'true', 'yes', 'on'):
        _selective_debug = False
        # Try to log, but logger might not be initialized yet
        try:
            logger = default_logger()
            logger.info("Debug all enabled via PKDEVTOOLS_DEBUG_ALL environment variable")
        except:
            pass
        return
    
    # Check if selective debug should be disabled
    selective_debug_env = os.environ.get("PKDEVTOOLS_SELECTIVE_DEBUG", "")
    if selective_debug_env.lower() in ('0', 'false', 'no', 'off'):
        _selective_debug = False
        try:
            logger = default_logger()
            logger.info("Selective debug disabled via PKDEVTOOLS_SELECTIVE_DEBUG environment variable")
        except:
            pass
    
    # Parse each environment variable and add to filters
    env_mappings = {
        'PKDEVTOOLS_DEBUG_PACKAGES': 'packages',
        'PKDEVTOOLS_DEBUG_MODULES': 'modules', 
        'PKDEVTOOLS_DEBUG_CLASSES': 'classes',
        'PKDEVTOOLS_DEBUG_FUNCTIONS': 'functions',
        'PKDEVTOOLS_DEBUG_FILES': 'files',
    }
    
    for env_var, filter_type in env_mappings.items():
        value = os.environ.get(env_var, "")
        if value:
            # Split by comma and strip whitespace
            items = [item.strip() for item in value.split(',') if item.strip()]
            if items:
                _debug_filters[filter_type].update(items)
                # Try to log, but logger might not be initialized yet
                try:
                    logger = default_logger()
                    logger.debug(f"Added to {filter_type} from env {env_var}: {items}")
                except:
                    pass

# Initialize filters from environment variables when module loads
_init_debug_filters_from_env()


def enable_debug_for(component_type, component_names):
    """
    Enable debug logging for specific components.
    
    Args:
        component_type: One of 'package', 'module', 'class', 'function', 'file'
        component_names: Single name or list of names to enable debug for
    
    Examples:
        >>> enable_debug_for('package', 'PKBrokers')
        >>> enable_debug_for('module', 'PKBrokers.bot.tickbot')
        >>> enable_debug_for('class', 'KiteTokenWatcher')
        >>> enable_debug_for('function', 'process_tick')
        >>> enable_debug_for('file', 'kiteTokenWatcher.py')
        >>> enable_debug_for('function', ['process_tick', 'export_daily_candles'])
    """
    global _debug_filters
    
    if not isinstance(component_names, list):
        component_names = [component_names]
    
    plural_type = component_type + 's'
    if plural_type in _debug_filters:
        _debug_filters[plural_type].update(component_names)
        logger = default_logger()
        logger.debug(f"Enabled debug for {component_type}: {component_names}")


def disable_debug_for(component_type, component_names):
    """
    Disable debug logging for specific components.
    
    Args:
        component_type: One of 'package', 'module', 'class', 'function', 'file'
        component_names: Single name or list of names to disable debug for
    
    Examples:
        >>> disable_debug_for('package', 'PKBrokers')
        >>> disable_debug_for('module', 'PKBrokers.bot.tickbot')
        >>> disable_debug_for('class', 'KiteTokenWatcher')
        >>> disable_debug_for('function', 'process_tick')
        >>> disable_debug_for('file', 'kiteTokenWatcher.py')
    """
    global _debug_filters
    
    if not isinstance(component_names, list):
        component_names = [component_names]
    
    plural_type = component_type + 's'
    if plural_type in _debug_filters:
        for name in component_names:
            _debug_filters[plural_type].discard(name)
        logger = default_logger()
        logger.debug(f"Disabled debug for {component_type}: {component_names}")


def reset_debug_filters():
    """Reset all debug filters to empty."""
    global _debug_filters
    for key in _debug_filters:
        _debug_filters[key].clear()
    logger = default_logger()
    logger.debug("Reset all debug filters")


def set_selective_debug(enabled=True):
    """
    Enable or disable selective debug mode.
    
    When enabled, debug logs only appear for filtered components.
    When disabled, all debug logs appear (traditional behavior).
    
    Args:
        enabled: True to enable selective debug, False to disable
    """
    global _selective_debug
    _selective_debug = enabled
    logger = default_logger()
    logger.debug(f"Selective debug mode: {'enabled' if enabled else 'disabled'}")


def get_debug_filters():
    """
    Get current debug filter settings.
    
    Returns:
        dict: Current debug filters with lists of enabled components
        
    Example:
        >>> filters = get_debug_filters()
        >>> print(filters['packages'])
        ['PKBrokers', 'PKScreener']
    """
    global _debug_filters
    return {k: list(v) for k, v in _debug_filters.items()}


def is_debug_enabled_for(component_type, component_name):
    """
    Check if debug is enabled for a specific component.
    
    Args:
        component_type: One of 'package', 'module', 'class', 'function', 'file'
        component_name: Name of the component to check
    
    Returns:
        bool: True if debug is enabled for this component
        
    Example:
        >>> if is_debug_enabled_for('file', 'AssetsManager.py'):
        ...     print("Debug enabled for AssetsManager")
    """
    global _debug_filters, _selective_debug
    
    if not _selective_debug:
        return True
    
    plural_type = component_type + 's'
    if plural_type in _debug_filters:
        return component_name in _debug_filters[plural_type]
    
    return False


def print_debug_filter_status():
    """
    Print current debug filter configuration to console.
    
    This is useful for debugging and understanding what components
    are currently configured for debug logging.
    
    Example:
        >>> print_debug_filter_status()
        ============================================================
        DEBUG FILTER CONFIGURATION
        ============================================================
        Selective Debug Mode: ENABLED
        
        PACKAGES:
          - PKBrokers
          - PKScreener
        
        MODULES:
          - PKScreener.classes.AssetsManager
        
        FUNCTIONS:
          - process_tick
          - loadStockData
        ============================================================
    """
    global _debug_filters, _selective_debug
    
    print("\n" + "="*60)
    print("DEBUG FILTER CONFIGURATION")
    print("="*60)
    print(f"Selective Debug Mode: {'ENABLED' if _selective_debug else 'DISABLED (all debug enabled)'}")
    
    if _selective_debug:
        for filter_type, items in _debug_filters.items():
            if items:
                print(f"\n{filter_type.upper()}:")
                for item in sorted(items):
                    print(f"  - {item}")
            else:
                print(f"\n{filter_type.upper()}: (none)")
    print("="*60)


def _should_log_debug(caller_info):
    """
    Determine if debug logging should occur based on caller information.
    
    Args:
        caller_info: Dict with keys 'package', 'module', 'class', 'function', 'file'
    
    Returns:
        True if debug should be logged, False otherwise
    """
    global _selective_debug, _debug_filters
    
    # If selective debug is disabled, log everything
    if not _selective_debug:
        return True
    
    # Check each filter type
    if caller_info.get('package') and caller_info['package'] in _debug_filters['packages']:
        return True
    
    if caller_info.get('module') and caller_info['module'] in _debug_filters['modules']:
        return True
    
    if caller_info.get('class') and caller_info['class'] in _debug_filters['classes']:
        return True
    
    if caller_info.get('function') and caller_info['function'] in _debug_filters['functions']:
        return True
    
    if caller_info.get('file') and caller_info['file'] in _debug_filters['files']:
        return True
    
    # No filters matched
    return False


class colors:
    """
    ANSI color codes for terminal text formatting.

    Provides foreground (fg) and background (bg) color constants along with
    text formatting options like bold, underline, etc.

    Usage:
        colors.fg.red + "red text" + colors.reset
        colors.bg.green + "green background" + colors.reset
        colors.bold + "bold text" + colors.reset
    """

    reset = "\033[0m"
    bold = "\033[01m"
    disable = "\033[02m"
    underline = "\033[04m"
    reverse = "\033[07m"
    strikethrough = "\033[09m"
    invisible = "\033[08m"

    class fg:
        """Foreground text colors"""

        black = "\033[30m"
        red = "\033[31m"
        green = "\033[32m"
        orange = "\033[33m"
        blue = "\033[34m"
        purple = "\033[35m"
        cyan = "\033[36m"
        lightgrey = "\033[37m"
        darkgrey = "\033[90m"
        lightred = "\033[91m"
        lightgreen = "\033[92m"
        yellow = "\033[93m"
        lightblue = "\033[94m"
        pink = "\033[95m"
        lightcyan = "\033[96m"

    class bg:
        """Background colors"""

        black = "\033[40m"
        red = "\033[41m"
        green = "\033[42m"
        orange = "\033[43m"
        blue = "\033[44m"
        purple = "\033[45m"
        cyan = "\033[46m"
        lightgrey = "\033[47m"


class emptylogger:
    """
    Null logger implementation that performs no operations.

    Used when PKDevTools_Default_Log_Level environment variable is not set,
    providing a no-op interface that maintains API compatibility while
    avoiding any logging overhead.
    """

    @property
    def logger(self):
        """Returns None since this is a null logger"""
        return None

    @property
    def level(self):
        """Returns NOTSET level for null logger"""
        return logging.NOTSET

    @property
    def isDebugging(self):
        """Always returns False for null logger"""
        return False

    @level.setter
    def level(self, level):
        """No-op level setter"""
        return

    @staticmethod
    def getlogger(logger):
        """Returns a new emptylogger instance"""
        return emptylogger()

    def flush(self):
        """No-op flush method"""
        return

    def addHandlers(self, log_file_path=None, levelname=logging.NOTSET):
        """No-op handler addition method"""
        return None, None

    def debug(self, e, exc_info=False):
        """No-op debug logging"""
        return

    def info(self, line):
        """No-op info logging"""
        return

    def warn(self, line):
        """No-op warning logging"""
        return

    def warning(self, line):
        """No-op warning logging"""
        return
    
    def error(self, line):
        """No-op error logging"""
        return

    def setLevel(self, level):
        """No-op level setting"""
        return

    def critical(self, line):
        """No-op critical logging"""
        return

    def addHandler(self, hdl):
        """No-op handler addition"""
        return

    def removeHandler(self, hdl):
        """No-op handler removal"""
        return


class filterlogger:
    """
    Thread and process-safe logger implementation with module name detection.

    This logger handles both multi-threaded and multiprocessing environments
    by using appropriate locking mechanisms and process-specific configuration.
    
    Features:
    - Module-specific logger instances
    - Process-safe singleton instantiation per module
    - Thread-safe logging operations within processes
    - Automatic process-specific handler management
    - Filter-based message filtering
    - Caller information injection
    - Selective debug logging
    """

    def __new__(cls, module_name="PKDevTools"):
        """
        Process-safe singleton instantiation with module-specific loggers.

        Uses multiprocessing lock to ensure only one instance per module per process
        while allowing different instances in different processes.

        Args:
            module_name: Name of the module requesting the logger

        Returns:
            filterlogger instance for the specified module
        """
        with _process_lock:
            if module_name not in _module_loggers:
                _module_loggers[module_name] = super().__new__(cls)
                _module_loggers[module_name]._initialized = False
            return _module_loggers[module_name]

    def __init__(self, module_name="PKDevTools"):
        """
        Initialize the logger for the specified module.

        Args:
            module_name: Name of the module for logging (e.g., 'PKBrokers.bot.tickbot')
        """
        if getattr(self, "_initialized", False):
            return

        with _thread_lock:
            if getattr(self, "_initialized", False):
                return

            self._module_name = module_name
            # Create hierarchical logger name
            self._logger = logging.getLogger(module_name)
            self._initialized = True
            # Store process ID for handler management
            self._process_id = current_process().pid

    def __repr__(self):
        """String representation showing log level and debugging status"""
        return f"LogLevel: {self.level}, isDebugging: {self.isDebugging}"

    @property
    def logger(self):
        """Returns the underlying logging.Logger instance"""
        return self._logger

    @property
    def level(self):
        """Returns the current logging level"""
        return self.logger.level

    @property
    def isDebugging(self):
        """Returns True if logging level is DEBUG"""
        return self.level == logging.DEBUG

    @level.setter
    def level(self, level):
        """
        Sets the logging level with thread safety.

        Args:
            level: Logging level to set (e.g., logging.DEBUG, logging.INFO)
        """
        with _thread_lock:
            if level != self.level:
                self.logger.setLevel(level)

    @staticmethod
    def getlogger(module_name="PKDevTools"):
        """
        Factory method to get appropriate logger instance.

        Returns emptylogger if PKDevTools_Default_Log_Level is not set,
        otherwise returns a filterlogger instance for the specified module.

        Args:
            module_name: Name of the module requesting the logger

        Returns:
            emptylogger or filterlogger instance
        """
        if "PKDevTools_Default_Log_Level" not in os.environ.keys():
            return emptylogger()

        return filterlogger(module_name=module_name)

    def flush(self):
        """
        Flush all logger handlers.

        Thread-safe operation that attempts to flush all handlers,
        gracefully handling any exceptions.
        """
        with _thread_lock:
            for h in self.logger.handlers:
                try:
                    h.flush()
                except Exception:
                    # Continue flushing other handlers if one fails
                    pass

    def addHandlers(self, log_file_path=None, levelname=logging.NOTSET):
        """
        Add file and console handlers to the logger.

        Configures handlers specifically for the current process, ensuring
        each process has its own set of handlers without conflicts.

        Args:
            log_file_path: Path to log file (optional, auto-generated if None)
            levelname: Logging level for handlers

        Returns:
            Tuple of (console_handler, file_handler) instances
        """
        with _thread_lock:
            # Use process-specific tracking instead of global flag
            process_id = current_process().pid

            if process_id in _process_handlers:
                return _process_handlers[process_id]

            if log_file_path is None:
                log_file_path = os.path.join(
                    tempfile.gettempdir(), f"PKDevTools-logs-{process_id}.txt"
                )

            trace_formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

            # Remove existing handlers to avoid duplicates
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)

            # Create file handler (always created if logging is enabled)
            file_handler = logging.FileHandler(
                log_file_path, mode="a", encoding="utf-8"
            )
            file_handler.setFormatter(trace_formatter)
            file_handler.setLevel(levelname)
            self.logger.addHandler(file_handler)

            # Create console handler only if explicitly enabled
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(trace_formatter)
            console_handler.setLevel(levelname)
            self.logger.addHandler(console_handler)

            # Store handlers for this process
            _process_handlers[process_id] = (console_handler, file_handler)

            return console_handler, file_handler

    def _should_log(self, message):
        """
        Check if a message should be logged based on the global filter.

        Args:
            message: Message to check against filter

        Returns:
            True if message should be logged, False otherwise
        """
        global __filter__
        if __filter__ is None:
            return True
        return __filter__ in message.upper()

    def _get_caller_info(self):
        """
        Extract detailed caller information for debug filtering.
        Skips debugger, decorator, and framework frames.
        
        Returns:
            Dict with keys: package, module, class, function, file
        """
        caller_info = {
            'package': None,
            'module': None,
            'class': None,
            'function': None,
            'file': None
        }
        
        # Patterns to skip
        skip_patterns = [
            'debugpy', 'pydevd', 'ipykernel', 'IPython',  # Debuggers/IDEs
            'halo', 'decorator', 'functools', 'contextlib',  # Decorators
            'pkscreener.classes.PKAnalytics',  # Analytics decorators
            'PKDevTools.classes.log','log.py'  # Logging itself
        ]
        
        skip_functions = {
            'wrapper', 'decorator', 'timed', 'wrap', '__call__', 'new_func',
            'run', 'call', 'invoke', '_run_with_interrupt_thread'
        }
        
        try:
            # Walk up the stack to find the first relevant frame
            for i in range(1, len(inspect.stack())):
                frame_info = inspect.stack()[i]
                frame = frame_info[0]
                filename = frame_info.filename
                function_name = frame_info.function
                
                # Skip debugger frames
                should_skip = False
                for pattern in skip_patterns:
                    if pattern in filename.lower():
                        should_skip = True
                        break
                
                if should_skip:
                    continue
                
                # Skip wrapper functions
                if function_name in skip_functions:
                    continue
                
                # Check the module
                module = inspect.getmodule(frame)
                if module and module.__name__:
                    module_name = module.__name__
                    
                    # Skip decorator modules
                    should_skip = False
                    for pattern in skip_patterns:
                        if pattern in module_name.lower():
                            should_skip = True
                            break
                    
                    if should_skip:
                        continue
                    
                    # Found a real caller
                    caller_info['file'] = os.path.basename(filename)
                    caller_info['function'] = function_name
                    caller_info['module'] = module_name
                    caller_info['package'] = module_name.split('.')[0]
                    
                    # Try to get class name
                    if 'self' in frame.f_locals:
                        caller_info['class'] = frame.f_locals['self'].__class__.__name__
                    elif 'cls' in frame.f_locals:
                        caller_info['class'] = frame.f_locals['cls'].__name__
                    
                    # Also try to get class from module name if available
                    if not caller_info['class'] and '.' in module_name:
                        parts = module_name.split('.')
                        if len(parts) >= 2:
                            caller_info['class'] = parts[-1]
                    
                    break
                    
        except Exception:
            # Fallback to simple method
            try:
                for i in range(1, 4):
                    frame_info = inspect.stack()[i] if i < len(inspect.stack()) else None
                    if frame_info and 'debugpy' not in frame_info.filename:
                        caller_info['file'] = os.path.basename(frame_info.filename)
                        caller_info['function'] = frame_info.function
                        break
            except Exception:
                pass
        
        return caller_info

    def _format_message_with_caller_info(self, message):
        """
        Add caller information to the log message.

        Extracts filename, function name, and line number from the call stack
        and prepends this information to the message.

        Args:
            message: Original log message

        Returns:
            Formatted message with caller information
        """
        try:
            frame_2 = inspect.stack()[2]  # Skip logger method and caller
            filename_2 = os.path.basename(frame_2.filename)
            return f"{filename_2} - {frame_2.function} - {frame_2.lineno} - {message}"
        except Exception:
            return message

    def debug(self, e, exc_info=False):
        """
        Log a debug message - only if selective debug filters allow it.

        Args:
            e: Message or exception to log
            exc_info: If True, include exception information
        """
        if "PKDevTools_Default_Log_Level" not in os.environ.keys():
            return

        # Check if debug should be logged based on caller
        caller_info = self._get_caller_info()
        if not _should_log_debug(caller_info):
            return

        line = self._format_message_with_caller_info(str(e))

        if not self._should_log(line):
            return

        with _thread_lock:
            self.logger.debug(line, exc_info=exc_info)

    def info(self, line):
        """
        Log an info message (always logged, not filtered).

        Args:
            line: Message to log
        """
        if "PKDevTools_Default_Log_Level" not in os.environ.keys():
            return

        formatted_line = self._format_message_with_caller_info(line)

        if not self._should_log(formatted_line):
            return

        with _thread_lock:
            self.logger.info(formatted_line)

    def warning(self, line):
        self.warn(line=line)

    def warn(self, line):
        """
        Log a warning message (always logged, not filtered).

        Args:
            line: Message to log
        """
        if "PKDevTools_Default_Log_Level" not in os.environ.keys():
            return

        formatted_line = self._format_message_with_caller_info(line)
        if not self._should_log(formatted_line):
            return

        with _thread_lock:
            self.logger.warning(formatted_line)

    def error(self, line):
        """
        Log an error message (always logged, not filtered).

        Args:
            line: Message to log
        """
        if "PKDevTools_Default_Log_Level" not in os.environ.keys():
            return

        formatted_line = self._format_message_with_caller_info(line)
        if not self._should_log(formatted_line):
            return

        message = f"{formatted_line}:{traceback.format_exc()}"
        with _thread_lock:
            self.logger.error(message)
        
        try:
            from PKDevTools.classes.Telegram import send_message
            DEV_CHANNEL_ID = -1001785195297
            send_message(message=message, userID=DEV_CHANNEL_ID)
        except BaseException:
            pass

    def setLevel(self, level):
        """
        Set the logging level.

        Args:
            level: Logging level to set
        """
        with _thread_lock:
            self.logger.setLevel(level)

    def critical(self, line):
        """
        Log a critical message (always logged, not filtered).

        Args:
            line: Message to log
        """
        if "PKDevTools_Default_Log_Level" not in os.environ.keys():
            return

        if not self._should_log(line):
            return

        with _thread_lock:
            self.logger.critical(line)

    def addHandler(self, hdl):
        """
        Add a handler to the logger.

        Args:
            hdl: Handler to add
        """
        with _thread_lock:
            self.logger.addHandler(hdl)

    def removeHandler(self, hdl):
        """
        Remove a handler from the logger.

        Args:
            hdl: Handler to remove
        """
        with _thread_lock:
            self.logger.removeHandler(hdl)


def setup_custom_logger(
    name,
    levelname=logging.DEBUG,
    trace=False,
    log_file_path="PKDevTools-logs.txt",
    trace_file_path=None,
    filter=None,
    selective_debug=True,
):
    """
    Set up and configure a custom logger instance with optional tracing and selective debug.

    Environment variables override:
        PKDEVTOOLS_LOG_LEVEL: Override log level (0-50)
            Example: PKDEVTOOLS_LOG_LEVEL=10  # DEBUG level
        PKDEVTOOLS_TRACE_ENABLED: Set to '1' to enable tracing
            Example: PKDEVTOOLS_TRACE_ENABLED=1
        PKDEVTOOLS_SELECTIVE_DEBUG: Set to '0' to disable selective debug
            Example: PKDEVTOOLS_SELECTIVE_DEBUG=0

    Args:
        name: Name of the logger
        levelname: Default logging level
        trace: Enable tracing mode
        log_file_path: Path to main log file
        trace_file_path: Path to trace log file (optional, defaults to log_file_path + '.trace')
        filter: String filter for messages (only messages containing this string will be logged)
        selective_debug: Enable selective debug filtering

    Returns:
        Configured logger instance (emptylogger if logging disabled)

    Usage Examples:
        # Enable debug only for specific modules
        >>> setup_custom_logger("MyApp", selective_debug=True)
        >>> enable_debug_for('module', 'PKBrokers.bot.tickbot')
        >>> enable_debug_for('class', 'KiteTokenWatcher')
        >>> enable_debug_for('function', 'process_tick')

        # With environment variables
        $ export PKDEVTOOLS_DEBUG_MODULES="PKBrokers.bot.tickbot"
        $ export PKDEVTOOLS_LOG_LEVEL=10
        $ python your_script.py

        # Basic tracing:
        >>> from PKDevTools.classes.log import trace_log, setup_custom_logger
        >>> logger = setup_custom_logger("MyApp", trace=True)
        >>> trace_log("Starting database connection")
        >>> # ... do something
        >>> trace_log("Database connection established")

        # Function tracing with decorator:
        >>> from PKDevTools.classes.log import tracelog
        >>> @tracelog
        ... def calculate_price(amount, tax_rate=0.18):
        ...     return amount * (1 + tax_rate)

        # Class method tracing:
        >>> from PKDevTools.classes.log import tracemethod
        >>> @tracemethod
        ... class StockAnalyzer:
        ...     def calculate_rsi(self, prices):
        ...         # This method will be automatically traced
        ...         pass

        # Separate trace file:
        >>> logger = setup_custom_logger(
        ...     "MyApp", 
        ...     trace=True,
        ...     trace_file_path="/var/log/myapp/trace.log"
        ... )
    """
    global __trace__, __filter__, _selective_debug

    # Check environment variables for overrides
    env_trace = os.environ.get("PKDEVTOOLS_TRACE_ENABLED", "")
    if env_trace.lower() in ('1', 'true', 'yes', 'on'):
        trace = True
    
    env_selective = os.environ.get("PKDEVTOOLS_SELECTIVE_DEBUG", "")
    if env_selective.lower() in ('0', 'false', 'no', 'off'):
        selective_debug = False
    
    __trace__ = trace
    __filter__ = filter.upper() if filter else None
    _selective_debug = selective_debug

    # Only setup logging if environment variable is set
    if "PKDevTools_Default_Log_Level" not in os.environ.keys():
        return emptylogger()

    # Main application logger
    logger = filterlogger.getlogger(name)

    # Set the log level from environment variable
    try:
        # First check for PKDEVTOOLS_LOG_LEVEL override
        env_level = os.environ.get("PKDEVTOOLS_LOG_LEVEL")
        if env_level is not None:
            level = int(env_level)
        else:
            level = int(os.environ["PKDevTools_Default_Log_Level"])
        logger.level = level
    except (ValueError, KeyError):
        logger.level = levelname

    # Configure main logger handlers
    logger.addHandlers(log_file_path=log_file_path, levelname=logger.level)

    # Setup trace logger if tracing is enabled
    if trace:
        # Create a separate trace logger with hierarchical name
        trace_logger_name = f"{name}.trace"
        trace_logger = filterlogger.getlogger(trace_logger_name)
        trace_logger.level = logging.DEBUG  # Trace always uses DEBUG
        
        # Use separate trace file if specified
        trace_path = trace_file_path or f"{log_file_path}.trace"
        
        # Add handler for trace logger
        trace_formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - TRACE - %(message)s"
        )
        
        trace_handler = logging.FileHandler(trace_path, mode="a", encoding="utf-8")
        trace_handler.setFormatter(trace_formatter)
        trace_handler.setLevel(logging.DEBUG)
        trace_logger.logger.addHandler(trace_handler)
        
        logger.info(f"Tracing enabled - trace logs will be written to {trace_path}")
        
        # Store trace logger reference
        global _trace_logger
        _trace_logger = trace_logger

    # Turn off warnings
    warnings.simplefilter("ignore", DeprecationWarning)
    warnings.simplefilter("ignore", FutureWarning)

    return logger


def default_logger():
    """
    Get the default logger instance with automatic module detection.
    
    Detects the calling module's top-level package by walking up the stack
    and skipping debugger, IDE, decorator, and framework frames.
    
    Returns:
        filterlogger instance if logging enabled, otherwise emptylogger
    """
    if "PKDevTools_Default_Log_Level" not in os.environ.keys():
        return emptylogger()
    
    # Patterns to skip (debugger, IDE, decorators, frameworks)
    skip_patterns = [
        'debugpy',           # VSCode debugger
        'pydevd',            # PyDev debugger
        'ipykernel',         # Jupyter kernel
        'IPython',           # IPython
        'pytest',            # pytest framework
        'unittest',          # unittest framework
        'halo',              # Halo spinner decorator
        'decorator',         # Decorator module
        'functools',         # functools.wraps
        'contextlib',        # context managers
        'pkscreener.classes.PKAnalytics',  # Analytics decorators
        'PKDevTools.classes.log', 'log.py'          # Logging itself
    ]
    
    # Function names to skip (common wrapper names)
    skip_functions = {
        'wrapper', 'decorator', 'timed', 'wrap', '__call__', 'new_func',
        'run', 'call', 'invoke', '_run_with_interrupt_thread',  # Debugger internals
        '__main__',  # Main block
    }
    
    try:
        stack = inspect.stack()
        
        # Look for the first non-debugger, non-decorator frame
        for frame_info in stack:
            frame = frame_info[0]
            filename = frame_info.filename
            function_name = frame_info.function
            
            # Skip if the filename matches any debugger/IDE pattern
            should_skip = False
            for pattern in skip_patterns:
                if pattern in filename.lower():
                    should_skip = True
                    break
            
            if should_skip:
                continue
            
            # Skip common wrapper function names
            if function_name in skip_functions:
                continue
            
            # Get the module from the frame
            module = inspect.getmodule(frame)
            if module and module.__name__:
                module_name = module.__name__
                
                # Skip if module is in skip patterns
                should_skip = False
                for pattern in skip_patterns:
                    if pattern in module_name.lower():
                        should_skip = True
                        break
                
                if should_skip:
                    continue
                
                # Skip if the module name indicates a decorator
                if 'decorator' in module_name.lower() or 'wrapper' in module_name.lower():
                    continue
                
                # Extract the top-level package name
                top_level_package = module_name.split('.')[0]
                
                # For our known packages, use the appropriate naming
                if top_level_package in ['PKBrokers', 'PKScreener', 'PKNSETools', 'PKDevTools']:
                    # For our packages, use the full module path for clarity
                    parts = module_name.split('.')
                    if len(parts) > 3:
                        # Keep first 3 parts for readability (e.g., "PKScreener.classes.AssetsManager")
                        module_name = '.'.join(parts[:3])
                    elif len(parts) >= 2:
                        module_name = '.'.join(parts[:2])
                    else:
                        module_name = top_level_package
                else:
                    module_name = top_level_package
                
                # Final check: ensure we don't have an empty or invalid module name
                if module_name and module_name not in ['', 'PKDevTools', 'logging', '__main__']:
                    return filterlogger.getlogger(module_name)
        
        # If we couldn't find a good frame, use the caller's direct frame
        # but still try to skip debugger frames
        for frame_info in stack[1:5]:  # Check first few frames
            filename = frame_info.filename
            if 'debugpy' not in filename and 'pydevd' not in filename:
                module = inspect.getmodule(frame_info[0])
                if module and module.__name__:
                    module_name = module.__name__
                    top_level_package = module_name.split('.')[0]
                    if top_level_package in ['PKBrokers', 'PKScreener', 'PKNSETools', 'PKDevTools']:
                        parts = module_name.split('.')
                        if len(parts) > 3:
                            module_name = '.'.join(parts[:3])
                        return filterlogger.getlogger(module_name)
                    elif module_name not in ['PKDevTools', 'logging']:
                        return filterlogger.getlogger(module_name)
        
    except Exception as e:
        pass  # Fallback to PKDevTools
    
    return filterlogger.getlogger("PKDevTools")


def file_logger():
    """
    Get the file logger instance for tracing.

    Returns:
        filterlogger instance if logging enabled, otherwise emptylogger
    """
    if "PKDevTools_Default_Log_Level" in os.environ.keys():
        return filterlogger.getlogger("PKDevTools_file_logger")
    else:
        return emptylogger()


def trace_log(line, level=logging.DEBUG):
    """
    Log tracing information - only logs if tracing is enabled.
    
    Args:
        line: Tracing message to log
        level: Logging level for the trace (default: DEBUG)
    """
    global __trace__, _trace_logger
    if __trace__:
        try:
            # Get caller information
            frame = inspect.stack()[1]
            filename = os.path.basename(frame.filename)
            caller_info = f"{filename}:{frame.function}:{frame.lineno}"
            
            # Format trace message
            trace_msg = f"[TRACE] {caller_info} - {line}"
            
            # Use trace logger if available
            if _trace_logger:
                if level == logging.DEBUG:
                    _trace_logger.debug(trace_msg)
                elif level == logging.INFO:
                    _trace_logger.info(trace_msg)
                elif level == logging.WARNING:
                    _trace_logger.warning(trace_msg)
                else:
                    _trace_logger.debug(trace_msg)
            else:
                # Fallback to file_logger
                file_logger().info(trace_msg)
        except Exception:
            # If anything fails in tracing, don't break the application
            pass


# Global trace logger reference
_trace_logger = None


def flatten(line):
    """
    Flatten a nested iterable structure.

    Args:
        line: Iterable to flatten (can contain nested iterables)

    Yields:
        Flattened elements
    """
    for el in line:
        if isinstance(el, Iterable) and not isinstance(el, str):
            for sub in flatten(el):
                yield sub
        else:
            yield el


def getargnames(func):
    """
    Get all argument names from a function signature.

    Args:
        func: Function to inspect

    Returns:
        Iterator over argument names including varargs and kwargs
    """
    (
        args,
        varargs,
        varkw,
        defaults,
        kwonlyargs,
        kwonlydefaults,
        annotations,
    ) = inspect.getfullargspec(func)
    return chain(flatten(args), filter(None, [varargs, varkw]))


def getcallargs_ordered(func, *args, **kwargs):
    """
    Get function call arguments in ordered dictionary.

    Args:
        func: Function being called
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        OrderedDict of argument names to values
    """
    argdict = inspect.getcallargs(func, *args, **kwargs)
    return OrderedDict((name, argdict[name]) for name in getargnames(func))


def describe_call(func, *args, **kwargs):
    """
    Generate description of function call with arguments.

    Args:
        func: Function being called
        *args: Positional arguments
        **kwargs: Keyword arguments

    Yields:
        Lines describing the function call
    """
    yield "Calling %s with args:" % func.__name__
    for argname, argvalue in getcallargs_ordered(
        func, *args, **kwargs).items():
        yield "\t%s = %s" % (argname, repr(argvalue))


def log_to(logger_func):
    """
    Decorator to log function calls with arguments and timing.

    Args:
        logger_func: Function that accepts a string and logs it

    Returns:
        Decorator function
    """
    if logger_func is not None and "PKDevTools_Default_Log_Level" in os.environ.keys():

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if default_logger().level == logging.DEBUG or __trace__:
                    try:
                        frame = inspect.stack()[1]
                        filename = os.path.basename(frame.filename)
                        func_description = (
                            f"{filename} - {frame.function} - {frame.lineno}"
                        )

                        description = f"Calling {func.__name__} with args:"
                        for argname, argvalue in inspect.getcallargs(
                            func, *args, **kwargs
                        ).items():
                            description += f"\n\t{argname} = {repr(argvalue)}"

                        logger_func(f"{func_description} - {description}")
                        startTime = time.time()
                        ret_val = func(*args, **kwargs)
                        time_spent = time.time() - startTime
                        logger_func(
                            f"{func_description} - {func.__name__} completed: {time_spent:.3f}s (TIME_TAKEN)"
                        )
                        return ret_val
                    except Exception:
                        return func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

            return wrapper
    else:

        def decorator(func):
            return func

    return decorator


def measure_time(f):
    """
    Decorator to measure and log function execution time.

    Args:
        f: Function to decorate

    Returns:
        Decorated function
    """

    def timed(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()

        print("%r %2.2f sec" % (f.__name__, te - ts))
        return result

    return timed if default_logger().level == logging.DEBUG else log_to(None)


def tracelog(func):
    """
    Decorator to trace function calls with arguments and return values.
    
    Usage:
        @tracelog
        def my_function(a, b):
            return a + b
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if __trace__:
            try:
                # Get function signature
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                
                # Format arguments
                args_str = ", ".join(f"{k}={v}" for k, v in bound_args.arguments.items())
                
                # Log function entry
                trace_log(f"→ {func.__name__}({args_str})")
                
                # Execute function
                start_time = time.time()
                result = func(*args, **kwargs)
                elapsed = (time.time() - start_time) * 1000  # Convert to ms
                
                # Log function exit with result and timing
                trace_log(f"← {func.__name__} returned {result!r} in {elapsed:.2f}ms")
                
                return result
            except Exception as e:
                trace_log(f"✗ {func.__name__} raised {type(e).__name__}: {e}")
                raise
        else:
            return func(*args, **kwargs)
    return wrapper


def tracemethod(cls):
    """
    Class decorator to trace all methods of a class.
    
    Usage:
        @tracemethod
        class MyClass:
            def method1(self): ...
            def method2(self): ...
    """
    for name, method in inspect.getmembers(cls, inspect.isfunction):
        setattr(cls, name, tracelog(method))
    return cls


class suppress_stdout_stderr(object):
    """
    Context manager for suppressing stdout and stderr output.

    Provides deep suppression that works even with compiled C/Fortran code.
    Does not suppress raised exceptions.
    """

    def __init__(self):
        # Open a pair of null files
        self.null_fds = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
        # Save the actual stdout (1) and stderr (2) file descriptors.
        self.save_fds = [os.dup(1), os.dup(2)]

    def __enter__(self):
        # Assign the null pointers to stdout and stderr.
        os.dup2(self.null_fds[0], 1)
        os.dup2(self.null_fds[1], 2)

    def __exit__(self, *_):
        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(self.save_fds[0], 1)
        os.dup2(self.save_fds[1], 2)
        # Close the null files
        for fd in self.null_fds + self.save_fds:
            os.close(fd)


def line_break():
    """Print a line break separator"""
    print("-" * 25)


def clear_screen():
    """Clear the terminal screen"""
    os.system("clear" if os.name == "posix" else "cls")


def set_cursor():
    """Set cursor position (terminal specific)"""
    sys.stdout.write("\033[F")
    sys.stdout.write("\033[K")


def redForegroundText(text):
    """Print text with red foreground color"""
    print("" + colors.fg.red + text + colors.reset)


def greenForegroundText(text):
    """Print text with green foreground color"""
    print("" + colors.fg.green + text + colors.reset)


# Register cleanup function
@atexit.register
def cleanup_logging():
    """
    Clean up logging handlers on program exit.

    Flushes all loggers and performs proper logging shutdown.
    """
    if "PKDevTools_Default_Log_Level" in os.environ.keys():
        logger = default_logger()
        if hasattr(logger, "flush"):
            logger.flush()
        logging.shutdown()
        # Clear process handlers on exit
        process_id = current_process().pid
        if process_id in _process_handlers:
            del _process_handlers[process_id]
        # Clear module loggers
        _module_loggers.clear()