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

import datetime
import email
import imaplib

from PKDevTools.classes.Environment import PKEnvironment


class PKGmailReader:
    @classmethod
    def getTransactions(
        self,
        user=None,
        password=None,
        label=None,
        senderEmail=None,
        forNthDayFromToday=0,
        utr=None,
    ):
        imap_url = "imap.gmail.com"
        try:
            mail = imaplib.IMAP4_SSL(imap_url)
            mail.login(user, password)
            # Make sure emails can be modified (not read-only)
            mail.select(label, readonly=False)  # Connect to the labeled inbox.
            today = datetime.date.today()
            pastDate = today - datetime.timedelta(forNthDayFromToday)
            date = pastDate.strftime("%d-%b-%Y")

            # result, data  = mail.search(None,f'FROM "{senderEmail}"',"UNSEEN")
            # result, data = mail.uid('search', None, "UNSEEN") # (ALL/UNSEEN)
            # Search for UNSEEN emails from the sender on a specific date
            result, data = mail.uid(
                "search", None, f'UNSEEN FROM "{senderEmail}" (SENTON %s)' % date
            )

            i = len(data[0].split())
            transactions = {}
            # if result == "OK":
            for x in range(i):
                latest_email_uid = data[0].split()[x]
                result, email_data = mail.uid(
    "fetch", latest_email_uid, "(RFC822)")
                # if result == "OK":
                # result, email_data = conn.store(num,'+FLAGS','\\Seen')
                # this might work to set flag to seen, if it doesn't already
                raw_email = email_data[0][1]
                raw_email_string = raw_email.decode("utf-8")
                email_message = email.message_from_string(raw_email_string)

                # Header Details
                date_tuple = email.utils.parsedate_tz(email_message["Date"])
                if date_tuple:
                    local_date = datetime.datetime.fromtimestamp(
                        email.utils.mktime_tz(date_tuple)
                    )
                    local_message_date = "%s" % (
                        str(local_date.strftime("%a, %d %b %Y %H:%M:%S"))
                    )
                email_from = str(
                    email.header.make_header(
                        email.header.decode_header(email_message["From"])
                    )
                )
                email_to = str(
                    email.header.make_header(
                        email.header.decode_header(email_message["To"])
                    )
                )
                subject = str(
                    email.header.make_header(
                        email.header.decode_header(email_message["Subject"])
                    )
                )

                # Body details
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True)
                        try:
                            bodyText = (
                                body.decode("utf-8", errors="ignore")
                                .replace("\r\n", "")
                                .replace("  ", "")
                            )
                            # Here's the summary of your transaction: Amount
                            # Credited: INR 2000.00 Account Number: XX0801 Date
                            # & Time: 31-01-25, 09:47:46 IST Transaction Info:
                            # UPI/P2A/614257008125/SPPACFI D/HDFC BANK
                            amountCredited = bodyText.split(
                                "INR ")[1].split(" ")[0]
                            dateAndTime = bodyText.split("Date & Time: ")[1].split(
                                " Transaction"
                            )[0]
                            transactionInfo = bodyText.split("Transaction Info: ")[
                                1
                            ].split(" Feel free")[0]
                            paymentMode = transactionInfo.split("/")[0]
                            # The UPI transaction reference number is a 12-digit alphanumeric code
                            # that identifies each Unified Payments Interface (UPI) transaction.
                            # It's also known as the Unique Transaction
                            # Reference (UTR) number.
                            transactionNumber = transactionInfo.split("/")[2]

                            if utr is not None and str(
                                transactionNumber) == str(utr):
                                # Mark email as read if UTR matches
                                mail.uid(
    "store", latest_email_uid, "+FLAGS", "\\Seen")

                            senderName = transactionInfo.split("/")[3]
                            senderBank = transactionInfo.split("/")[-1]
                            transactions[transactionNumber] = {
                                "UTR": transactionNumber,
                                "dateAndTime": dateAndTime,
                                "amountPaid": amountCredited,
                                "transactionInfo": transactionInfo,
                                "paymentMode": paymentMode,
                                "senderName": senderName,
                                "senderBank": senderBank,
                            }
                        except BaseException:
                            pass
                        # file_name = "email_" + str(x) + ".txt"
                        # output_file = open(file_name, 'w')
                        # output_file.write("From: %s\nTo: %s\nDate: %s\nSubject: %s\n\nBody: \n\n%s" %(email_from, email_to,local_message_date, subject, body.decode('utf-8',errors="ignore").replace("\r\n","").replace("  ","")))
                        # output_file.close()
                    else:
                        continue
                return transactions
        except Exception as e:
            print("Connection failed: {}".format(e))
            raise
        return transactions

    @classmethod
    def getTransactionsDict(self, forNthDayFromToday=0, utr=None):
        secrets = PKEnvironment().allSecrets
        trans = PKGmailReader.getTransactions(
            secrets["MCU"],
            secrets["MCAP"],
            secrets["MCL"],
            secrets["MS"],
            forNthDayFromToday=forNthDayFromToday,
            utr=utr,
        )
        return trans

    @classmethod
    def matchUTR(self, utr=None):
        if utr is not None and len(str(utr)) > 1:
            foundTransaction = None
            for days in [0, 1, 2, 3]:
                try:
                    transactions = PKGmailReader.getTransactionsDict(
                        forNthDayFromToday=days, utr=utr
                    )
                    if str(utr) in transactions.keys():
                        foundTransaction = transactions.get(str(utr))
                        break
                except BaseException:
                    pass
            if foundTransaction is not None:
                return foundTransaction
        return None
