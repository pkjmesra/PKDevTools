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

from __future__ import print_function

import functools
import os
import sys
import threading
import time
from time import sleep

try:
    import thread
except ImportError:
    import _thread as thread

INTERMEDIATE_NUM_SECONDS_WARN = 30
if "RUNNER" in os.environ.keys():
    try:
        owner = (
            os.popen("git ls-remote --get-url origin | cut -d/ -f4")
            .read()
            .replace("\n", "")
        )
        repo = (
            os.popen("git ls-remote --get-url origin | cut -d/ -f5")
            .read()
            .replace(".git", "")
            .replace("\n", "")
        )
        if owner.lower() not in ["pkjmesra", "pkscreener"]:
            sys.exit(0)
    except BaseException:
        pass


def cdquit(fn_name):
    # print to stderr, unbuffered in Python 2.
    print(
        "{0} took too long. Handle KeyboardInterrupt if you do not want to exit".format(
            fn_name
        ),
        file=sys.stderr,
    )
    sys.stderr.flush()  # Python 3 stderr is likely buffered.
    thread.interrupt_main()  # raises KeyboardInterrupt


def intermediateMessage(fn_name):
    # print to stderr, unbuffered in Python 2.
    print(
        "{0} is taking too long...Let the developer know!\n".format(fn_name),
        file=sys.stderr,
    )
    sys.stderr.flush()  # Python 3 stderr is likely buffered.


def exit_after(s):
    """
    use as decorator to exit process if
    function takes longer than s seconds
    """

    def outer(fn):
        def inner(*args, **kwargs):
            timer = threading.Timer(s, cdquit, args=[fn.__name__])
            timer.start()
            timer_mid = threading.Timer(
                INTERMEDIATE_NUM_SECONDS_WARN, intermediateMessage, args=[
                    fn.__name__]
            )
            timer_mid.start()
            try:
                result = None
                result = fn(*args, **kwargs)
            finally:
                timer.cancel()
                timer_mid.cancel()
            return result

        return inner

    return outer


def ping(interval=60, instance=None, prefix=""):
    """Decorator to run a ping function in a background thread."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            stop_event = threading.Event()

            def send_ping():
                while not stop_event.is_set():
                    time.sleep(interval)
                    if instance is not None and hasattr(
                        instance, "send_event"):
                        instance.send_event(f"{prefix}ping")

            # Start ping thread
            ping_thread = threading.Thread(target=send_ping, daemon=True)
            ping_thread.start()

            try:
                return func(*args, **kwargs)  # Run the main function
            except (KeyboardInterrupt, SystemExit):
                stop_event.set()
                try:
                    ping_thread.join(timeout=1)
                except BaseException:
                    pass
            finally:
                stop_event.set()  # Ensure ping thread stops even if func exits normally

        return wrapper

    return decorator
