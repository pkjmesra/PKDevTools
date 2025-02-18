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
try:
    import libsql_client as libsql
except: # pragma: no cover
    print("Error loading libsql_client!")
    pass
import pyotp
from time import sleep
from enum import Enum
from PKDevTools.classes.log import default_logger
from PKDevTools.classes.Environment import PKEnvironment
from PKDevTools.classes.PKDateUtilities import PKDateUtilities

class PKUserModel(Enum):
        userid = 0
        username = 1
        name = 2
        email = 3
        mobile = 4
        otpvaliduntil = 5
        totptoken = 6
        subscriptionmodel = 7
        lastotp = 8

class PKScannerJob:
    scannerId=''
    userIds=[]

    def scannerJobFromRecord(row):
        scanner = PKScannerJob()
        scanner.scannerId= row[0]
        scanner.userIds = []
        for user in str(row[1]).split(";"):
            scanner.userIds.append(user)
        if len(scanner.userIds) > 0:
            # Only unique values
            scanner.userIds = list(set(scanner.userIds))
        return scanner
    
class PKUser:
    userid=0
    username=""
    name=""
    email=""
    mobile=0
    otpvaliduntil=""
    totptoken=""
    subscriptionmodel=""
    lastotp=""
    balance = 0
    scannerJobs = []
    customeField = None

    def userFromDBRecord(row):
        user = PKUser()
        user.userid= row[0] if len(row) > 0 else None
        if len(row) < 9:
            user.customeField = row[0] if len(row) > 0 else None
        user.username= row[1] if len(row) > 1 else None
        user.name= row[2] if len(row) > 2 else None
        user.email= row[3] if len(row) > 3 else None
        user.mobile= row[4] if len(row) > 4 else None
        user.otpvaliduntil= row[5] if len(row) > 5 else None
        user.totptoken= row[6] if len(row) > 6 else None
        user.subscriptionmodel= row[7] if len(row) > 7 else None
        user.lastotp= row[8] if len(row) > 8 else None
        return user

    def payingUserFromDBRecord(row):
        user = PKUser()
        user.userid= row[0] if len(row) > 0 else None
        user.subscriptionmodel = row[1] if len(row) > 1 else None
        user.balance= row[2] if len(row) > 2 else None
        return user

    def userFromAlertsRecord(row,user=None):
        if user is None:
            user = PKUser()
            user.userid= row[0]
        user.balance= row[1]
        user.scannerJobs = []
        for job in str(row[2]).split(";"):
            user.scannerJobs.append(str(job).upper())
        if len(user.scannerJobs) > 0:
            # Only unique values
            user.scannerJobs = list(set(user.scannerJobs))
        return user

