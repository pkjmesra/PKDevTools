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

import logging
import multiprocessing
import os
import pickle
import sys
import warnings
from queue import Empty

from filelock import FileLock

from PKDevTools.classes import Archiver
from PKDevTools.classes.multiprocessing_logging import SubProcessLogHandler

warnings.simplefilter("ignore", UserWarning)


os.environ["PYTHONWARNINGS"] = "ignore::UserWarning"

# usage: pkscreenercli.exe [-h] [-a ANSWERDEFAULT] [-c CRONINTERVAL] [-d] [-e] [-o OPTIONS] [-p] [-t] [-l] [-v]
# pkscreenercli.exe: error: unrecognized arguments: --multiprocessing-fork parent_pid=4620 pipe_handle=708
# https://github.com/pyinstaller/pyinstaller/wiki/Recipe-Multiprocessing
# Module multiprocessing is organized differently in Python 3.4+
try:
    # Python 3.4+
    if sys.platform.startswith("win"):
        import multiprocessing.popen_spawn_win32 as forking
    else:
        import multiprocessing.popen_fork as forking
except ImportError:
    print("Contact developer! Your platform does not support multiprocessing!")


class PKMultiProcessorClient(multiprocessing.Process):
    def __init__(
        self,
        processorMethod,
        task_queue=None,
        result_queue=None,
        logging_queue=None,
        processingCounter=None,
        processingResultsCounter=None,
        objectDictionaryPrimary=None,
        objectDictionarySecondary=None,
        proxyServer=None,
        keyboardInterruptEvent=None,
        defaultLogger=None,
        fetcher=None,
        configManager=None,
        candlePatterns=None,
        screener=None,
        dbFileNamePrimary=None,
        dbFileNameSecondary=None,
        stockList=None,
        dataCallbackHandler=None,
        progressCallbackHandler=None,
        processorArgs=None,
        rs_strange_index=-1,
    ):
        multiprocessing.Process.__init__(self)
        self.multiprocessingForWindows()
        assert processorMethod is not None, (
            "processorMethod argument must not be None. This is the meyhod that will do the processing."
        )
        # assert keyboardInterruptEvent is not None, "keyboardInterruptEvent argument must not be None."
        # assert task_queue is not None, "task_queue argument must not be None."
        # assert (result_queue is not None or dataCallbackHandler is not None), "result_queue or dataCallbackHandler argument must not be None."
        self.processorMethod = processorMethod
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.logging_queue = logging_queue
        # processingCounter and processingResultsCounter
        # are sunchronized counters that can be used within
        # processorMethod via hostRef.processingCounter
        # or hostRef.processingResultsCounter
        self.processingCounter = processingCounter
        self.processingResultsCounter = processingResultsCounter
        self.dbFileNamePrimary = dbFileNamePrimary
        self.dbFileNameSecondary = dbFileNameSecondary
        # A helper object dictionary that can contain anything
        # and can be accessed using hostRef.objectDictionary
        # within processorMethod
        self.objectDictionaryPrimary = objectDictionaryPrimary
        self.objectDictionarySecondary = objectDictionarySecondary
        # A proxyServer that can contain proxyServer info
        # and can be accessed using hostRef.proxyServer
        # within processorMethod
        self.proxyServer = proxyServer
        # A logger that can contain logger reference
        # and can be accessed using hostRef.default_logger
        # within processorMethod
        self.default_logger = None
        self.logLevel = (
            defaultLogger.level if defaultLogger is not None else logging.NOTSET
        )

        self.keyboardInterruptEvent = keyboardInterruptEvent
        self.stockList = stockList
        self.dataCallbackHandler = dataCallbackHandler
        self.progressCallbackHandler = progressCallbackHandler
        self.fetcher = fetcher
        self.intradayNSEFetcher = None
        self.configManager = configManager
        self.candlePatterns = candlePatterns
        self.screener = screener
        self.refreshDatabase = (self.dbFileNamePrimary is not None) or (
            self.dbFileNameSecondary is not None
        )
        self.paused = False
        self.processorArgs = processorArgs
        self.queueProcessingMode = (self.task_queue is not None) and (
            self.result_queue is not None
        )
        self.rs_strange_index = rs_strange_index

    def _clear(self):
        self.paused = True
        try:
            if self.queueProcessingMode:
                while True:
                    self.task_queue.get_nowait()
        except Empty:
            if self.default_logger is not None:
                self.default_logger.debug("task_queue empty.")
            pass
        try:
            if self.queueProcessingMode:
                while True:
                    self.result_queue.get_nowait()
        except Empty:
            if self.default_logger is not None:
                self.default_logger.debug("result_queue empty.")
            pass
        self.paused = False

    def _setupLogger(self):
        # create the logger to use.
        logger = logging.getLogger("PKDevTools.subprocess")
        # The only handler desired is the SubProcessLogHandler.  If any others
        # exist, remove them. In this case, on Unix and Linux the StreamHandler
        # will be inherited.

        for handler in logger.handlers:
            # just a check for my sanity
            assert not isinstance(handler, SubProcessLogHandler)
            logger.removeHandler(handler)
        # add the handler
        handler = SubProcessLogHandler(self.logging_queue)
        formatter = logging.Formatter(
            fmt="\n%(asctime)s - %(name)s - %(levelname)s - %(filename)s - %(module)s - %(funcName)s - %(lineno)d\n%(message)s\n"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # On Windows, the level will not be inherited.  Also, we could just
        # set the level to log everything here and filter it in the main
        # process handlers.  For now, just set it from the global default.
        logger.setLevel(self.logLevel)
        self.default_logger = logger
        # if self.default_logger is not None:
        #     self.default_logger.info("PKMultiProcessorClient initialized.")

    def _reloadDatabase(self):
        if self.refreshDatabase and self.dbFileNamePrimary is not None:
            # Looks like we got the filename instead of stock dictionary
            # Let's load the saved stocks' data
            cache_file_primary = self.dbFileNamePrimary
            try:
                fileName = os.path.join(
                    Archiver.get_user_data_dir(), f"{cache_file_primary}"
                )
                with FileLock(f"{fileName}.lck"):
                    with open(
                        os.path.join(
    Archiver.get_user_data_dir(),
     cache_file_primary),
                        "rb",
                    ) as f:
                        self.objectDictionaryPrimary = pickle.load(f)
            except BaseException:
                self.objectDictionaryPrimary = multiprocessing.Manager().dict()
                pass
        if self.refreshDatabase and self.dbFileNameSecondary is not None:
            try:
                cache_file_secondary = self.dbFileNameSecondary
                fileName = os.path.join(
                    Archiver.get_user_data_dir(), f"{cache_file_secondary}"
                )
                with FileLock(f"{fileName}.lck"):
                    with open(
                        os.path.join(
                            Archiver.get_user_data_dir(
                            ), f"{cache_file_secondary}"
                        ),
                        "rb",
                    ) as f:
                        self.objectDictionarySecondary = pickle.load(f)

            except BaseException:
                self.objectDictionarySecondary = multiprocessing.Manager().dict()
                pass
        self.refreshDatabase = False

    def processQueueItems(self):
        while not self.keyboardInterruptEvent.is_set():
            try:
                if self.refreshDatabase:
                    # Maybe the database pickle file changed/re-saved.
                    # We'd need to reload again
                    self._reloadDatabase()

                next_task = None
                answer = None
                if self.task_queue is not None:
                    next_task = self.task_queue.get()
                    if next_task is not None:
                        # Inject a reference to this instance of the client
                        # so that the task can still get access back to it.
                        next_task = (*(next_task), self)
            except Empty as e:
                if self.default_logger is not None:
                    self.default_logger.debug(e, exc_info=True)
                continue
            except KeyboardInterrupt as e:
                if self.default_logger is not None:
                    self.default_logger.debug(e, exc_info=True)
                sys.exit(0)
            if next_task is None:
                if self.default_logger is not None:
                    self.default_logger.info("No next task in queue")
                if self.task_queue is not None:
                    self.task_queue.task_done()
                break
            if self.processorMethod is not None and not self.paused:
                answer = self.processorMethod(*(next_task))
            if self.task_queue is not None:
                self.task_queue.task_done()
            # self.default_logger.info(f"Task done. Result:{answer}")
            if self.result_queue is not None and not self.paused:
                self.result_queue.put(answer)

    def run(self):
        try:
            self._setupLogger()
            if self.queueProcessingMode:
                self.processQueueItems()
            else:
                if self.keyboardInterruptEvent is not None:
                    while not self.keyboardInterruptEvent.is_set():
                        try:
                            if self.processorMethod is not None and not self.paused:
                                try:
                                    import tensorflow as tf

                                    with tf.device("/device:GPU:0"):
                                        self.processorMethod(
                                            self.processorArgs)
                                except BaseException:
                                    self.processorMethod(self.processorArgs)
                                    pass
                        except KeyboardInterrupt:
                            try:
                                self.terminate()
                            finally:
                                sys.exit(0)
                elif self.processorMethod is not None:
                    self.processorMethod(self.processorArgs)
        except Exception as e:
            if self.default_logger is not None:
                self.default_logger.debug(e, exc_info=True)
            sys.exit(0)

    def multiprocessingForWindows(self):
        if sys.platform.startswith("win"):
            # First define a modified version of Popen.
            class _Popen(forking.Popen):
                def __init__(self, *args, **kw):
                    if hasattr(sys, "frozen"):
                        # We have to set original _MEIPASS2 value from sys._MEIPASS
                        # to get --onefile mode working.
                        os.putenv("_MEIPASS2", sys._MEIPASS)
                    try:
                        super(_Popen, self).__init__(*args, **kw)
                    finally:
                        if hasattr(sys, "frozen"):
                            # On some platforms (e.g. AIX) 'os.unsetenv()' is not
                            # available. In those cases we cannot delete the variable
                            # but only set it to the empty string. The bootloader
                            # can handle this case.
                            if hasattr(os, "unsetenv"):
                                os.unsetenv("_MEIPASS2")
                            else:
                                os.putenv("_MEIPASS2", "")

            # Second override 'Popen' class with our modified version.
            forking.Popen = _Popen
