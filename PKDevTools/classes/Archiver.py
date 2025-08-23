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

import glob
import os
import os.path
import tempfile
import warnings
from datetime import datetime, timezone

import pandas as pd
import pytz

from PKDevTools.classes.log import default_logger

warnings.simplefilter("ignore", DeprecationWarning)
warnings.simplefilter("ignore", FutureWarning)


def resolveFilePath(fileName):
    if fileName is None:
        fileName = ""
    dirPath = os.path.join(tempfile.gettempdir(), "PKDevTools")
    filePath = os.path.join(dirPath, fileName)
    safe_open_w(filePath)
    return filePath


def get_last_modified_datetime(file_path):
    from PKDevTools.classes.PKDateUtilities import PKDateUtilities

    last_modified = datetime.fromtimestamp(
        os.path.getmtime(file_path), tz=pytz.timezone("Asia/Kolkata")
    )
    return last_modified


def cacheFile(bData, fileName):
    filePath = resolveFilePath(fileName)
    with open(filePath, "wb") as f:
        f.write(bData)


def findFile(fileName):
    filePath = resolveFilePath(fileName)
    try:
        exists = os.path.exists(filePath)
        with open(filePath, "rb") as f:
            bData = f.read()
        return bData, filePath, get_last_modified_datetime(
            filePath) if exists else None
    except Exception:
        return None, filePath, None


def findFileInAppResultsDirectory(directory=None, fileName=None):
    filePath = os.path.join(
        get_user_outputs_dir() if directory is None else directory, fileName
    )
    exists = os.path.exists(filePath)
    data = None
    try:
        if exists:
            with open(filePath, "r") as f:
                data = f.read()
        return data, filePath, get_last_modified_datetime(
            filePath) if exists else None
    except Exception:
        return None, filePath, None


def saveData(data, fileName):
    if not len(data) > 0 or fileName == "" or fileName is None:
        return
    filePath = resolveFilePath(fileName)
    try:
        data.to_pickle(filePath)
    except Exception:
        # print(e)
        pass


def readData(fileName):
    if fileName == "" or fileName is None:
        return
    filePath = resolveFilePath(fileName)
    unpickled_df = None
    try:
        unpickled_df = pd.read_pickle(filePath)
        return unpickled_df, filePath, get_last_modified_datetime(filePath)
    except Exception:
        # print(e)
        pass
    return None, filePath, None


def safe_open_w(path):
    """Open "path" for writing, creating any parent directories as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # return open(path, 'wb')


def get_user_outputs_dir():
    # Let's make the results directory where we'll push all outputs
    os.makedirs(
        os.path.dirname(os.path.join(os.getcwd(), f"results{os.sep}")), exist_ok=True
    )
    return os.path.join(os.getcwd(), "results")


def get_user_data_dir():
    # Let's make the data directory where we'll push all data outputs
    resultsDir = get_user_outputs_dir()
    os.makedirs(
        os.path.dirname(os.path.join(resultsDir, f"Data{os.sep}")), exist_ok=True
    )
    return os.path.join(resultsDir, "Data")


def get_user_indices_dir():
    # Let's make the indices directory where we'll push all indices outputs
    resultsDir = get_user_outputs_dir()
    os.makedirs(
        os.path.dirname(os.path.join(resultsDir, f"Indices{os.sep}")), exist_ok=True
    )
    return os.path.join(resultsDir, "Indices")


def get_user_cookies_dir():
    # Let's make the cookies directory where we'll push all cookies outputs
    resultsDir = get_user_outputs_dir()
    os.makedirs(
        os.path.dirname(os.path.join(resultsDir, f"Cookies{os.sep}")), exist_ok=True
    )
    return os.path.join(resultsDir, "Cookies")


def get_user_reports_dir():
    # Let's make the reports directory where we'll push all user generated
    # report outputs
    resultsDir = get_user_outputs_dir()
    os.makedirs(
        os.path.dirname(os.path.join(resultsDir, f"Reports{os.sep}")), exist_ok=True
    )
    return os.path.join(resultsDir, "Reports")


def get_user_temp_dir():
    # Let's make the cookies directory where we'll push all cookies outputs
    resultsDir = get_user_outputs_dir()
    os.makedirs(
        os.path.dirname(os.path.join(resultsDir, f"DeleteThis{os.sep}")), exist_ok=True
    )
    return os.path.join(resultsDir, "DeleteThis")


def deleteFileWithPattern(
    pattern=None, excludeFile=None, rootDir=None, recursive=False
):
    if pattern is None:
        return
    if rootDir is None:
        rootDir = [
            get_user_outputs_dir(),
            get_user_outputs_dir().replace("results", "actions-data-download"),
        ]
    else:
        rootDir = [rootDir]
    for dir in rootDir:
        files = glob.glob(pattern, root_dir=dir, recursive=recursive)
        for f in files:
            if excludeFile is not None:
                if not f.endswith(excludeFile):
                    try:
                        os.remove(f if os.sep in f else os.path.join(dir, f))
                    except Exception as e:
                        default_logger().debug(e, exc_info=True)
                        pass
            else:
                try:
                    os.remove(f if os.sep in f else os.path.join(dir, f))
                except Exception as e:
                    default_logger().debug(e, exc_info=True)
                    pass
