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
import urllib
import warnings
from datetime import timedelta

import requests
import requests_cache
from requests.exceptions import ConnectTimeout, ReadTimeout
from requests_cache import CachedSession
from urllib3.exceptions import ReadTimeoutError

from PKDevTools.classes import Archiver
from PKDevTools.classes.ColorText import colorText
from PKDevTools.classes.log import default_logger

warnings.simplefilter("ignore", DeprecationWarning)
warnings.simplefilter("ignore", FutureWarning)


requests.packages.urllib3.util.connection.HAS_IPV6 = False


class PKCachedSession(CachedSession):
    def __getstate__(self):
        return {}


userDataDirComponents = Archiver.get_user_data_dir().split(os.sep)
session = PKCachedSession(
    cache_name=f"{os.sep.join(userDataDirComponents[-2:])}{os.sep}PKDevTools_cache",
    db_path=os.path.join(
    Archiver.get_user_data_dir(),
     "PKDevTools_cache.sqlite"),
    expire_after=timedelta(hours=6),
    stale_if_error=True,
)


# Exception class if yfinance stock delisted
class StockDataEmptyException(Exception):
    pass


# This Class Handles Fetching of Stock Data over the internet
class stubConfigManager:
    def __init__(self):
        self.maxNetworkRetryCount = 3
        self.generalTimeout = 2
        self.longTimeout = 2 * self.generalTimeout

    def restartRequestsCache(self):
        return None


class fetcher:
    def __init__(self, configManager=None):
        if configManager is None:
            configManager = stubConfigManager()

        self.configManager = configManager
        self._proxy = None
        self.session = session
        pass

    @property
    def proxyServer(self):
        if self._proxy is None:
            self._proxy = self._getProxyServer()
        return self._proxy

    def _getProxyServer(self):
        # Get system wide proxy for networking
        try:
            proxy = urllib.request.getproxies()["http"]
            proxy = {"https": proxy}
        except KeyError as e:
            # default_logger().debug(e, exc_info=True)
            proxy = None
        return proxy

    def postURL(
        self,
        url,
        data=None,
        headers={},
        trial=1,
        params=None,
        timeout=0,
        raiseError=False,
    ):
        try:
            response = None
            requestor = self.session
            # We should try to switch to requests lib if cached_session
            # begin to give some problem after we've tried for
            # 50% of the configured retrials.
            if trial >= int(self.configManager.maxNetworkRetryCount / 2):
                requestor = requests
                self.session = requestor.session()
            timeout = (
                timeout if timeout > 0 else trial * self.configManager.generalTimeout
            )
            response = requestor.post(
                url,
                proxies=self.proxyServer,
                data=data,
                headers=headers,
                params=params,
                timeout=timeout,
            )
        except (ConnectTimeout, ReadTimeoutError, ReadTimeout) as e:
            default_logger().debug(e, exc_info=True)
            if raiseError:
                raise e
            if trial <= int(self.configManager.maxNetworkRetryCount):
                # print(colorText.BOLD + colorText.FAIL + f"[+] Network Request timed-out. Going for {trial} of {self.configManager.maxNetworkRetryCount}th trial..." + colorText.END)
                return self.postURL(
                    url,
                    data=data,
                    headers=headers,
                    trial=trial + 1,
                    params=params,
                    timeout=timeout,
                )
        except Exception as e:
            # Something went wrong with the CachedSession.
            default_logger().debug(e, exc_info=True)
            if trial <= int(self.configManager.maxNetworkRetryCount):
                if trial <= 1:
                    # Let's try and restart the cache
                    self.configManager.restartRequestsCache()
                elif trial > 1 and requests_cache.is_installed():
                    # REstarting didn't fix it. We need to disable the cache
                    # altogether.
                    requests_cache.clear()
                    requests_cache.uninstall_cache()
                # print(colorText.BOLD + colorText.FAIL + f"[+] Network Request failed. Going for {trial} of {self.configManager.maxNetworkRetryCount}th trial..." + colorText.END)
                return self.postURL(
                    url,
                    data=data,
                    headers=headers,
                    trial=trial + 1,
                    params=params,
                    timeout=timeout,
                )
        if trial > 1 and not requests_cache.is_installed():
            # Let's try and re-enable the caching behaviour before exiting.
            # Maybe there was something wrong with this request, but the next
            # request should have access to cache.
            self.configManager.restartRequestsCache()
        return response

    def fetchURL(
        self,
        url,
        stream=False,
        trial=1,
        headers=None,
        params=None,
        timeout=0,
        raiseError=False,
    ):
        try:
            response = None
            requestor = self.session
            cookies = requestor.cookies
            # We should try to switch to requests lib if cached_session
            # begin to give some problem after we've tried for
            # 50% of the configured retrials.
            if stream or trial >= int(
                self.configManager.maxNetworkRetryCount / 2):
                requestor = requests
                self.session = requestor.session()
                if cookies is not None and headers is not None:
                    self.session.cookies.update(cookies)
                    self.session.headers.update(headers)
                    requestor = self.session
            timeout = (
                timeout if timeout > 0 else trial * self.configManager.generalTimeout
            )
            response = requestor.get(
                url,
                params=params,
                proxies=self.proxyServer,
                stream=stream,
                timeout=timeout,
                headers=headers,
            )
        except (ConnectTimeout, ReadTimeoutError, ReadTimeout) as e:
            default_logger().debug(e, exc_info=True)
            if raiseError:
                raise e
            if trial <= int(self.configManager.maxNetworkRetryCount):
                # print(colorText.BOLD + colorText.FAIL + f"[+] Network Request timed-out. Going for {trial} of {self.configManager.maxNetworkRetryCount}th trial..." + colorText.END)
                return self.fetchURL(
                    url,
                    stream=stream,
                    trial=trial + 1,
                    params=params,
                    headers=headers,
                    timeout=timeout,
                )
        except Exception as e:
            # Something went wrong with the CachedSession.
            default_logger().debug(e, exc_info=True)
            if trial <= int(self.configManager.maxNetworkRetryCount):
                if trial <= 1:
                    # Let's try and restart the cache
                    self.configManager.restartRequestsCache()
                elif trial > 1 and requests_cache.is_installed():
                    # REstarting didn't fix it. We need to disable the cache
                    # altogether.
                    requests_cache.clear()
                    requests_cache.uninstall_cache()
                # print(colorText.BOLD + colorText.FAIL + f"[+] Network Request failed. Going for {trial} of {self.configManager.maxNetworkRetryCount}th trial..." + colorText.END)
                return self.fetchURL(
                    url,
                    stream=stream,
                    trial=trial + 1,
                    params=params,
                    headers=headers,
                    timeout=timeout,
                )
        if response is None and trial > 1 and not requests_cache.is_installed():
            # Let's try and re-enable the caching behaviour before exiting.
            # Maybe there was something wrong with this request, but the next
            # request should have access to cache.
            self.configManager.restartRequestsCache()
        return response
