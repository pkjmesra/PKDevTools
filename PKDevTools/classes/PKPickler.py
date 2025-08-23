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

import copy
import os
import pickle
import sys

from alive_progress import alive_bar
from filelock import FileLock

from PKDevTools.classes import Archiver
from PKDevTools.classes.ColorText import colorText
from PKDevTools.classes.Fetcher import fetcher
from PKDevTools.classes.log import default_logger
from PKDevTools.classes.OutputControls import OutputControls
from PKDevTools.classes.Singleton import SingletonMixin, SingletonType
from PKDevTools.classes.Utils import getProgressbarStyle, random_user_agent


class PKPickler(SingletonMixin, metaclass=SingletonType):
    def __init__(self):
        super(PKPickler, self).__init__()
        self.fetcher = fetcher()

    @property
    def pickledDict(self):
        if "pickledDict" in self.attributes.keys():
            return self.attributes["pickledDict"]
        else:
            self.pickledDict = {}
            return self.pickledDict

    @pickledDict.setter
    def pickledDict(self, dict):
        self.attributes["pickledDict"] = dict

    def pickle(self, dataDict, fileName="dafault.pkl",
               overWriteConfirmationFunc=None):
        """
        pickle
        ------
        Saves the `dataDict` to the supplied `fileName` using `pickle.dump`. If no `fileName`
        is supplied, the `dataDict` will be written to `dafault.pkl` under the folder returned by
        `Archiver.get_user_data_dir()`

        If the file already exists, the caller can optionally provide a `overWriteConfirmationFunc`
        function that will be called to accept user input (`True` to overwrite or `False` to abort.)

        Example
        -------
        `PKPickler().pickle("MyFile.pkl", self.overWriteConfirmationFunc)`

        def overWriteConfirmationFunc(self, filePath:str): -> bool
            # Check with user if the user really wants to overwrite?
            ...

            # User responded to overwrite

            return True

            # User responded to not overwrite. The pickling will be aborted silently.

            return False

        If `overWriteConfirmationFunc` is `None`, the file will always be overwritten by default.

        Exceptions
        ----------
        Raises `pickle.PicklingError` if `pickle.dump` raised `pickle.PicklingError`.
        Raises `Exception` for all other exceptions when writing.
        """
        cache_file = os.path.join(Archiver.get_user_data_dir(), fileName)
        if not os.path.exists(cache_file) or overWriteConfirmationFunc is None:
            self._dumpPickle(dataDict, cache_file, fileName)
        else:
            if overWriteConfirmationFunc is not None:
                if overWriteConfirmationFunc(cache_file):
                    self._dumpPickle(dataDict, cache_file, fileName)
                else:
                    default_logger().debug(
                        f"User aborted pickling/overwriting because file {cache_file} already existed!"
                    )

    def _dumpPickle(self, dataDict, cache_file, fileName):
        try:
            with self.attributes["lock"]:
                dataCopy = copy.deepcopy(dataDict)
                diskDataDict = {}
                exists = os.path.isfile(cache_file)
                if exists:
                    with FileLock(f"{cache_file}.lck"):
                        with open(cache_file, "r+b") as pfile:
                            diskDataDict = pickle.load(pfile)
                            dataCopy = diskDataDict | dataCopy
                            if len(diskDataDict) > len(dataCopy):
                                dataCopy = dataCopy | diskDataDict
                            pickle.dump(
                                dataCopy, pfile, protocol=pickle.HIGHEST_PROTOCOL
                            )
                self.pickledDict[fileName] = dataCopy
        except pickle.PicklingError as e:  # pragma: no cover
            default_logger().debug(e, exc_info=True)
            raise e
        except Exception as e:  # pragma: no cover
            default_logger().debug(e, exc_info=True)
            raise e

    def unpickle(
        self,
        fileName="dafault.pkl",
        overWriteConfirmationFuncIfCorruptedOrError=None,
        retrial=False,
    ):
        """
        unpickle
        ------
        Retrieves the data from the supplied `fileName` and returns `dict` or `None` using `pickle.load`. If no `fileName`
        is supplied, `dafault.pkl` will be searched on the `PKScreener` under `actions-data-download` and data saved under
        `Archiver.get_user_data_dir()` by the filename `dafault.pkl`

        If the file already exists, the caller can optionally provide a `overWriteConfirmationFuncIfCorruptedOrError`
        function that will be called to accept user input (`True` to overwrite or `False` to abort.) for cases
        when the data might have been corrupted or there were other issues with saved data.

        Example
        -------
        `PKPickler().unpickle("MyFile.pkl", self.overWriteConfirmationFuncIfCorruptedOrError)`

        def overWriteConfirmationFuncIfCorruptedOrError(self, filePath:str, error:Exception): -> bool
            # Check with user if the user really wants to overwrite?
            ...

            # User responded to overwrite

            return True

            # User responded to not overwrite. The unpickling will be aborted silently.

            return False

        If `overWriteConfirmationFuncIfCorruptedOrError` is `None`, the file will always be overwritten by default if an error
        was encountered due to corruption of data.

        Exceptions
        ----------
        Sends `pickle.UnpicklingError` in the `error` parameter of `overWriteConfirmationFuncIfCorruptedOrError`
        if `pickle.load` raised `pickle.UnpicklingError`. Sends `EOFError` for `EOFError` error.
        """
        if fileName in self.pickledDict.keys():
            return self.pickledDict[fileName]

        dataLoaded = False
        dataDict = None
        cache_file = os.path.join(Archiver.get_user_data_dir(), fileName)
        filePath = f"results/Data/{fileName}"
        exists = os.path.isfile(cache_file)
        default_logger().info(
            f"Stock data cache file:{cache_file} exists ->{str(exists)}"
        )
        error = None
        if exists:
            dataDict = {}
            with open(cache_file, "rb") as f:
                try:
                    with self.attributes["lock"]:
                        if not dataLoaded:
                            with FileLock(f"{cache_file}.lck"):
                                with open(cache_file, "rb") as pfile:
                                    dataDict = pickle.load(pfile)
                        dataLoaded = True
                except pickle.UnpicklingError as e:
                    default_logger().debug(
    f"File: {filePath}\n{e}", exc_info=True)
                    default_logger().debug(e, exc_info=True)
                    f.close()
                    error = e
                except EOFError as e:  # pragma: no cover
                    default_logger().debug(
    f"File: {filePath}\n{e}", exc_info=True)
                    f.close()
                    error = e

        userResponse = False
        if (overWriteConfirmationFuncIfCorruptedOrError is None) or (
            overWriteConfirmationFuncIfCorruptedOrError is not None
            and overWriteConfirmationFuncIfCorruptedOrError(cache_file, error)
        ):
            userResponse = True

        if (not dataLoaded and userResponse) or not exists:
            cache_url = (
                "https://raw.githubusercontent.com/pkjmesra/PKScreener/actions-data-download/actions-data-download/"
                + filePath
            )
            headers = {
                "authority": "raw.githubusercontent.com",
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "dnt": "1",
                "sec-ch-ua-mobile": "?0",
                # 'sec-ch-ua-platform': '"macOS"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "cross-site",
                "origin": "https://github.com",
                "referer": f"https://github.com/pkjmesra/PKScreener/blob/actions-data-download/actions-data-download/{filePath}",
                "user-agent": f"{random_user_agent()}",
                # 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36
            }
            resp = self.fetcher.fetchURL(
    url=cache_url, headers=headers, stream=True)
            if resp is not None:
                default_logger().info(
                    f"Data cache file:{filePath} request status ->{resp.status_code}"
                )
                if resp.status_code == 200:
                    try:
                        contentLength = resp.headers.get("content-length")
                        serverBytes = (
                            int(contentLength) if contentLength is not None else 0
                        )
                        KB = 1024
                        MB = KB * 1024
                        chunksize = (
                            MB
                            if serverBytes >= MB
                            else (KB if serverBytes >= KB else 1)
                        )
                        filesize = int(serverBytes / chunksize)
                        if filesize > 0:
                            bar, spinner = getProgressbarStyle()
                            with self.attributes["lock"]:
                                if not os.path.isfile(
                                    cache_file) and not dataLoaded:
                                    f = open(
    cache_file, "wb")  # .split(os.sep)[-1]
                                    dl = 0
                                    lastPath = (cache_file.split(os.sep)[-1]).replace(
                                        "DB.pkl", ""
                                    )
                                    OutputControls().printOutput(
                                        f"{colorText.GREEN}[+] Downloading {
                                            lastPath
                                        } cache from pkscreener server...{
                                            colorText.END
                                        }"
                                    )
                                    with alive_bar(
                                        filesize, bar=bar, spinner=spinner, manual=True
                                    ) as progressbar:
                                        for data in resp.iter_content(
                                            chunk_size=chunksize
                                        ):
                                            dl += 1
                                            f.write(data)
                                            progressbar(dl / filesize)
                                            if dl >= filesize:
                                                progressbar(1.0)
                                    f.close()
                                    # sys.stdout.write(f"\x1b[2A")
                                dataLoaded = True
                        else:
                            default_logger().debug(
                                f"Data cache file:{filePath} on server has length ->{filesize}"
                            )
                    except Exception as e:  # pragma: no cover
                        default_logger().debug(e, exc_info=True)
                        f.close()
                        OutputControls().printOutput(
                            "[!] Download Error - " + str(e))
                    if not retrial and dataLoaded:
                        # Don't try for more than once.
                        dataDict = self.unpickle(
                            fileName=fileName,
                            overWriteConfirmationFuncIfCorruptedOrError=overWriteConfirmationFuncIfCorruptedOrError,
                            retrial=True,
                        )
        return dataDict


