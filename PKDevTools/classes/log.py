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
import threading
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
    Thread and process-safe logger implementation.

    This logger handles both multi-threaded and multiprocessing environments
    by using appropriate locking mechanisms and process-specific configuration.

    Features:
    - Process-safe singleton instantiation
    - Thread-safe logging operations within processes
    - Automatic process-specific handler management
    - Filter-based message filtering
    - Caller information injection
    """

    _instance = None

    def __new__(cls, logger=None):
        """
        Process-safe singleton instantiation.

        Uses multiprocessing lock to ensure only one instance per process
        while allowing different instances in different processes.

        Args:
            logger: Existing logger instance to wrap (optional)

        Returns:
            filterlogger instance for the current process
        """
        with _process_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, logger=None):
        """
        Initialize the logger for the current process.

        Args:
            logger: Existing logger instance to wrap (optional)
        """
        if getattr(self, "_initialized", False):
            return

        with _thread_lock:
            if getattr(self, "_initialized", False):
                return

            self._logger = logger or logging.getLogger(
                f"PKDevTools_{current_process().pid}_{get_ident()}"
            )
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
    def getlogger(logger):
        """
        Factory method to get appropriate logger instance.

        Returns emptylogger if PKDevTools_Default_Log_Level is not set,
        otherwise returns a filterlogger instance.

        Args:
            logger: Logger instance to wrap

        Returns:
            emptylogger or filterlogger instance
        """
        if "PKDevTools_Default_Log_Level" not in os.environ:
            return emptylogger()

        return filterlogger(logger=logger)

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
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(filename)s - "
                "%(module)s - %(funcName)s - %(lineno)d - %(message)s"
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
            frame = inspect.stack()[2]  # Skip logger method and caller
            filename = os.path.basename(frame.filename)
            return f"{filename} - {frame.function} - {frame.lineno} - {message}"
        except Exception:
            return message

    def debug(self, e, exc_info=False):
        """
        Log a debug message.

        Args:
            e: Message or exception to log
            exc_info: If True, include exception information
        """
        if "PKDevTools_Default_Log_Level" not in os.environ:
            return

        line = self._format_message_with_caller_info(str(e))

        if not self._should_log(line):
            return

        with _thread_lock:
            self.logger.debug(line, exc_info=exc_info)

    def info(self, line):
        """
        Log an info message.

        Args:
            line: Message to log
        """
        if "PKDevTools_Default_Log_Level" not in os.environ:
            return

        formatted_line = self._format_message_with_caller_info(line)

        if not self._should_log(formatted_line):
            return

        with _thread_lock:
            self.logger.info(formatted_line)

    def warn(self, line):
        """
        Log a warning message.

        Args:
            line: Message to log
        """
        if "PKDevTools_Default_Log_Level" not in os.environ:
            return

        if not self._should_log(line):
            return

        with _thread_lock:
            self.logger.warning(line)

    def error(self, line):
        """
        Log an error message.

        Args:
            line: Message to log
        """
        if "PKDevTools_Default_Log_Level" not in os.environ:
            return

        if not self._should_log(line):
            return

        with _thread_lock:
            self.logger.error(line)

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
        Log a critical message.

        Args:
            line: Message to log
        """
        if "PKDevTools_Default_Log_Level" not in os.environ:
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
    filter=None,
):
    """
    Set up and configure a custom logger instance.

    Args:
        name: Name of the logger
        levelname: Default logging level
        trace: Enable tracing mode
        log_file_path: Path to log file
        filter: String filter for messages (only messages containing this string will be logged)

    Returns:
        Configured logger instance (emptylogger if logging disabled)
    """
    global __trace__, __filter__

    __trace__ = trace
    __filter__ = filter.upper() if filter else None

    # Only setup logging if environment variable is set
    if "PKDevTools_Default_Log_Level" not in os.environ:
        return emptylogger()

    logger = filterlogger.getlogger(logging.getLogger(name))

    # Set the log level from environment variable
    try:
        env_level = int(os.environ["PKDevTools_Default_Log_Level"])
        logger.level = env_level
    except (ValueError, KeyError):
        logger.level = levelname

    # Configure handlers
    logger.addHandlers(log_file_path=log_file_path, levelname=logger.level)

    # Setup trace logger if tracing is enabled
    if trace:
        trace_logger = filterlogger.getlogger(
            logging.getLogger("PKDevTools_file_logger")
        )
        trace_logger.level = logging.DEBUG  # Tracing always uses DEBUG level
        trace_logger.addHandlers(
    log_file_path=log_file_path,
     levelname=logging.DEBUG)
        logger.info("Tracing started")

    # Turn off warnings
    warnings.simplefilter("ignore", DeprecationWarning)
    warnings.simplefilter("ignore", FutureWarning)

    return logger


def default_logger():
    """
    Get the default logger instance.

    Returns:
        filterlogger instance if logging enabled, otherwise emptylogger
    """
    if "PKDevTools_Default_Log_Level" in os.environ:
        return filterlogger.getlogger(logging.getLogger("PKDevTools"))
    else:
        return emptylogger()


def file_logger():
    """
    Get the file logger instance for tracing.

    Returns:
        filterlogger instance if logging enabled, otherwise emptylogger
    """
    if "PKDevTools_Default_Log_Level" in os.environ:
        return filterlogger.getlogger(
            logging.getLogger("PKDevTools_file_logger"))
    else:
        return emptylogger()


def trace_log(line):
    """
    Log tracing information - always works if tracing is enabled.

    Args:
        line: Tracing message to log
    """
    global __trace__
    if __trace__:
        file_logger().info(f"TRACE: {line}")


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
    if logger_func is not None and "PKDevTools_Default_Log_Level" in os.environ:

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
                            f"{func_description} - {func.__name__} completed: {
                                time_spent:.3f
                            }s (TIME_TAKEN)"
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


# Conditional tracelog decorator
tracelog = (
    log_to(trace_log)
    if "PKDevTools_Default_Log_Level" in os.environ
    and (default_logger().level == logging.DEBUG or __trace__)
    else log_to(None)
)


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
    if "PKDevTools_Default_Log_Level" in os.environ:
        logger = default_logger()
        if hasattr(logger, "flush"):
            logger.flush()
        logging.shutdown()
        # Clear process handlers on exit
        process_id = current_process().pid
        if process_id in _process_handlers:
            del _process_handlers[process_id]
