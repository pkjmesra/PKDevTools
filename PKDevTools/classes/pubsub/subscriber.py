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

import uuid

import requests

from PKDevTools.classes.DBManager import DBManager
from PKDevTools.classes.pubsub.events import globalEventsSignal
from PKDevTools.classes.Singleton import SingletonMixin, SingletonType
from PKDevTools.classes.Telegram import send_message

DEV_CHANNEL_ID = "-1001785195297"


class PKNotificationService(SingletonMixin, metaclass=SingletonType):
    def __init__(self):
        super(PKNotificationService, self).__init__()
        # Subscribe to the event
        globalEventsSignal.connect(self.notify)

    def notify(self, sender, **kwargs):
        if "eventType" in kwargs:
            if kwargs["eventType"] == "ga":
                # Capture GA event
                event_name = kwargs["event_name"]
                event_params = kwargs["event_params"]
                if event_params is None:
                    event_params = {}

                payload = {
                    "client_id": str(uuid.uuid4()),  # Unique client ID for GA
                    "events": [{"name": event_name, "params": event_params}],
                }
                # Google Analytics API Details
                MEASUREMENT_ID = "G-T0TLV56Y0C"
                API_SECRET = "2dD6iqHQQl2EzhCvHXA7EQ"
                GA_ENDPOINT = f"https://www.google-analytics.com/mp/collect?measurement_id={MEASUREMENT_ID}&api_secret={API_SECRET}"

                try:
                    response = requests.post(GA_ENDPOINT, json=payload)
                    # if response.status_code == 204:
                    #     print(f"Event '{event_name}' sent successfully")
                    # else:
                    #     print(f"Error sending event: {response.text}")
                except Exception as e:
                    # print(f"Failed to send event: {e}")
                    pass
        else:
            notificationText = (
                kwargs["notification"] if "notification" in kwargs else ""
            )
            scannerID = kwargs["scannerID"] if "scannerID" in kwargs else ""
            print(
                f"[Notification] Notifying for {scannerID} with data: {notificationText}"
            )
            dbManager = DBManager()
            try:
                if len(str(scannerID)) > 0:
                    userIDs = dbManager.usersForScannerJobId(
                        scannerJobId=scannerID)
                    if len(userIDs) > 0:
                        for userID in userIDs:
                            send_message(
                                message=notificationText,
                                userID=userID,
                                parse_type="HTML",
                            )
                        send_message(
                            message=f"{notificationText}\nsent to {
    ','.join(userIDs)}",
                            userID=DEV_CHANNEL_ID,
                            parse_type="HTML",
                        )
                        # Let's now update the alerts summary
                        for userID in userIDs:
                            dbManager.addAlertSummary(
                                user_id=userID, scanner_id=scannerID
                            )
                    else:
                        send_message(
                            message=f"No user subscribed to {scannerID} but the alerts job is running!",
                            userID=DEV_CHANNEL_ID,
                            parse_type="HTML",
                        )
                else:
                    print(
                        f"Error encountered:\n0 length scannerID passed for {notificationText}"
                    )
                    send_message(
                        message=f"Error encountered:\n0 length scannerID passed for {notificationText}",
                        userID=DEV_CHANNEL_ID,
                        parse_type="HTML",
                    )
            except Exception as e:
                print(f"Error encountered:\n{e}")
                send_message(
                    message=f"Error encountered:\n{e}",
                    userID=DEV_CHANNEL_ID,
                    parse_type="HTML",
                )
                pass


# Ensure the subscriber is instantiated so it listens to events
notification_service = PKNotificationService()
