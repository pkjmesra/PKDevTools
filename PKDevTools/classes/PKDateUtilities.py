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
import numpy as np
import pytz
import pandas as pd
import datetime
import requests
from datetime import timezone

class PKDateUtilities:
    def utc_to_ist(utc_dt):
        return (
            pytz.utc.localize(utc_dt)
            .replace(tzinfo=timezone.utc)
            .astimezone(tz=pytz.timezone("Asia/Kolkata"))
        )

    def tradingDate(simulate=False, day=None):
        curr = PKDateUtilities.currentDateTime(simulate=simulate, day=day)
        if simulate:
            return curr.replace(day=day)
        else:
            if PKDateUtilities.isTradingWeekday() and PKDateUtilities.ispreMarketTime():
                # Monday to Friday but before 9:15AM.So the date should be yesterday
                return (curr - datetime.timedelta(days=1)).date()
            if PKDateUtilities.isTradingTime() or PKDateUtilities.ispostMarketTime():
                # Monday to Friday but after 9:15AM or after 15:30.So the date should be today
                return curr.date()
            if not PKDateUtilities.isTradingWeekday():
                # Weekends .So the date should be last Friday
                return (curr - datetime.timedelta(days=(curr.weekday() - 4))).date()

    def dateFromYmdString(Ymd=None):
        return datetime.datetime.strptime(Ymd, "%Y-%m-%d")

    def days_between(d1, d2):
        return abs((d2 - d1).days)

    def trading_days_between(d1, d2):
        return np.busday_count(
            d1, d2
        )  # ,weekmask=[1,1,1,1,1,0,0],holidays=['2020-01-01'])

    def currentDateTime(simulate=False, day=None, hour=None, minute=None):
        curr = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        if simulate:
            return curr.replace(day=day if day is not None else curr.day,
                                hour=hour if hour is not None else curr.hour,
                                minute=minute if minute is not None else curr.minute,)
        else:
            return curr

    def isTradingTime():
        curr = PKDateUtilities.currentDateTime()
        openTime = curr.replace(hour=9, minute=15)
        closeTime = curr.replace(hour=15, minute=30)
        return (openTime <= curr <= closeTime) and PKDateUtilities.isTradingWeekday()

    def isTradingWeekday():
        curr = PKDateUtilities.currentDateTime()
        return 0 <= curr.weekday() <= 4

    def ispreMarketTime():
        curr = PKDateUtilities.currentDateTime()
        openTime = curr.replace(hour=9, minute=15)
        return (openTime > curr) and PKDateUtilities.isTradingWeekday()

    def ispostMarketTime():
        curr = PKDateUtilities.currentDateTime()
        closeTime = curr.replace(hour=15, minute=30)
        return (closeTime < curr) and PKDateUtilities.isTradingWeekday()

    def isClosingHour():
        curr = PKDateUtilities.currentDateTime()
        openTime = curr.replace(hour=15, minute=00)
        closeTime = curr.replace(hour=15, minute=30)
        return (openTime <= curr <= closeTime) and PKDateUtilities.isTradingWeekday()

    def secondsAfterCloseTime():
        curr = PKDateUtilities.currentDateTime()  # (simulate=True,day=7,hour=8,minute=14)
        closeTime = curr.replace(hour=15, minute=30)
        return (curr - closeTime).total_seconds()

    def secondsBeforeOpenTime():
        curr = PKDateUtilities.currentDateTime()  # (simulate=True,day=7,hour=8,minute=14)
        openTime = curr.replace(hour=9, minute=15)
        return (curr - openTime).total_seconds()

    def nextRunAtDateTime(bufferSeconds=3600, cronWaitSeconds=300):
        curr = PKDateUtilities.currentDateTime()  # (simulate=True,day=7,hour=8,minute=14)
        nextRun = curr + datetime.timedelta(seconds=cronWaitSeconds)
        if 0 <= curr.weekday() <= 4:
            daysToAdd = 0
        else:
            daysToAdd = 7 - curr.weekday()
        if PKDateUtilities.isTradingTime():
            nextRun = curr + datetime.timedelta(seconds=cronWaitSeconds)
        else:
            # Same day after closing time
            secondsAfterClosingTime = PKDateUtilities.secondsAfterCloseTime()
            if secondsAfterClosingTime > 0:
                if secondsAfterClosingTime <= bufferSeconds:
                    nextRun = curr + datetime.timedelta(
                        days=daysToAdd,
                        seconds=1.5 * cronWaitSeconds
                        + bufferSeconds
                        - secondsAfterClosingTime,
                    )
                elif secondsAfterClosingTime > (bufferSeconds + 1.5 * cronWaitSeconds):
                    # Same day, upto 11:59:59pm
                    curr = curr + datetime.timedelta(
                        days=3 if curr.weekday() == 4 else 1
                    )
                    nextRun = curr.replace(hour=9, minute=15) - datetime.timedelta(
                        days=daysToAdd, seconds=1.5 * cronWaitSeconds + bufferSeconds
                    )
            elif secondsAfterClosingTime < 0:
                # Next day
                nextRun = curr.replace(hour=9, minute=15) - datetime.timedelta(
                    days=daysToAdd, seconds=1.5 * cronWaitSeconds + bufferSeconds
                )
        return nextRun
    
    def holidayList():
        url = "https://raw.githubusercontent.com/pkjmesra/PKScreener/main/.github/dependencies/nse-holidays.json"
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers)
        if res is None or res.status_code != 200:
            return None
        try:
            cm = res.json()["CM"]  # CM = Capital Markets
            df = pd.DataFrame(cm)
            df = df[["tradingDate", "weekDay", "description"]]
            df.loc[:, "description"] = df.loc[:, "description"].apply(
                lambda x: x.replace("\r", "")
            )
            return df
        except Exception:  # pragma: no cover
            return None


    def isTodayHoliday():
        holidays = PKDateUtilities.holidayList()
        if holidays is None:
            return False, None

        curr = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        today = curr.strftime("%d-%b-%Y")
        occasion = None
        for holiday in holidays["tradingDate"]:
            if today in holiday:
                occasion = holidays[holidays["tradingDate"] == holiday]["description"].iloc[
                    0
                ]
                break
        return occasion is not None, occasion
