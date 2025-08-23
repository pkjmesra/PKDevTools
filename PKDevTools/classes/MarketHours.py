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

from PKDevTools.classes.Singleton import SingletonType


class MarketHours(metaclass=SingletonType):
    def __init__(self, openHour=9, openMinute=15,
                 closeHour=15, closeMinute=30):
        super(MarketHours, self).__init__()
        self._openHour = openHour
        self._openMinute = openMinute
        self._closeHour = closeHour
        self._closeMinute = closeMinute

    def setMarketOpenHourMinute(self, hourMinute: str):
        self._openHour = int(hourMinute.split(":")[0])
        self._openMinute = int(hourMinute.split(":")[1])

    def setMarketCloseHourMinute(self, hourMinute: str):
        self._closeHour = int(hourMinute.split(":")[0])
        self._closeMinute = int(hourMinute.split(":")[1])

    @property
    def openHour(self):
        return self._openHour

    @property
    def openMinute(self):
        return self._openMinute

    @property
    def closeHour(self):
        return self._closeHour

    @property
    def closeMinute(self):
        return self._closeMinute
