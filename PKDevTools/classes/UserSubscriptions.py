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

from PKDevTools.classes.DBManager import DBManager, PKUser, PKUserModel
from PKDevTools.classes.Pikey import PKPikey
from PKDevTools.classes.PKDateUtilities import PKDateUtilities


class PKSubscriptionModel(Enum):
    No_Subscription = 0
    One_Reg_Scan_Alerts_1_Day = 31
    One_Piped_Scan_Alerts_1_Day = 40
    All_Scans_1_Day = 130
    All_Scans_1_Week = 600
    All_Scans_1_Month = 2000
    All_Scans_6_Months = 11000
    All_Scans_1_Year = 22000


class PKUserSusbscriptions:
    @classmethod
    def subscriptionModelFromValue(self, subValue):
        try:
            model = PKSubscriptionModel(int(subValue))
        except ValueError:
            print(f"Value error for {subValue}")
            models = [
                int(x)
                for x in list(PKUserSusbscriptions().subscriptionValueKeyPairs.keys())
            ]
            import bisect

            models.sort()  # Ensure the list is sorted
            idx = bisect.bisect_right(models, int(subValue)) - 1
            modelValue = models[idx] if idx >= 0 else 0
            print(
    f"The best model for {subValue} was found to be {modelValue}")
            model = PKSubscriptionModel(modelValue)
        except Exception as e:
            pass
        return model

    @classmethod
    def updateSubscriptions(self):
        try:
            dbManager = DBManager()
            users = dbManager.getUsers()
            for user in users:
                PKUserSusbscriptions.updateUserSubscription(user, dbManager)
        except BaseException:
            pass

    @classmethod
    def updateSubscription(
        self,
        userID,
        subscription: PKSubscriptionModel = PKSubscriptionModel.No_Subscription,
        subValue=0,
    ):
        dbManager = DBManager()
        user = None
        dbUsers = dbManager.getUserByID(userID=userID)
        if len(dbUsers) > 0:
            user = dbUsers[0]
            if subValue > 0 and (
                subscription.value != subValue
                or subscription.value < PKSubscriptionModel.All_Scans_1_Day.value
            ):
                # Update the balance instead of the standard subscription
                toppedUp = dbManager.topUpAlertSubscriptionBalance(
                    userID=userID, topup=subValue
                )
                if not toppedUp:
                    print(
                        f"Could not top-up alert balance {subValue} for user:{userID}"
                    )
                return
            user.subscriptionmodel = str(subscription.value)
        else:
            user = PKUser.userFromDBRecord(
                [userID, "", "", "", "", "", "", str(subscription.value), 0]
            )
        dbManager.updateUserModel(
            userID, PKUserModel.subscriptionmodel, str(subscription.value)
        )
        PKUserSusbscriptions.updateUserSubscription(user, dbManager)

    @classmethod
    def updateUserSubscription(self, user: PKUser, dbManager: DBManager):
        # Let's remove the subscriptions for those for which the validity has already expired
        # or there is no subscription!
        # No subscription cases
        if (
            (
                user.subscriptionmodel is None
                or str(user.subscriptionmodel)
                == str(PKSubscriptionModel.No_Subscription.value)
                or str(user.subscriptionmodel) == ""
            )
            or
            # Validity of subscriptions expired!
            (
                user.otpvaliduntil is not None
                and len(user.otpvaliduntil) > 1
                and PKDateUtilities.dateFromYmdString(user.otpvaliduntil).date()
                < PKDateUtilities.currentDateTime().date()
            )
        ):
            # Remove such files and update user subscription back to
            # no_subscription
            PKPikey.removeSavedFile(str(user.userid))
            if len(str(user.subscriptionmodel)) > 0:
                print(
                    f"Subscription being updated/removed for user:{
                        user.userid
                    }, subscription: {user.subscriptionmodel}, validity: {
                        user.otpvaliduntil
                    }"
                )
                user.subscriptionmodel = "0"
                user.otpvaliduntil = ""
                otpUpdated, _ = dbManager.refreshOTPForUser(user)
                print(
                    f"Subscription {
                        'updated/removed'
                        if otpUpdated
                        else 'could NOT be updated/removed'
                    } for user:{user.userid}"
                )

        # Users having a valid existing subscription
        if (
            user.subscriptionmodel is not None
            and str(user.subscriptionmodel)
            != str(PKSubscriptionModel.No_Subscription.value)
            and len(str(user.subscriptionmodel)) > 1
        ) and (user.otpvaliduntil is not None and len(user.otpvaliduntil) > 1):
            # Update validity of subscription that are pre-existing
            # We just need to periodically update the OTP, leaving the
            # validity and subscription type unchanged.
            print(
                f"OTP being updated for user:{user.userid}, subscription: {
                    user.subscriptionmodel
                }, validity: {user.otpvaliduntil}"
            )
            created, fileKey = dbManager.refreshOTPForUser(user)
            if created:
                fileCreated = PKPikey.createFile(
                    str(user.userid), fileKey, "PKScreener"
                )
                print(f"OTP updated for user:{user.userid}")
                print(
                    f"Subscription file {
                        'updated' if fileCreated else 'could NOT be updated'
                    } for user:{user.userid}"
                )
            else:
                print(f"OTP could NOT be updated for user:{user.userid}")
                print(
    f"Subscription file could NOT be updated for user:{
        user.userid}")

        # Users having a valid existing subscription, probably the first time
        # subscription users
        if (
            user.subscriptionmodel is not None
            and str(user.subscriptionmodel)
            != str(PKSubscriptionModel.No_Subscription.value)
            and len(str(user.subscriptionmodel)) > 1
        ) and (user.otpvaliduntil is None or str(user.otpvaliduntil) == ""):
            # the subscription validity has not been updated so far
            # Update validity of subscription
            n = 1
            if user.subscriptionmodel == str(
                PKSubscriptionModel.All_Scans_1_Day.value):
                n = 1
            elif user.subscriptionmodel == str(
                PKSubscriptionModel.All_Scans_1_Week.value
            ):
                n = 6
            elif user.subscriptionmodel == str(
                PKSubscriptionModel.All_Scans_1_Month.value
            ):
                n = 29
            elif user.subscriptionmodel == str(
                PKSubscriptionModel.All_Scans_6_Months.value
            ):
                n = 179
            elif user.subscriptionmodel == str(
                PKSubscriptionModel.All_Scans_1_Year.value
            ):
                n = 364
            user.otpvaliduntil = PKDateUtilities.YmdStringFromDate(
                PKDateUtilities.currentDateTime(), n=n
            )
            created, fileKey = dbManager.refreshOTPForUser(user)
            if created:
                fileCreated = PKPikey.createFile(
                    str(user.userid), fileKey, "PKScreener"
                )
                print(
                    f"Subscription updated for user:{user.userid} to subscription: {
                        user.subscriptionmodel
                    }, validity: {user.otpvaliduntil}"
                )
                print(
                    f"Subscription file {
                        'updated' if fileCreated else 'could NOT be updated'
                    } for user:{user.userid}"
                )
            else:
                print(
                    f"Subscription could NOT be updated for user:{
                        user.userid
                    } to subscription: {user.subscriptionmodel}, validity: {
                        user.otpvaliduntil
                    }"
                )
                print(
    f"Subscription file could NOT be updated for user:{
        user.userid}")

    @classmethod
    def userExists(self, userID):
        dbManager = DBManager()
        dbusers = dbManager.getUserByID(userID)
        return len(dbusers) > 0

    @classmethod
    def userSubscribed(self, userID):
        dbManager = DBManager()
        dbusers = dbManager.getUserByID(userID)
        user = None
        if len(dbusers) > 0:
            user = dbusers[0]
        return (
            user is not None
            and (
                user.subscriptionmodel is not None
                and str(user.subscriptionmodel)
                != str(PKSubscriptionModel.No_Subscription.value)
                and len(str(user.subscriptionmodel)) > 1
            )
            and (
                user.otpvaliduntil is not None
                and len(user.otpvaliduntil) > 1
                and PKDateUtilities.dateFromYmdString(user.otpvaliduntil).date()
                >= PKDateUtilities.currentDateTime().date()
            )
        )

    @property
    def subscriptionKeyValuePairs(self):
        return {
            f"{PKSubscriptionModel.No_Subscription.name}": f"{str(PKSubscriptionModel.No_Subscription.value)}",
            f"{PKSubscriptionModel.One_Reg_Scan_Alerts_1_Day.name}": f"{str(PKSubscriptionModel.One_Reg_Scan_Alerts_1_Day.value)}",
            f"{PKSubscriptionModel.One_Piped_Scan_Alerts_1_Day.name}": f"{str(PKSubscriptionModel.One_Piped_Scan_Alerts_1_Day.value)}",
            f"{PKSubscriptionModel.All_Scans_1_Day.name}": f"{str(PKSubscriptionModel.All_Scans_1_Day.value)}",
            f"{PKSubscriptionModel.All_Scans_1_Week.name}": f"{str(PKSubscriptionModel.All_Scans_1_Week.value)}",
            f"{PKSubscriptionModel.All_Scans_1_Month.name}": f"{str(PKSubscriptionModel.All_Scans_1_Month.value)}",
            f"{PKSubscriptionModel.All_Scans_6_Months.name}": f"{str(PKSubscriptionModel.All_Scans_6_Months.value)}",
            f"{PKSubscriptionModel.All_Scans_1_Year.name}": f"{str(PKSubscriptionModel.All_Scans_1_Year.value)}",
        }

    @property
    def subscriptionValueKeyPairs(self):
        return {
            f"{PKSubscriptionModel.No_Subscription.value}": f"{str(PKSubscriptionModel.No_Subscription.name)}",
            f"{PKSubscriptionModel.One_Reg_Scan_Alerts_1_Day.value}": f"{str(PKSubscriptionModel.One_Reg_Scan_Alerts_1_Day.name)}",
            f"{PKSubscriptionModel.One_Piped_Scan_Alerts_1_Day.value}": f"{str(PKSubscriptionModel.One_Piped_Scan_Alerts_1_Day.name)}",
            f"{PKSubscriptionModel.All_Scans_1_Day.value}": f"{str(PKSubscriptionModel.All_Scans_1_Day.name)}",
            f"{PKSubscriptionModel.All_Scans_1_Week.value}": f"{str(PKSubscriptionModel.All_Scans_1_Week.name)}",
            f"{PKSubscriptionModel.All_Scans_1_Month.value}": f"{str(PKSubscriptionModel.All_Scans_1_Month.name)}",
            f"{PKSubscriptionModel.All_Scans_6_Months.value}": f"{str(PKSubscriptionModel.All_Scans_6_Months.name)}",
            f"{PKSubscriptionModel.All_Scans_1_Year.value}": f"{str(PKSubscriptionModel.All_Scans_1_Year.name)}",
        }
