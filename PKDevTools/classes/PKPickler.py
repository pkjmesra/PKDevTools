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
import os
import pickle

from alive_progress import alive_bar
from PKDevTools.classes.Singleton import SingletonType
from PKDevTools.classes import Archiver
from PKDevTools.classes.log import default_logger
from PKDevTools.classes.Fetcher import fetcher
from PKDevTools.classes.Utils import getProgressbarStyle

class PKPickler:
    def __init__(self, metaclass=SingletonType):
        super(PKPickler, self).__init__()

    def pickle(self, dataDict, fileName="dafault.pkl", overWriteConfirmationFunc=None):
        """
        pickle
        ------
        Saves the `dataDict` to the supplied `fileName` using `pickle.dump`. If no `fileName`
        is supplied, the `dataDict` will be written to `dafault.pkl` under the folder returned by
        `Archiver.get_user_outputs_dir()`

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
        cache_file = os.path.join(Archiver.get_user_outputs_dir(), fileName)
        if not os.path.exists(cache_file):
            self._dumpPickle(dataDict, cache_file)
        else:
            if overWriteConfirmationFunc is not None:
                if overWriteConfirmationFunc(cache_file):
                    self._dumpPickle(dataDict, cache_file)
                else:
                    default_logger().debug(f"User aborted pickling/overwriting because file {cache_file} already existed!")

    def _dumpPickle(self, dataDict, cache_file):
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(dataDict.copy(), f, protocol=pickle.HIGHEST_PROTOCOL)
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
        retrial = False
    ):
        dataLoaded = False
        dataDict = None
        cache_file = os.path.join(Archiver.get_user_outputs_dir(),fileName)
        exists = os.path.isfile(cache_file)
        default_logger().info(f"Stock data cache file:{cache_file} exists ->{str(exists)}")
        error = None
        if exists:
            with open(cache_file, "rb") as f:
                try:
                    data = pickle.load(f)
                    dataDict = {}
                    for rowKey in data:
                        dataDict[rowKey] = data.get(rowKey)
                    dataLoaded = True
                except pickle.UnpicklingError as e:
                    default_logger().debug(e, exc_info=True)
                    f.close()
                    error = e
                except EOFError as e:  # pragma: no cover
                    default_logger().debug(e, exc_info=True)
                    f.close()
                    error = e

        userResponse = False
        if (overWriteConfirmationFuncIfCorruptedOrError is None) or (overWriteConfirmationFuncIfCorruptedOrError is not None and overWriteConfirmationFuncIfCorruptedOrError(cache_file,error)):
            userResponse = True

        if (not dataLoaded and userResponse) or not exists:
            cache_url = "https://raw.github.com/pkjmesra/PKScreener/actions-data-download/actions-data-download/" + fileName
            resp = fetcher.fetchURL(cache_url, stream=True)
            if resp is not None:
                default_logger().info(f"Data cache file:{fileName} request status ->{resp.status_code}")
                if resp.status_code == 200:
                    try:
                        chunksize = 1024 * 1024 * 1
                        filesize = int(int(resp.headers.get("content-length")) / chunksize)
                        if filesize > 0:
                            bar, spinner = getProgressbarStyle()
                            f = open(cache_file,"wb")  # .split(os.sep)[-1]
                            dl = 0
                            with alive_bar(
                                filesize, bar=bar, spinner=spinner, manual=True
                            ) as progressbar:
                                for data in resp.iter_content(chunk_size=chunksize):
                                    dl += 1
                                    f.write(data)
                                    progressbar(dl / filesize)
                                    if dl >= filesize:
                                        progressbar(1.0)
                            f.close()
                            dataLoaded = True
                        else:
                            default_logger().debug(f"Data cache file:{fileName} on server has length ->{filesize}")
                    except Exception as e:  # pragma: no cover
                        default_logger().debug(e, exc_info=True)
                        f.close()
                        print("[!] Download Error - " + str(e))
                    if not retrial and dataLoaded:
                        # Don't try for more than once.
                        dataDict = self.unpickle(fileName=fileName, overWriteConfirmationFuncIfCorruptedOrError=overWriteConfirmationFuncIfCorruptedOrError,retrial=True)
        return dataDict
