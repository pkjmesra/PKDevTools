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

import multiprocessing
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()
import datetime
import json
from time import sleep

import pytz

from PKDevTools.classes.Fetcher import fetcher
from PKDevTools.classes.PKMultiProcessorClient import PKMultiProcessorClient
from PKDevTools.classes.Singleton import SingletonMixin, SingletonType
from PKDevTools.classes.Utils import random_user_agent

try:
    import cloudscraper
except BaseException:
    pass


class NSEMarketStatus(SingletonMixin, metaclass=SingletonType):
    def __init__(self, mp_dict={}, keyboardevent=None):
        super(NSEMarketStatus, self).__init__()
        self.marketStatus = mp_dict
        self.keyboardevent = keyboardevent

    @property
    def status(self):
        return self.marketStatus.get("marketStatus")

    @property
    def tradeDate(self):
        return self.marketStatus.get("tradeDate")

    @property
    def lastLevel(self):
        return self.marketStatus.get("last")

    @property
    def variation(self):
        return self.marketStatus.get("variation")

    @property
    def percentChange(self):
        return self.marketStatus.get("percentChange")

    @property
    def next_bell(self):
        return self.marketStatus.get("next_bell")

    def startMarketMonitor(self):
        worker = PKMultiProcessorClient(
            processorMethod=self.updateOnlineTradingStatus,
            keyboardInterruptEvent=self.keyboardevent,
            processorArgs=self.marketStatus,
        )
        worker.daemon = True
        worker.start()

    def shouldFetchNextBell(self):
        from PKDevTools.classes import Archiver

        fileName = "nse_next_bell.txt"
        next_bell, filePath, modifiedDateTime = Archiver.findFileInAppResultsDirectory(
            directory=Archiver.get_user_data_dir(), fileName=fileName
        )
        curr = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        if next_bell is not None:
            dtPart = next_bell.replace("T", " ").split("+")[0]
            lastBellDateTime = datetime.datetime.strptime(
                dtPart, "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=curr.tzinfo)
        shouldFetch = next_bell is None or (
            next_bell is not None
            and (curr.date() >= modifiedDateTime.date() and curr > lastBellDateTime)
        )
        return shouldFetch, next_bell, filePath, modifiedDateTime

    def getNextBell(self):
        # if 'unittest' in sys.modules or any("pytest" in arg for arg in sys.argv):
        #     return '2025-02-14T09:15:00+05:30'

        next_bell = self.marketStatus.get("next_bell")
        if next_bell is not None:
            return next_bell

        shouldFetch, next_bell, filePath, modifiedDateTime = self.shouldFetchNextBell()
        if shouldFetch:
            scraper = cloudscraper.create_scraper()
            url = "https://www.tradinghours.com/markets/nse-india"
            res = scraper.get(url)
            try:
                if res is None or res.status_code != 200:
                    return ""
                marketResp = res.text
                jsonDict = marketResp.split("window.Statuses = ")[
                                            1].split(";")[0]
                next_bell = json.loads(jsonDict)["IN.NSE"]["next_bell"]
                with open(filePath, "w") as f:
                    f.write(next_bell)
            except BaseException:
                next_bell = ""
                pass
        self.marketStatus["next_bell"] = next_bell
        return next_bell

    def updateOnlineTradingStatus(self, mp_dict={}):
        """
        This method is expected to be called only on a separate multiprocessing process/thread.
        DO NOT call this on main thread.

        Updates the `multi_dict` every minute and then sleeps for the next minute.
        """
        try:
            self.getNextBell()
        except BaseException:
            pass
        url = "https://www.nseindia.com/api/marketStatus"
        headers = {"user-agent": random_user_agent()}
        f = fetcher()
        try:
            res = f.fetchURL(url, headers=headers, timeout=10)
            if res is None or res.status_code != 200:
                return None, None
            marketResp = res.json()
            marketStates = marketResp["marketState"]
            for mktState in marketStates:
                if mktState["market"].lower() == "capital market":
                    self.marketStatus.update(mktState)
                    mp_dict.update(mktState)
                    break
        except BaseException:
            pass
        sleep(10)
