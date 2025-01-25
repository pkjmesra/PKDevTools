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
from enum import Enum
from PKDevTools.classes.DBManager import DBManager
from PKDevTools.classes.Pikey import PKPikey

class PKSubscriptionModel(Enum):
    No_Subscription = 0
    One_Day = 130
    One_Week = 600
    One_Month = 2000
    Six_Months = 11000
    One_Year = 22000

class PKUserSusbscriptions:

    @classmethod
    def updateSubscriptions(self):
        try:
            dbManager = DBManager()
            users = dbManager.getUsers()
            for user in users:
                if user.subscriptionmodel is None or \
                    str(user.subscriptionmodel) == str(PKSubscriptionModel.No_Subscription.value) or \
                        str(user.subscriptionmodel) == "":
                    created, fileKey = dbManager.refreshOTPForUser(user)
                    if created:
                        PKPikey.createFile(str(user.userid),fileKey,"PKScreener")
        except:
            pass

    @property
    def subscriptionKeyValuePairs(self):
        return {f"{PKSubscriptionModel.No_Subscription.name}":f"{str(PKSubscriptionModel.No_Subscription.value)}",
                f"{PKSubscriptionModel.One_Day.name}":f"{str(PKSubscriptionModel.One_Day.value)}",
                f"{PKSubscriptionModel.One_Week.name}":f"{str(PKSubscriptionModel.One_Week.value)}",
                f"{PKSubscriptionModel.One_Month.name}":f"{str(PKSubscriptionModel.One_Month.value)}",
                f"{PKSubscriptionModel.Six_Months.name}":f"{str(PKSubscriptionModel.Six_Months.value)}",
                f"{PKSubscriptionModel.One_Year.name}":f"{str(PKSubscriptionModel.One_Year.value)}"
                }

    @property
    def subscriptionValueKeyPairs(self):
        return {f"{PKSubscriptionModel.No_Subscription.value}":f"{str(PKSubscriptionModel.No_Subscription.name)}",
                f"{PKSubscriptionModel.One_Day.value}":f"{str(PKSubscriptionModel.One_Day.name)}",
                f"{PKSubscriptionModel.One_Week.value}":f"{str(PKSubscriptionModel.One_Week.name)}",
                f"{PKSubscriptionModel.One_Month.value}":f"{str(PKSubscriptionModel.One_Month.name)}",
                f"{PKSubscriptionModel.Six_Months.value}":f"{str(PKSubscriptionModel.Six_Months.name)}",
                f"{PKSubscriptionModel.One_Year.value}":f"{str(PKSubscriptionModel.One_Year.name)}"
                }