class PKPicklerDB:
    def __init__(self, fileName="default.pkl"):
        self.fileName = fileName
        self.pickler = PKPickler()

    def searchCache(self, ticker: str = None, name: str = None):
        if (ticker is None and name is None) or (
            len(ticker.strip()) == 0 and len(name.strip()) == 0
        ):
            raise TypeError(
                "At least one of ticker or name should have some value!")

        savedData = self.pickler.unpickle(fileName=self.fileName)
        if savedData is not None and len(savedData) > 0:
            if (
                ticker is not None
                and isinstance(ticker, str)
                and ticker.strip().upper() in savedData.keys()
            ):
                return savedData[ticker.strip().upper()]
            if (
                name is not None
                and isinstance(name, str)
                and name.strip().upper() in savedData.keys()
            ):
                return savedData[name.strip().upper()]
        return None

    def saveCache(self, ticker: str = None, name: str = None,
                  stockDict: dict = None):
        if (ticker is None and name is None) or (
            len(ticker.strip()) == 0 and len(name.strip()) == 0
        ):
            raise TypeError(
                "At least one of ticker or name should have some value!")
        if not isinstance(stockDict, dict) or stockDict is None or len(
            stockDict) == 0:
            raise TypeError(
                "stockDict should be a dictionary and should have some value!"
            )

        savedData = self.pickler.unpickle(fileName=self.fileName)
        if savedData is None:
            savedData = {}
        if ticker is not None and len(ticker.strip()) > 0:
            savedData[ticker.strip().upper()] = stockDict
        if name is not None and len(name.strip()) > 0:
            savedData[name.strip().upper()] = stockDict
        self.pickler.pickle(savedData, fileName=self.fileName)
