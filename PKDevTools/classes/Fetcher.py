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

import urllib
from datetime import timedelta

import requests
import requests_cache
from requests.exceptions import ConnectTimeout, ReadTimeout
from requests_cache import CachedSession
from urllib3.exceptions import ReadTimeoutError

from PKDevTools.classes.ColorText import colorText
from PKDevTools.classes.log import default_logger

requests.packages.urllib3.util.connection.HAS_IPV6 = False
session = CachedSession(
    "PKDevTools_cache",
    expire_after=timedelta(hours=6),
    stale_if_error=True,
)

# This Class Handles Fetching of any Data over the internet

class fetcher:
    def __init__(self):
        self._proxy = None
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
            default_logger().debug(e, exc_info=True)
            proxy = None
        return proxy

    def postURL(self, url, data=None, headers={}, maxNetworkRetryCount=10, timeout=2, trial=1):
        try:
            response = None
            requestor = session
            # We should try to switch to requests lib if cached_session 
            # begin to give some problem after we've tried for
            # 50% of the configured retrials.
            if trial >= int(maxNetworkRetryCount/2):
                requestor = requests
            response = requestor.post(
                            url,
                            proxies=self.proxyServer,
                            data = data,
                            headers=headers,
                            timeout=trial*timeout,
                        )
        except (ConnectTimeout,ReadTimeoutError,ReadTimeout) as e:
            default_logger().debug(e, exc_info=True)
            if trial <= int(maxNetworkRetryCount):
                print(colorText.BOLD + colorText.FAIL + f"[+] Network Request timed-out. Going for {trial} of {maxNetworkRetryCount}th trial..." + colorText.END, end="")
                return self.postURL(url, data=data, headers=headers, maxNetworkRetryCount=maxNetworkRetryCount, timeout=timeout, trial=trial+1)
        except Exception as e:
            # Something went wrong with the CachedSession.
            default_logger().debug(e, exc_info=True)
            if trial <= int(maxNetworkRetryCount):
                if trial <= 1:
                    # Let's try and restart the cache
                    self.restartRequestsCache()
                elif trial > 1 and requests_cache.is_installed():
                    # REstarting didn't fix it. We need to disable the cache altogether.
                    requests_cache.clear()
                    requests_cache.uninstall_cache()
                print(colorText.BOLD + colorText.FAIL + f"[+] Network Request failed. Going for {trial} of {maxNetworkRetryCount}th trial..." + colorText.END, end="")
                return self.postURL(url, data=data, headers=headers, maxNetworkRetryCount=maxNetworkRetryCount, timeout=timeout, trial=trial+1)
        if trial > 1 and not requests_cache.is_installed():
            # Let's try and re-enable the caching behaviour before exiting.
            # Maybe there was something wrong with this request, but the next
            # request should have access to cache.
            self.restartRequestsCache()
        return response

    def fetchURL(self, url, stream=False, maxNetworkRetryCount=10, timeout=2, trial=1):
        try:
            response = None
            requestor = session
            # We should try to switch to requests lib if cached_session 
            # begin to give some problem after we've tried for
            # 50% of the configured retrials.
            if trial >= int(maxNetworkRetryCount/2):
                requestor = requests
            response = requestor.get(
                            url,
                            proxies=self.proxyServer,
                            stream = stream,
                            timeout=trial*timeout,
                        ) 
        except (ConnectTimeout,ReadTimeoutError,ReadTimeout) as e:
            default_logger().debug(e, exc_info=True)
            if trial <= int(maxNetworkRetryCount):
                print(colorText.BOLD + colorText.FAIL + f"[+] Network Request timed-out. Going for {trial} of {maxNetworkRetryCount}th trial..." + colorText.END, end="")
                return self.fetchURL(url, stream=stream, maxNetworkRetryCount=maxNetworkRetryCount, timeout=timeout, trial=trial+1)
        except Exception as e:
            # Something went wrong with the CachedSession.
            default_logger().debug(e, exc_info=True)
            if trial <= int(maxNetworkRetryCount):
                if trial <= 1:
                    # Let's try and restart the cache
                    self.restartRequestsCache()
                elif trial > 1 and requests_cache.is_installed():
                    # REstarting didn't fix it. We need to disable the cache altogether.
                    requests_cache.clear()
                    requests_cache.uninstall_cache()
                print(colorText.BOLD + colorText.FAIL + f"[+] Network Request failed. Going for {trial} of {maxNetworkRetryCount}th trial..." + colorText.END, end="")
                return self.fetchURL(url, stream=stream, maxNetworkRetryCount=maxNetworkRetryCount, timeout=timeout, trial=trial+1)
        if trial > 1 and not requests_cache.is_installed():
            # Let's try and re-enable the caching behaviour before exiting.
            # Maybe there was something wrong with this request, but the next
            # request should have access to cache.
            self.restartRequestsCache()
        return response

    def restartRequestsCache(self):
        try:
            if requests_cache.is_installed():
                requests_cache.clear()
                requests_cache.uninstall_cache()
            self.deleteFileWithPattern("*_cache.sqlite")
            requests_cache.install_cache('PKDevTools_cache')
        except Exception as e:
            default_logger().debug(e, exc_info=True)