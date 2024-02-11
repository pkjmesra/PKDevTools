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
import calendar
import numpy as np
import pytz
import pandas as pd
import datetime
import requests
from datetime import timezone
from PKDevTools.classes.Fetcher import fetcher

class PKDateUtilities:
    def utc_to_ist(utc_dt):
        return (
            pytz.utc.localize(utc_dt)
            .replace(tzinfo=timezone.utc)
            .astimezone(tz=pytz.timezone("Asia/Kolkata"))
        )

    def last_day_of_month(any_day):
        weekday, lastDay = calendar.monthrange(any_day.year, any_day.month)
        return PKDateUtilities.currentDateTime(simulate=True,day=lastDay,year=any_day.year,month=any_day.month)

    def last_day_of_previous_month(any_day):
        first = any_day.replace(day=1)
        last_day_last_month = first - datetime.timedelta(days=1)
        return last_day_last_month

    def tradingDate(simulate=False, day=None):
        lastTradingDate = None
        curr = PKDateUtilities.currentDateTime(simulate=simulate, day=day)
        if simulate:
            lastTradingDate = curr.replace(day=day).date()
        else:
            if PKDateUtilities.isTradingWeekday() and PKDateUtilities.ispreMarketTime():
                # Monday to Friday but before 9:15AM.So the date should be yesterday
                lastTradingDate = (curr - datetime.timedelta(days=1)).date()
            if PKDateUtilities.isTradingTime() or PKDateUtilities.ispostMarketTime():
                # Monday to Friday but after 9:15AM or after 15:30.So the date should be today
                lastTradingDate = curr.date()
            if not PKDateUtilities.isTradingWeekday():
                # Weekends .So the date should be last Friday
                lastTradingDate = (curr - datetime.timedelta(days=(curr.weekday() - 4))).date()
        while PKDateUtilities.isHoliday(lastTradingDate)[0] or not PKDateUtilities.isTradingWeekday(lastTradingDate):
            lastTradingDate = PKDateUtilities.previousTradingDate(lastTradingDate)
        return lastTradingDate
    
    def previousTradingDate(d1=None):
        if isinstance(d1,str):
            d1 = PKDateUtilities.dateFromYmdString(d1)
        lastTradingDate = (d1 - datetime.timedelta(days=1))
        while PKDateUtilities.isHoliday(lastTradingDate)[0] or not PKDateUtilities.isTradingWeekday(lastTradingDate):
            lastTradingDate = PKDateUtilities.previousTradingDate(lastTradingDate)
        if isinstance(lastTradingDate,datetime.datetime):
            lastTradingDate = lastTradingDate.date()
        return lastTradingDate

    def dateFromYmdString(Ymd=None):
        today = PKDateUtilities.currentDateTime()
        return datetime.datetime.strptime(Ymd, "%Y-%m-%d").replace(tzinfo=today.tzinfo)
    
    def dateFromdbYString(dbY=None):
        today = PKDateUtilities.currentDateTime()
        return datetime.datetime.strptime(dbY, "%d-%b-%Y").replace(tzinfo=today.tzinfo)

    def days_between(d1, d2):
        return abs((d2 - d1).days)

    def trading_days_between(d1, d2):
        _, hList = PKDateUtilities.holidayList()
        return np.busday_count(
            d1, d2
        ,weekmask=[1,1,1,1,1,0,0],holidays=hList)

    def nthPastTradingDateStringFromFutureDate(n=0,d1=None):
        if d1 is None:
            d1 = PKDateUtilities.tradingDate()
        counter = n
        d2 = (d1 - datetime.timedelta(days=counter))
        if isinstance(d2,datetime.datetime):
            d2 = d2.date()
        while PKDateUtilities.trading_days_between(d2,d1) != n:
            d2 = (d1 - datetime.timedelta(days=counter+1))
            if isinstance(d2,datetime.datetime):
                d2 = d2.date()
            counter += 1
        return d2.strftime("%Y-%m-%d")

    def currentDateTime(simulate=False, day=None, hour=None, minute=None, month=None, year=None):
        curr = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        if simulate:
            return curr.replace(year=year if year is not None else curr.year,
                                month=month if month is not None else curr.month,
                                day=day if day is not None else curr.day,
                                hour=hour if hour is not None else curr.hour,
                                minute=minute if minute is not None else curr.minute,)
        else:
            return curr

    def isTradingTime():
        curr = PKDateUtilities.currentDateTime()
        openTime = curr.replace(hour=9, minute=15)
        closeTime = curr.replace(hour=15, minute=30)
        return (openTime <= curr <= closeTime) and PKDateUtilities.isTradingWeekday()

    def isTradingWeekday(checkDate=None):
        if checkDate is None:
            checkDate = PKDateUtilities.currentDateTime()
        return 0 <= checkDate.weekday() <= 4

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
        f = fetcher()
        res = f.fetchURL(url, headers=headers)
        if res is None or res.status_code != 200:
            return None
        try:
            cm = res.json()["CM"]  # CM = Capital Markets
            df = pd.DataFrame(cm)
            df = df[["tradingDate", "weekDay", "description"]]
            df.loc[:, "description"] = df.loc[:, "description"].apply(
                lambda x: x.replace("\r", "")
            )
            df.loc[:, "tradingDate"] = df.loc[:, "tradingDate"].apply(
                lambda x: PKDateUtilities.dateFromdbYString(x).strftime("%Y-%m-%d")
            )
            return df, df['tradingDate'].tolist()
        except Exception:  # pragma: no cover
            return None

    def isHoliday(d1=None):
        if isinstance(d1,str):
            d1 = PKDateUtilities.dateFromYmdString(d1)
        today = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        if isinstance(d1,datetime.datetime):
            curr = d1.replace(tzinfo=today.tzinfo)
        else:
            curr = d1
        holidays,_ = PKDateUtilities.holidayList()
        if holidays is None:
            return False, None

        today = curr.strftime("%Y-%m-%d")
        occasion = None
        for holiday in holidays["tradingDate"]:
            if today in holiday:
                occasion = holidays[holidays["tradingDate"] == holiday]["description"].iloc[
                    0
                ]
                break
        return occasion is not None, occasion
    
    def isTodayHoliday():
        curr = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        return PKDateUtilities.isHoliday(curr)