class DBManager:
    
    def __init__(self):
        try:
            local_secrets = PKEnvironment().allSecrets
            self.url = local_secrets["TDU"]
            self.token = local_secrets["TAT"]
        except Exception as e: # pragma: no cover
            print(f"Could not init library (__init__):\n{e}")
            default_logger().debug(e, exc_info=True)
            # print(e)
            self.url = None
            self.token = None
        self.conn = None
    
    def shouldSkipLoading(self):
        skipLoading = False
        try:
            import libsql_client as libsql
        except Exception as e: # pragma: no cover
            print(f"Could not load library (shouldSkipLoading):\n{e}")
            skipLoading = True
            pass
        return skipLoading
    
    def connection(self):
        try:
            if self.conn is None:
                # self.conn = libsql.connect("pkscreener.db", sync_url=self.url, auth_token=self.token)
                # self.conn.sync()
                self.conn = libsql.create_client_sync(self.url,auth_token=self.token)
        except Exception as e: # pragma: no cover
            print(f"Could not establish connection:\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        return self.conn

    def validateOTP(self,userIDOrName,otp,validityIntervalInSeconds=30):
        try:
            otpValue = 0
            dbUsers = self.getUserByIDorUsername(userIDOrName)
            token = ""
            if len(dbUsers) > 0:
                token = dbUsers[0].totptoken
                lastOTP = dbUsers[0].lastotp
                if token is not None:
                    otpValue = str(pyotp.TOTP(token,interval=int(validityIntervalInSeconds)).now())
            else:
                print(f"Could not locate user: {userIDOrName}")
        except Exception as e: # pragma: no cover
            print(f"Could not locate user (validateOTP): {userIDOrName}\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        isValid = (otpValue == str(otp)) and int(otpValue) > 0
        if not isValid and len(token) > 0:
            isValid = pyotp.TOTP(token,interval=int(validityIntervalInSeconds)).verify(otp=otp,valid_window=60)
            default_logger().debug(f"User entered OTP: {otp} did not match machine generated OTP: {otpValue} while the DB OTP was: {lastOTP} with local config interval:{validityIntervalInSeconds}")
            if not isValid and len(str(lastOTP)) > 0 and len(str(otp)) > 0:
                isValid = (str(otp) == str(lastOTP)) or (int(otp) == int(lastOTP))
        return isValid

    def refreshOTPForUser(self,user:PKUser,validityIntervalInSeconds=30):
        otpValue = str(pyotp.TOTP(user.totptoken,interval=int(validityIntervalInSeconds)).now())
        try:
            self.updateOTP(user.userid,otpValue,user.otpvaliduntil)
            return True, otpValue
        except Exception as e: # pragma: no cover
            print(f"Could not refresh OTP (refreshOTPForUser) for user: {user.userid}\n{e}")
            default_logger().debug(e, exc_info=True)
            return False, otpValue

    def getOTP(self,userID,username=None,name=None,retry=False,validityIntervalInSeconds=86400):
        try:
            otpValue = 0
            user = None
            dbUsers = self.getUserByID(int(userID))
            if len(dbUsers) > 0:
                dbUser = dbUsers[0]
                subscriptionModel = dbUser.subscriptionmodel
                subscriptionValidity = dbUser.otpvaliduntil
                otpStillValid = (dbUser.otpvaliduntil is not None and len(dbUser.otpvaliduntil) > 1 and \
                    PKDateUtilities.dateFromYmdString(dbUser.otpvaliduntil).date() >= PKDateUtilities.currentDateTime().date())
                otpValue = dbUser.lastotp if otpStillValid else otpValue
                if not retry:
                    if len(dbUsers) > 0:
                        token = dbUser.totptoken
                        if token is not None:
                            if not otpStillValid:
                                otpValue = str(pyotp.TOTP(token,interval=int(validityIntervalInSeconds)).now())
                        else:
                            # Update user
                            user = PKUser.userFromDBRecord([userID,str(username).lower(),name,dbUser.email,dbUser.mobile,dbUser.otpvaliduntil,pyotp.random_base32(),dbUser.subscriptionmodel,dbUser.lastotp])
                            self.updateUser(user)
                            return self.getOTP(userID,username,name,retry=True)
                    else:
                        # Insert user
                        user = PKUser.userFromDBRecord([userID,str(username).lower(),name,None,None,None,pyotp.random_base32(),None,None])
                        self.insertUser(user)
                        return self.getOTP(userID,username,name,retry=True)
            else:
                # Insert user
                user = PKUser.userFromDBRecord([userID,str(username).lower(),name,None,None,None,pyotp.random_base32(),None,None])
                self.insertUser(user)
                return self.getOTP(userID,username,name,retry=True)
        except Exception as e: # pragma: no cover
            print(f"Could not get OTP (getOTP) for user: {user.userid}\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        try:
            self.updateOTP(userID,otpValue)
        except Exception as e: # pragma: no cover
            print(f"Could not get/update (getOTP) OTP for user: {user.userid}\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        alertUser = self.alertsForUser(userID,user=user)
        return otpValue, subscriptionModel, subscriptionValidity, alertUser

    def getUserByID(self,userID):
        try:
            users = []
            cursor = self.connection() #.cursor()
            records = cursor.execute(f"SELECT * FROM users WHERE userid={self.sanitisedIntValue(userID)}") #.fetchall()
            for row in records.rows:
                users.append(PKUser.userFromDBRecord(row))
            # cursor.close()
            if len(records.columns) > 0 and len(records.rows) <= 0:
                # Let's tell the user
                default_logger().debug(f"User: {userID} not found! Probably needs registration?")
        except Exception as e: # pragma: no cover
            print(f"Could not find user getUserByID: {userID}\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        finally:
            if self.conn is not None:
                self.conn.close()
                self.conn = None
        return users

    def getUserByIDorUsername(self,userIDOrusername):
        try:
            users = []
            cursor = self.connection() #.cursor()
            try:
                userID = int(userIDOrusername)
            except Exception as e: # pragma: no cover
                print(f"Invalid UserID: {userIDOrusername}\n{e}")
                userID = 0
                pass
            if userID == 0:
                records = cursor.execute(f"SELECT * FROM users WHERE username={self.sanitisedStrValue(str(userIDOrusername).lower())}") #.fetchall()
            else:
                records = cursor.execute(f"SELECT * FROM users WHERE userid={self.sanitisedIntValue(userID)}") #.fetchall()
            for row in records.rows:
                users.append(PKUser.userFromDBRecord(row))
            if len(records.columns) > 0 and len(records.rows) <= 0:
                # Let's tell the user
                default_logger().debug(f"User: {userIDOrusername} not found! Probably needs registration?")
                print(f"Could not locate user: {userIDOrusername}. Please reach out to the developer!")
                sleep(3)
        except Exception as e: # pragma: no cover
            print(f"Could not getUserByIDorUsername UserID: {userIDOrusername}\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        finally:
            if self.conn is not None:
                self.conn.close()
                self.conn = None
        return users
    
    def insertUser(self,user:PKUser):
        try:
            result = self.connection().execute(f"INSERT INTO users(userid,username,name,email,mobile,otpvaliduntil,totptoken,subscriptionmodel) VALUES ({self.sanitisedIntValue(user.userid)},{self.sanitisedStrValue(str(user.username).lower())},{self.sanitisedStrValue(user.name)},{self.sanitisedStrValue(user.email)},{self.sanitisedIntValue(user.mobile)},{self.sanitisedStrValue(user.otpvaliduntil)},{self.sanitisedStrValue(user.totptoken)},{self.sanitisedStrValue(user.subscriptionmodel)});")
            if result.rows_affected > 0 and result.last_insert_rowid is not None:
                default_logger().debug(f"User: {user.userid} inserted as last row ID: {result.last_insert_rowid}!")
            # self.connection().commit()
            # self.connection().sync()
        except Exception as e: # pragma: no cover
            print(f"Could not insertUser UserID: {user.userid}\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        finally:
            if self.conn is not None:
                self.conn.close()
                self.conn = None
    
    def sanitisedStrValue(self,param):
        return "''" if param is None else f"'{param}'"

    def sanitisedIntValue(self,param):
        return param if param is not None else 0

    def updateUser(self,user:PKUser):
        try:
            result = self.connection().execute(f"UPDATE users SET username={self.sanitisedStrValue(str(user.username).lower())},name={self.sanitisedStrValue(user.name)},email={self.sanitisedStrValue(user.email)},mobile={self.sanitisedIntValue(user.mobile)},otpvaliduntil={self.sanitisedStrValue(user.otpvaliduntil)},totptoken={self.sanitisedStrValue(user.totptoken)},subscriptionmodel={self.sanitisedStrValue(user.subscriptionmodel)},lastotp={self.sanitisedStrValue(user.lastotp)} WHERE userid={self.sanitisedIntValue(user.userid)}")
            if result.rows_affected > 0:
                default_logger().debug(f"User: {user.userid} updated!")
        except Exception as e: # pragma: no cover
            print(f"Could not updateUser UserID: {user.userid}\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        finally:
            if self.conn is not None:
                self.conn.close()
                self.conn = None

    def updateOTP(self,userID,otp,otpValidUntilDate=None):
        try:
            if otpValidUntilDate is None:
                result = self.connection().execute(f"UPDATE users SET lastotp={self.sanitisedStrValue(otp)} WHERE userid={self.sanitisedIntValue(userID)}")
            elif otpValidUntilDate is not None:
                result = self.connection().execute(f"UPDATE users SET otpvaliduntil={self.sanitisedStrValue(otpValidUntilDate)},lastotp={self.sanitisedStrValue(otp)} WHERE userid={self.sanitisedIntValue(userID)}")
            if result.rows_affected > 0:
                default_logger().debug(f"User: {userID} updated with otp: {otp}!")
        except Exception as e: # pragma: no cover
            print(f"Could not updateOTP UserID: {userID}\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        finally:
            if self.conn is not None:
                self.conn.close()
                self.conn = None
    
    def updateUserModel(self,userID,column:PKUserModel,columnValue=None):
        try:
            result = self.connection().execute(f"UPDATE users SET {column.name}={self.sanitisedStrValue(columnValue) if type(columnValue) == str else self.sanitisedIntValue(columnValue)} WHERE userid={self.sanitisedIntValue(userID)}")
            if result.rows_affected > 0:
                default_logger().debug(f"User: {userID} updated with {column.name}: {columnValue}!")
        except Exception as e: # pragma: no cover
            print(f"Could not updateUserModel UserID: {userID}\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        finally:
            if self.conn is not None:
                self.conn.close()
                self.conn = None

    def getUsers(self,fieldName=None,where=None):
        """
        Returns all active PKUser instances in the database or an empty list if none is found.
        Returns only the fieldName if requested.
        """
        try:
            users = []
            cursor = self.connection() #.cursor()
            records = cursor.execute(f"SELECT {'*' if fieldName is None else fieldName} FROM users {where if where is not None else ''}") #.fetchall()
            for row in records.rows:
                users.append(PKUser.userFromDBRecord(row))
            # cursor.close()
            if len(records.columns) > 0 and len(records.rows) <= 0:
                # Let's tell the user
                default_logger().debug(f"Users not found!")
        except Exception as e: # pragma: no cover
            print(f"Could not getUsers\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        finally:
            if self.conn is not None:
                self.conn.close()
                self.conn = None
        return users

    def alertsForUser(self,userID:int,user:PKUser=None):
        """
        Returns a PKUser instance with user's updated balance for daily alerts 
        and relevant subscribed scannerJobs for a given userID or None.
        """
        try:
            users = []
            cursor = self.connection()
            records = cursor.execute(f"SELECT * FROM alertsubscriptions where userId={self.sanitisedIntValue(userID if user is None else user.userid)}")
            for row in records.rows:
                users.append(PKUser.userFromAlertsRecord(row,user=user))
            # cursor.close()
            if len(records.columns) > 0 and len(records.rows) <= 0:
                default_logger().debug(f"Users not found!")
        except Exception as e: # pragma: no cover
            print(f"Could not get alertsForUser\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        finally:
            if self.conn is not None:
                self.conn.close()
                self.conn = None
        return users[0] if len(users) > 0 else None

    def scannerJobsWithActiveUsers(self):
        """
        Returns all such PKScannerJob instances with (scannerIDs and subscribed userIds)
        where there's at least one subscribed user.
        """
        try:
            scanners = []
            cursor = self.connection()
            records = cursor.execute(f"SELECT * FROM scannerjobs where users != ''")
            for row in records.rows:
                scanners.append(PKScannerJob.scannerJobFromRecord(row))
            if len(records.columns) > 0 and len(records.rows) <= 0:
                default_logger().debug(f"Scanners not found!")
        except Exception as e: # pragma: no cover
            print(f"Could not get scannerJobsWithActiveUsers\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        finally:
            if self.conn is not None:
                self.conn.close()
                self.conn = None
        return scanners
    
    def usersForScannerJobId(self,scannerJobId:str):
        """
        Returns userIds that are subscribed to a given scannerJobId or an 
        empty list if that scannerJobId is not found.
        """
        try:
            scanners = []
            cursor = self.connection()
            records = cursor.execute(f"SELECT * FROM scannerjobs where scannerId = {self.sanitisedStrValue(str(scannerJobId).upper())}")
            for row in records.rows:
                scanners.append(PKScannerJob.scannerJobFromRecord(row))
            if len(records.columns) > 0 and len(records.rows) <= 0:
                default_logger().debug(f"Scanners not found!")
        except Exception as e: # pragma: no cover
            print(f"Could not get scannerJobsWithActiveUsers\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        finally:
            if self.conn is not None:
                self.conn.close()
                self.conn = None
        return scanners[0].userIds if len(scanners) > 0 else []

    def updateAlertSubscriptionModel(self,userID,charge:float,scanId:str):
        """
        Updates alertsubscriptions with balance update as well as scanner jobs 
        for a given user in the same table
        """
        try:
            success = False
            result = self.connection().execute("""
                                            UPDATE alertsubscriptions
                                            SET 
                                                balance = balance - ?,
                                                scannerJobs = scannerJobs || ';' || ?
                                            WHERE userId = ?;
                                        """, (charge, scanId, userID))
            if result.rows_affected > 0:
                default_logger().debug(f"User: {userID} updated with balance and scannerJobs!")
                success = self.topUpScannerJobs(scanId,userID)
        except Exception as e: # pragma: no cover
            print(f"Could not updateAlertSubscriptionModel UserID: {userID}\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        finally:
            if self.conn is not None:
                self.conn.close()
                self.conn = None
        return success

    def topUpAlertSubscriptionBalance(self,userID,topup:float):
        """
        Handles a new user insertion as well as update.

        If UserID does not exist, a new row is inserted with the given Balance.
        If UserID already exists, only the Balance is updated by adding the new amount 
        (Balance + excluded.Balance).
        """
        try:
            success = False
            result = self.connection().execute("""
                                            INSERT INTO alertsubscriptions (userId, balance) 
                                            VALUES (?, ?) 
                                            ON CONFLICT(userId) DO UPDATE 
                                            SET balance = balance + excluded.balance;
                                        """, (userID,topup))
            if result.rows_affected > 0:
                default_logger().debug(f"User: {userID} topped up with balance !")
                success = True
        except Exception as e: # pragma: no cover
            print(f"Could not topUpAlertSubscriptionBalance UserID: {userID}\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        finally:
            if self.conn is not None:
                self.conn.close()
                self.conn = None
        return success

    def topUpScannerJobs(self,scanId,userID):
        """
        Handles a new user insertion as well as update for a given scanId.

        If scanId does not exist, a new row is inserted with the given userId.
        If scanId already exists, only the users is updated by adding the new userId 
        """
        try:
            success = False
            result = self.connection().execute("""
                                            INSERT INTO scannerjobs (scannerId, users) 
                                            VALUES (?, ?) 
                                            ON CONFLICT(scannerId) DO UPDATE 
                                            SET users = users || ';' || excluded.users;
                                        """, (scanId,userID))
            if result.rows_affected > 0:
                default_logger().debug(f"User: {userID} added to scanId !")
                success = True
        except Exception as e: # pragma: no cover
            print(f"Could not topUpScannerJobs UserID: {userID}\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        finally:
            if self.conn is not None:
                self.conn.close()
                self.conn = None
        return success

    def resetScannerJobs(self):
        """
        Truncates scannerJobs and clears all jobs from users' alert subscriptions
        """
        try:
            success1 = False
            result = self.connection().execute("DELETE from scannerjobs")
            if result.rows_affected > 0:
                default_logger().debug(f"scannerJobs truncated !")
                success1 = True
            print(f"{result.rows_affected} rows deleted from scannerjobs")
        except Exception as e: # pragma: no cover
            print(f"Could not deleteScannerJobs \n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        finally:
            if self.conn is not None:
                self.conn.close()
                self.conn = None
        try:
            success2 = False
            result = self.connection().execute("""
                                            UPDATE alertsubscriptions
                                            SET scannerJobs = ''
                                        """)
            if result.rows_affected > 0:
                default_logger().debug(f"alertsubscriptions updated with cleaned up scannerJobs!")
                success2 = True
            print(f"{result.rows_affected} rows updated in alertsubscriptions")
        except Exception as e: # pragma: no cover
            print(f"Could not deleteScannerJobs \n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        finally:
            if self.conn is not None:
                self.conn.close()
                self.conn = None
        return success1 and success2

    def removeScannerJob(self,userID, scanId):
        """
        Removes scanId from scannerJobs column in alertsubscriptions
        
        Removes userID from the users column in scannerJobs

        Deletes the row in scannerJobs if no more userIds are left
        """
        try:
            success = False
            # Step 1: Remove job from user's alertsubscriptions table
            query_alertsubscriptions = """
                UPDATE alertsubscriptions
                SET scannerJobs = 
                    CASE 
                        WHEN scannerJobs = ? THEN ''  -- If the only job, set to empty string
                        ELSE 
                            TRIM(
                                REPLACE(
                                    REPLACE(
                                        ';' || scannerJobs || ';',  -- Add extra delimiters to prevent partial replacements
                                        ';' || ? || ';', 
                                        ';'
                                    ), 
                                    ';;', ';'  -- Fix extra semicolons
                                ),
                                ';'
                            )  -- Trim leading/trailing semicolon
                    END
                WHERE userId = ?;
                """
            result = self.connection().execute(query_alertsubscriptions, (scanId,scanId,userID))
            if result.rows_affected > 0:
                default_logger().debug(f"User: {userID} removed {scanId} from alertsubscriptions!")
                success = True
            if success:
                # Step 2: Remove userId from scannerJobs table
                query_scanner_jobs = """
                    UPDATE scannerJobs
                    SET users = 
                        CASE 
                            WHEN users = ? THEN ''  -- If the only user, set to empty string
                            ELSE 
                                TRIM(
                                    REPLACE(
                                        REPLACE(
                                            ';' || users || ';',
                                            ';' || ? || ';', 
                                            ';'
                                        ), 
                                        ';;', ';'
                                    ),
                                    ';'
                                )  -- Trim leading/trailing semicolon
                        END
                    WHERE scannerId = ?;
                    """
                result = self.connection().execute(query_scanner_jobs, (str(userID),str(userID),scanId))
                if result.rows_affected > 0:
                    default_logger().debug(f"User: {userID} removed {scanId} from scannerJobs!")
                    success = True
            if success:
                # Step 3: Delete row from scannerJobs if users column is empty
                query_delete_empty = """
                DELETE FROM scannerJobs WHERE scannerId = ? AND (users IS NULL OR users = '');
                """
                result = self.connection().execute(query_delete_empty, (scanId,))
                if result.rows_affected > 0:
                    default_logger().debug(f"{scanId} deleted from scannerJobs by User: {userID} !")
                    success = True
        except Exception as e: # pragma: no cover
            print(f"Could not removeScannerJob: {scanId} for UserID: {userID}\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        finally:
            if self.conn is not None:
                self.conn.close()
                self.conn = None
        return success

    def getPayingUsers(self):
        """
        Returns all active PKUser instances in the database who either have a subscription model
        or have a alerts balance.
        """
        try:
            users = []
            cursor = self.connection() #.cursor()
            query_paying_users = """
                SELECT DISTINCT u.userId, u.subscriptionmodel, a.balance
                FROM users u
                LEFT JOIN alertsubscriptions a ON u.userId = a.userId
                WHERE COALESCE(a.balance, 0) > 0 OR (u.subscriptionmodel != '' and u.subscriptionmodel != '0');

            """
            records = cursor.execute(query_paying_users)
            for row in records.rows:
                users.append(PKUser.payingUserFromDBRecord(row))
            # cursor.close()
            if len(records.columns) > 0 and len(records.rows) <= 0:
                # Let's tell the user
                default_logger().debug(f"Paying Users not found!")
        except Exception as e: # pragma: no cover
            print(f"Could not getPayingUsers\n{e}")
            default_logger().debug(e, exc_info=True)
            pass
        finally:
            if self.conn is not None:
                self.conn.close()
                self.conn = None
        return users
