#!/usr/bin/python3
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

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Union

from bs4 import BeautifulSoup
from mthrottle import Throttle
from requests.exceptions import ReadTimeout

from PKDevTools.classes.Fetcher import fetcher

throttleConfig = {
    "default": {
        "rps": 60,
    },
}

th = Throttle(throttleConfig, 10)


class CookieHelper:
    """A cookie helper class to renew cookies on-demand or read tokens
    from <meta> tags of html source file.

    Methods will raise
        - ``TimeoutError`` if request takes too long.
        - ``ConnectionError`` if request failed for any reason.

    :param download_folder: A folder/dir to save downloaded files and cookie files
    :type download_folder: pathlib.Path or str
    :raise ValueError: if ``download_folder`` is not a folder/dir
    """

    def __init__(
        self,
        download_folder: Union[str, Path],
        baseCookieUrl="https://www.nseindia.com/option-chain",
        cookieStoreName="n",
        baseHtmlUrl="https://www.nseindia.com/option-chain",
        htmlStoreName="n",
    ):
        """Initialise NSE"""

        uAgent = "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/118.0"

        self.default_headers = {
            "User-Agent": uAgent,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.nseindia.com/get-quotes/equity?symbol=HDFCBANK",
        }
        self.baseCookieUrl = baseCookieUrl
        self.baseHtmlUrl = baseHtmlUrl
        self.cookieStoreName = cookieStoreName
        self.htmlStoreName = htmlStoreName
        self.dir = CookieHelper.__getPath(download_folder, isFolder=True)

        self.cookie_path = self.dir / f"{cookieStoreName}_cookies.pkl"
        self.html_path = self.dir / f"{htmlStoreName}_html.pkl"
        self.fetcher = fetcher()
        self.html_metas = self.getMetaDictionary()
        self.cookies = self.getCookies()

    def __setCookies(self):
        r = self.__req(
    self.baseCookieUrl,
    headers=self.default_headers,
     timeout=10)
        if r is not None:
            cookies = r.cookies
            self.cookie_path.write_bytes(pickle.dumps(cookies))
        else:
            cookies = self.getCookies()
        return cookies

    def getCookies(self):
        if self.cookie_path.exists():
            cookies = pickle.loads(self.cookie_path.read_bytes())
            if self.__hasCookiesExpired(cookies):
                cookies = self.__setCookies()
            return cookies
        return self.__setCookies()

    def __setMetaDictionary(self):
        r = self.__req(
    self.baseHtmlUrl,
    headers=self.default_headers,
     timeout=10)
        metaDict = {}
        if r is not None:
            html = r.text
            soup = BeautifulSoup(html, features="lxml")
            for tag in soup.find_all("meta"):
                name = tag.get("name", None)
                content = tag.get("content", None)
                if name is not None and content is not None:
                    metaDict[name] = content
            self.html_path.write_bytes(pickle.dumps(metaDict))
        return metaDict

    def getMetaDictionary(self):
        if self.html_path.exists():
            metaDict = pickle.loads(self.html_path.read_bytes())
            return metaDict
        return self.__setMetaDictionary()

    def resetCookies(self):
        try:
            os.remove(self.cookie_path)
        except BaseException:
            pass

    def resetMetas(self):
        try:
            os.remove(self.html_path)
        except BaseException:
            pass

    @staticmethod
    def __hasCookiesExpired(cookies):
        for cookie in cookies:
            if cookie.is_expired():
                return True
        return False

    @staticmethod
    def __getPath(path: Union[str, Path], isFolder: bool = False):
        path = path if isinstance(path, Path) else Path(path)
        if isFolder:
            if path.is_file():
                raise ValueError(f"{path}: must be a folder")
            if not path.exists():
                path.mkdir(parents=True)

        return path

    def __req(self, url, params=None, headers=None, timeout=10):
        """Make a http request"""
        th.check()
        try:
            r = self.fetcher.fetchURL(
                url=url,
                params=params,
                headers=headers,
                timeout=timeout,
                raiseError=True,
            )
        except ReadTimeout as e:
            raise TimeoutError(repr(e))
        if r is not None and not r.ok:
            raise ConnectionError(f"{url} {r.status_code}: {r.reason}")
        return r


# ch = CookieHelper(download_folder="/Users/praveen.jha1/Downloads/codes/PKScreener-main/results/",
#                   baseCookieUrl="https://morningstar.in/stocks/0p0000c3nz/nse-hdfc-bank-ltd/overview.aspx",
#                   baseHtmlUrl="https://morningstar.in/stocks/0p0000c3nz/nse-hdfc-bank-ltd/overview.aspx",
#                   cookieStoreName="morningstar",
#                   htmlStoreName="morningstar")
# print(ch.getCookies())
# print(ch.getMetaDictionary())
