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
    import libsql
except BaseException:  # pragma: no cover
    print("Error loading libsql")
    pass
import contextlib
from enum import Enum
from time import sleep

import pyotp

from PKDevTools.classes.Environment import PKEnvironment
from PKDevTools.classes.log import default_logger
from PKDevTools.classes.PKDateUtilities import PKDateUtilities


class PKUserModel(Enum):
    """Enumeration representing the field mapping for User model database columns.

    Attributes:
        userid: Primary key identifier for the user
        username: Unique username/login identifier
        name: Full name of the user
        email: User's email address
        mobile: User's mobile number
        otpvaliduntil: Expiration timestamp for OTP validity
        totptoken: Secret token for TOTP generation
        subscriptionmodel: Type of subscription plan
        lastotp: Last generated OTP code
    """

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
    """Represents a scanner job with associated user subscriptions.

    Attributes:
        scannerId: Unique identifier for the scanner job
        userIds: List of user IDs subscribed to this scanner job
    """

    scannerId = ""
    userIds = []

    @staticmethod
    def scannerJobFromRecord(row):
        """Creates a PKScannerJob instance from a database record.

        Args:
            row: Database row tuple containing (scannerId, semicolon-separated userIds)

        Returns:
            PKScannerJob: Configured scanner job instance

        Example:
            >>> job = PKScannerJob.scannerJobFromRecord(('SCAN1', '123;456;123'))
            >>> job.scannerId
            'SCAN1'
            >>> job.userIds
            ['123', '456']
        """
        scanner = PKScannerJob()
        scanner.scannerId = row[0]
        scanner.userIds = []
        for user in str(row[1]).split(";"):
            scanner.userIds.append(user)
        if len(scanner.userIds) > 0:
            scanner.userIds = list(set(scanner.userIds))
        return scanner


class PKUser:
    """Data model representing a user in the system.

    Attributes:
        userid: Unique user identifier
        username: Login username
        name: Full name
        email: Email address
        mobile: Mobile number
        otpvaliduntil: OTP expiration timestamp
        totptoken: TOTP secret token
        subscriptionmodel: Subscription type
        lastotp: Last generated OTP
        balance: Account balance for alerts
        scannerJobs: List of subscribed scanner jobs
        customeField: Custom field placeholder
    """

    userid = 0
    username = ""
    name = ""
    email = ""
    mobile = 0
    otpvaliduntil = ""
    totptoken = ""
    subscriptionmodel = ""
    lastotp = ""
    balance = 0
    scannerJobs = []
    customeField = None

    @staticmethod
    def userFromDBRecord(row):
        """Creates a PKUser instance from a full database user record.

        Args:
            row: Database row tuple containing all user fields in PKUserModel order

        Returns:
            PKUser: Configured user instance

        Note:
            Handles rows with fewer than 9 fields by mapping remaining fields to None

        Example:
            >>> user = PKUser.userFromDBRecord((123, 'testuser', ...))
        """
        user = PKUser()
        user.userid = row[0] if len(row) > 0 else None
        if len(row) < 9:
            user.customeField = row[0] if len(row) > 0 else None
        user.username = row[1] if len(row) > 1 else None
        user.name = row[2] if len(row) > 2 else None
        user.email = row[3] if len(row) > 3 else None
        user.mobile = row[4] if len(row) > 4 else None
        user.otpvaliduntil = row[5] if len(row) > 5 else None
        user.totptoken = row[6] if len(row) > 6 else None
        user.subscriptionmodel = row[7] if len(row) > 7 else None
        user.lastotp = row[8] if len(row) > 8 else None
        return user

    @staticmethod
    def payingUserFromDBRecord(row):
        """Creates a PKUser instance from a limited payment-related record.

        Args:
            row: Database row tuple containing (userid, username, subscriptionmodel, balance)

        Returns:
            PKUser: User instance with payment-related fields populated

        Example:
            >>> user = PKUser.payingUserFromDBRecord((123, 'premium_user', 'premium', 100))
        """
        user = PKUser()
        user.userid = row[0] if len(row) > 0 else None
        user.username = row[1] if len(row) > 1 else None
        user.subscriptionmodel = row[2] if len(row) > 2 else None
        user.balance = row[3] if len(row) > 3 else None
        return user

    @staticmethod
    def userFromAlertsRecord(row, user=None):
        """Enriches a user instance with alert subscription data.

        Args:
            row: Database row tuple containing (userid, balance, semicolon-separated scanner jobs)
            user: Optional existing PKUser instance to enrich

        Returns:
            PKUser: User instance with alert data

        Example:
            >>> user = PKUser.userFromAlertsRecord((123, 50, 'SCAN1;SCAN2'))
        """
        if user is None:
            user = PKUser()
            user.userid = row[0]
        user.balance = row[1]
        user.scannerJobs = []
        for job in str(row[2]).split(";"):
            user.scannerJobs.append(str(job).upper())
        if len(user.scannerJobs) > 0:
            user.scannerJobs = list(set(user.scannerJobs))
        return user


class DBManager:
    """A database manager class for handling operations with Turso database using libsql."""

    def __init__(self):
        """Initialize the DBManager with connection parameters from environment.

        Reads TDU (Turso Database URL) and TAT (Turso Auth Token) from environment secrets.
        Initializes connection parameters but doesn't establish immediate connection.
        """
        try:
            local_secrets = PKEnvironment().allSecrets
            self.url = local_secrets["TDU"]
            self.token = local_secrets["TAT"]
        except Exception as e:  # pragma: no cover
            print(f"Could not init library (__init__):\n{e}")
            default_logger().debug(e, exc_info=True)
            self.url = None
            self.token = None
        self.conn = None

    def shouldSkipLoading(self):
        """Check if libsql is available for database operations.

        Returns:
            bool: True if libsql cannot be imported, False if it can be imported successfully.
        """
        skipLoading = False
        try:
            import libsql
        except Exception as e:  # pragma: no cover
            print(f"Could not load library (shouldSkipLoading):\n{e}")
            skipLoading = True
        return skipLoading

    def connection(self):
        """Establish and return a database connection.

        Creates a new connection if none exists. Uses Turso URL and auth token from initialization.

        Returns:
            libsql.Connection: An active database connection object.
        """
        try:
            if self.conn is None:
                # Connect to remote Turso database using libsql
                self.conn = libsql.connect(
    database=self.url, auth_token=self.token)
        except Exception as e:  # pragma: no cover
            print(f"Could not establish connection:\n{e}")
            default_logger().debug(e, exc_info=True)
        return self.conn

    def execute_query(self, query: str, params=None, commit: bool = False):
        """Execute a SQL query with proper error handling and connection management as well as with transaction control.

        Args:
            query (str): The SQL query to execute
            params (tuple, optional): Parameters for parameterized query
            commit: Whether to commit after execution (for writes)

        Returns:
            libsql.Cursor: A cursor object if successful
            None: If execution fails

        Raises:
            RuntimeError: If there's a database error
        """
        try:
            conn = self.connection()
            if conn is None:
                raise RuntimeError("Database connection failed")

            cursor = conn.cursor()

            # Ensure params is always a tuple or None
            if params is not None and not isinstance(params, (tuple, list)):
                params = (params,)

            # Execute with appropriate parameters
            if params:
                result = cursor.execute(query, params)
            else:
                result = cursor.execute(query)
            if commit:
                conn.commit()  # Explicit commit for writes
            return result

        except Exception as e:
            conn.rollback()  # Revert on error
            # Handle specific libsql errors
            if "panicked at" in str(e):
                raise RuntimeError(
                    "Database operation failed: internal error") from e
            default_logger().debug(
                f"Database error in query '{query}': {e}", exc_info=True
            )
            raise RuntimeError(f"Database operation failed: {str(e)}") from e
        finally:
            # Don't close connection here - let the caller manage it
            pass

    def validateOTP(self, userIDOrName, otp, validityIntervalInSeconds=30):
        """Validate a one-time password for a user.

        Args:
            userIDOrName (int/str): User ID or username to validate OTP for
            otp (str): The one-time password to validate
            validityIntervalInSeconds (int): Time window in seconds for OTP validity

        Returns:
            bool: True if OTP is valid, False otherwise

        Example:
            >>> db.validateOTP(123, "123456")
            True
        """
        try:
            otpValue = 0
            dbUsers = self.getUserByIDorUsername(userIDOrName)
            token = ""
            if len(dbUsers) > 0:
                token = dbUsers[0].totptoken
                lastOTP = dbUsers[0].lastotp
                if token is not None:
                    otpValue = str(
                        pyotp.TOTP(
    token, interval=int(validityIntervalInSeconds)).now()
                    )
            else:
                print(f"Could not locate user: {userIDOrName}")
        except Exception as e:  # pragma: no cover
            print(f"Could not locate user (validateOTP): {userIDOrName}\n{e}")
            default_logger().debug(e, exc_info=True)

        isValid = (otpValue == str(otp)) and int(otpValue) > 0
        if not isValid and len(token) > 0:
            isValid = pyotp.TOTP(token, interval=int(validityIntervalInSeconds)).verify(
                otp=otp, valid_window=60
            )
            default_logger().debug(
                f"User entered OTP: {otp} did not match machine generated OTP: {otpValue} while the DB OTP was: {lastOTP} with local config interval:{validityIntervalInSeconds}"
            )
            if not isValid and len(str(lastOTP)) > 0 and len(str(otp)) > 0:
                isValid = (
    str(otp) == str(lastOTP)) or (
        int(otp) == int(lastOTP))
        return isValid

    def refreshOTPForUser(self, user: PKUser, validityIntervalInSeconds=30):
        """Generate and store a new OTP for the specified user.

        Args:
            user (PKUser): User object to refresh OTP for
            validityIntervalInSeconds (int): Validity window for new OTP

        Returns:
            tuple: (success: bool, otpValue: str) where success indicates DB update status
        """
        otpValue = str(
            pyotp.TOTP(user.totptoken, interval=int(
                validityIntervalInSeconds)).now()
        )
        try:
            self.updateOTP(user.userid, otpValue, user.otpvaliduntil)
            return True, otpValue
        except Exception as e:  # pragma: no cover
            print(
                f"Could not refresh OTP (refreshOTPForUser) for user: {user.userid}\n{
                    e
                }"
            )
            default_logger().debug(e, exc_info=True)
            return False, otpValue

    def getOTP(
        self,
        userID,
        username=None,
        name=None,
        retry=False,
        validityIntervalInSeconds=86400,
    ):
        """Retrieve or generate OTP for a user with fallback creation logic.

        Args:
            userID (int): User ID to get OTP for
            username (str, optional): Username if creating new user
            name (str, optional): Name if creating new user
            retry (bool): Internal flag for retry logic
            validityIntervalInSeconds (int): OTP validity period

        Returns:
            tuple: (otp: str, subscriptionModel: str, subscriptionValidity: str, alertUser: PKUser)
        """
        try:
            otpValue = 0
            user = None
            dbUsers = self.getUserByID(int(userID))
            if len(dbUsers) > 0:
                dbUser = dbUsers[0]
                subscriptionModel = dbUser.subscriptionmodel
                subscriptionValidity = dbUser.otpvaliduntil
                otpStillValid = (
                    dbUser.otpvaliduntil is not None
                    and len(dbUser.otpvaliduntil) > 1
                    and PKDateUtilities.dateFromYmdString(dbUser.otpvaliduntil).date()
                    >= PKDateUtilities.currentDateTime().date()
                )
                otpValue = dbUser.lastotp if otpStillValid else otpValue
                if not retry:
                    if len(dbUsers) > 0:
                        token = dbUser.totptoken
                        if token is not None:
                            if not otpStillValid:
                                otpValue = str(
                                    pyotp.TOTP(
                                        token, interval=int(
                                            validityIntervalInSeconds)
                                    ).now()
                                )
                        else:
                            user = PKUser.userFromDBRecord(
                                [
                                    userID,
                                    str(username).lower(),
                                    name,
                                    dbUser.email,
                                    dbUser.mobile,
                                    dbUser.otpvaliduntil,
                                    pyotp.random_base32(),
                                    dbUser.subscriptionmodel,
                                    dbUser.lastotp,
                                ]
                            )
                            self.updateUser(user)
                            return self.getOTP(
                                userID, username, name, retry=True)
                    else:
                        user = PKUser.userFromDBRecord(
                            [
                                userID,
                                str(username).lower(),
                                name,
                                None,
                                None,
                                None,
                                pyotp.random_base32(),
                                None,
                                None,
                            ]
                        )
                        if not self.insertUser(user):
                            raise RuntimeError("Insert failed")
                        return self.getOTP(userID, username, name, retry=True)
            else:
                user = PKUser.userFromDBRecord(
                    [
                        userID,
                        str(username).lower(),
                        name,
                        None,
                        None,
                        None,
                        pyotp.random_base32(),
                        None,
                        None,
                    ]
                )
                if not self.insertUser(user):
                    raise RuntimeError("Insert failed")
                return self.getOTP(userID, username, name, retry=True)
        except Exception as e:  # pragma: no cover
            print(
                f"Could not get OTP (getOTP) for user: {
                    user.userid if user else 'unknown'
                }\n{e}"
            )
            default_logger().debug(e, exc_info=True)

        try:
            self.updateOTP(userID, otpValue)
        except Exception as e:  # pragma: no cover
            print(f"Could not get/update (getOTP) OTP for user: {userID}\n{e}")
            default_logger().debug(e, exc_info=True)

        alertUser = self.alertsForUser(userID, user=user)
        return otpValue, subscriptionModel, subscriptionValidity, alertUser

    def getUserByID(self, userID):
        """Retrieve user by their unique ID.

        Args:
            userID (int): The user ID to search for

        Returns:
            list[PKUser]: List of user objects (empty if not found)
        """
        users = []
        try:
            result = self.execute_query(
                "SELECT * FROM users WHERE userid = ?", (userID,)
            )
            if result:
                for row in result.fetchall():
                    users.append(PKUser.userFromDBRecord(row))
                if not users:
                    default_logger().debug(
                        f"User: {userID} not found! Probably needs registration?"
                    )
        except Exception as e:  # pragma: no cover
            print(f"Could not find user getUserByID: {userID}\n{e}")
            default_logger().debug(e, exc_info=True)
        return users

    def getUserByIDorUsername(self, userIDOrusername):
        """Retrieve user by either ID or username (case-insensitive).

        Args:
            userIDOrusername (int/str): Either user ID or username

        Returns:
            list[PKUser]: List of matching user objects
        """
        users = []
        try:
            try:
                userID = int(userIDOrusername)
                query = "SELECT * FROM users WHERE userid = ?"
                params = (userID,)
            except ValueError:
                query = "SELECT * FROM users WHERE username = ?"
                params = (str(userIDOrusername).lower(),)

            result = self.execute_query(query, params)
            if result:
                for row in result.fetchall():
                    users.append(PKUser.userFromDBRecord(row))
                if not users:
                    default_logger().debug(
                        f"User: {userIDOrusername} not found! Probably needs registration?"
                    )
                    print(
                        f"Could not locate user: {userIDOrusername}. Please reach out to the developer!"
                    )
                    sleep(3)
        except Exception as e:  # pragma: no cover
            print(
    f"Could not getUserByIDorUsername UserID: {userIDOrusername}\n{e}")
            default_logger().debug(e, exc_info=True)
        return users

    def insertUser(self, user: PKUser):
        """Insert a new user record into the database.

        Args:
            user (PKUser): User object containing all required fields

        Note:
            Requires userid, username, name, email, mobile, otpvaliduntil,
            totptoken, and subscriptionmodel fields
        """
        try:
            query = """
                INSERT INTO users(userid, username, name, email, mobile, otpvaliduntil, totptoken, subscriptionmodel)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                user.userid,
                str(user.username).lower(),
                user.name,
                user.email,
                user.mobile,
                user.otpvaliduntil,
                user.totptoken,
                user.subscriptionmodel,
            )

            result = self.execute_query(query, params, commit=True)
            if result and result.rowcount > 0:
                default_logger().debug(f"User: {user.userid} inserted!")
            return result.rowcount == 1
        except Exception as e:  # pragma: no cover
            print(f"Could not insertUser UserID: {user.userid}\n{e}")
            default_logger().debug(e, exc_info=True)
            return False

    def updateUser(self, user: PKUser):
        """Update all fields of an existing user record.

        Args:
            user (PKUser): User object with updated field values

        Note:
            Updates all fields for the user with matching userid
        """
        try:
            query = """
                UPDATE users
                SET username = ?, name = ?, email = ?, mobile = ?,
                    otpvaliduntil = ?, totptoken = ?, subscriptionmodel = ?, lastotp = ?
                WHERE userid = ?
            """
            params = (
                str(user.username).lower(),
                user.name,
                user.email,
                user.mobile,
                user.otpvaliduntil,
                user.totptoken,
                user.subscriptionmodel,
                user.lastotp,
                user.userid,
            )

            result = self.execute_query(query, params, commit=True)
            if result and result.rowcount > 0:
                default_logger().debug(f"User: {user.userid} updated!")
            return result.rowcount == 1
        except Exception as e:  # pragma: no cover
            print(f"Could not updateUser UserID: {user.userid}\n{e}")
            default_logger().debug(e, exc_info=True)
            return False

    def updateOTP(self, userID, otp, otpValidUntilDate=None):
        """Update the OTP and optionally its validity date for a user.

        Args:
            userID (int): User ID to update
            otp (str): New OTP value
            otpValidUntilDate (str, optional): Date string in YYYY-MM-DD format
        """
        try:
            if otpValidUntilDate is None:
                query = "UPDATE users SET lastotp = ? WHERE userid = ?"
                params = (otp, userID)
            else:
                query = (
                    "UPDATE users SET otpvaliduntil = ?, lastotp = ? WHERE userid = ?"
                )
                params = (otpValidUntilDate, otp, userID)

            result = self.execute_query(query, params, commit=True)
            if result and result.rowcount > 0:
                default_logger().debug(
    f"User: {userID} updated with otp: {otp}!")
            return result.rowcount == 1
        except Exception as e:  # pragma: no cover
            print(f"Could not updateOTP UserID: {userID}\n{e}")
            default_logger().debug(e, exc_info=True)
            return False

    def updateUserModel(self, userID, column: PKUserModel, columnValue=None):
        """Update a specific column for a user.

        Args:
            userID (int): User ID to update
            column (PKUserModel): Enum specifying which column to update
            columnValue: New value for the column (type depends on column)
        """
        try:
            query = f"UPDATE users SET {column.name} = ? WHERE userid = ?"
            params = (columnValue, userID)

            result = self.execute_query(query, params, commit=True)
            if result and result.rowcount > 0:
                default_logger().debug(
                    f"User: {userID} updated with {
    column.name}: {columnValue}!"
                )
            return result.rowcount == 1
        except Exception as e:  # pragma: no cover
            print(f"Could not updateUserModel UserID: {userID}\n{e}")
            default_logger().debug(e, exc_info=True)
            return False

    def getUsers(self, fieldName=None, where=None):
        """Retrieve users with optional field filtering and WHERE conditions.

        Args:
            fieldName (str, optional): Specific field(s) to retrieve
            where (str, optional): WHERE clause conditions

        Returns:
            list[PKUser]: List of matching user objects
        """
        users = []
        try:
            query = f"SELECT {'*' if fieldName is None else fieldName} FROM users {
                where if where is not None else ''
            }"
            result = self.execute_query(query)
            if result:
                for row in result.fetchall():
                    users.append(PKUser.userFromDBRecord(row))
                if not users:
                    default_logger().debug("Users not found!")
        except Exception as e:  # pragma: no cover
            print(f"Could not getUsers\n{e}")
            default_logger().debug(e, exc_info=True)
        return users

    def alertsForUser(self, userID: int, user: PKUser = None):
        """Retrieve alert subscription info for a user.

        Args:
            userID (int): User ID to lookup
            user (PKUser, optional): Existing user object to augment

        Returns:
            PKUser: User object with alert subscription data or None
        """
        try:
            users = []
            query = "SELECT * FROM alertsubscriptions where userId = ?"
            result = self.execute_query(
                query, (userID if user is None else user.userid,)
            )
            if result:
                for row in result.fetchall():
                    users.append(PKUser.userFromAlertsRecord(row, user=user))
                if not users:
                    default_logger().debug("Users not found!")
        except Exception as e:  # pragma: no cover
            print(f"Could not get alertsForUser\n{e}")
            default_logger().debug(e, exc_info=True)
        return users[0] if len(users) > 0 else None

    def scannerJobsWithActiveUsers(self):
        """Retrieve all scanner jobs that have subscribed users.

        Returns:
            list[PKScannerJob]: List of active scanner jobs
        """
        scanners = []
        try:
            result = self.execute_query(
                "SELECT * FROM scannerjobs where users != ''")
            if result:
                for row in result.fetchall():
                    scanners.append(PKScannerJob.scannerJobFromRecord(row))
                if not scanners:
                    default_logger().debug("Scanners not found!")
        except Exception as e:  # pragma: no cover
            print(f"Could not get scannerJobsWithActiveUsers\n{e}")
            default_logger().debug(e, exc_info=True)
        return scanners

    def usersForScannerJobId(self, scannerJobId: str):
        """Get all user IDs subscribed to a specific scanner job.

        Args:
            scannerJobId (str): Scanner job ID (case-insensitive)

        Returns:
            list[int]: List of subscribed user IDs
        """
        scanners = []
        try:
            query = "SELECT * FROM scannerjobs where scannerId = ?"
            result = self.execute_query(query, (str(scannerJobId).upper(),))
            if result:
                for row in result.fetchall():
                    scanners.append(PKScannerJob.scannerJobFromRecord(row))
                if not scanners:
                    default_logger().debug("Scanners not found!")
        except Exception as e:  # pragma: no cover
            print(f"Could not get scannerJobsWithActiveUsers\n{e}")
            default_logger().debug(e, exc_info=True)
        return scanners[0].userIds if len(scanners) > 0 else []

    def updateAlertSubscriptionModel(self, userID, charge: float, scanId: str):
        """Update user's balance and scanner job subscriptions.

        Args:
            userID (int): User ID to update
            charge (float): Amount to deduct from balance
            scanId (str): Scanner job ID to add

        Returns:
            bool: True if update was successful
        """
        success = False
        try:
            query = """
                UPDATE alertsubscriptions
                SET
                    balance = balance - ?,
                    scannerJobs = scannerJobs || ';' || ?
                WHERE userId = ?;
            """
            result = self.execute_query(
    query, (charge, scanId, userID), commit=True)
            if result and result.rowcount > 0:
                default_logger().debug(
                    f"User: {userID} updated with balance and scannerJobs!"
                )
                success = self.topUpScannerJobs(scanId, userID)
        except Exception as e:  # pragma: no cover
            print(
    f"Could not updateAlertSubscriptionModel UserID: {userID}\n{e}")
            default_logger().debug(e, exc_info=True)
        return success

    def topUpAlertSubscriptionBalance(self, userID, topup: float):
        """Add funds to user's alert subscription balance.

        Args:
            userID (int): User ID to update
            topup (float): Amount to add to balance

        Returns:
            bool: True if operation succeeded
        """
        success = False
        try:
            query = """
                INSERT INTO alertsubscriptions (userId, balance)
                VALUES (?, ?)
                ON CONFLICT(userId) DO UPDATE
                SET balance = balance + excluded.balance;
            """
            result = self.execute_query(query, (userID, topup), commit=True)
            if result and result.rowcount > 0:
                default_logger().debug(
    f"User: {userID} topped up with balance!")
                success = True
        except Exception as e:  # pragma: no cover
            print(
    f"Could not topUpAlertSubscriptionBalance UserID: {userID}\n{e}")
            default_logger().debug(e, exc_info=True)
        return success

    def topUpScannerJobs(self, scanId, userID):
        """Subscribe user to a scanner job.

        Args:
            scanId (str): Scanner job ID
            userID (int): User ID to subscribe

        Returns:
            bool: True if subscription succeeded
        """
        success = False
        try:
            query = """
                INSERT INTO scannerjobs (scannerId, users)
                VALUES (?, ?)
                ON CONFLICT(scannerId) DO UPDATE
                SET users = users || ';' || excluded.users;
            """
            result = self.execute_query(query, (scanId, userID), commit=True)
            if result and result.rowcount > 0:
                default_logger().debug(f"User: {userID} added to scanId!")
                success = True
        except Exception as e:  # pragma: no cover
            print(f"Could not topUpScannerJobs UserID: {userID}\n{e}")
            default_logger().debug(e, exc_info=True)
        return success

    def resetScannerJobs(self):
        """Clear all scanner jobs and user subscriptions.

        Returns:
            bool: True if both truncation and updates succeeded
        """
        success1 = False
        success2 = False
        try:
            result = self.execute_query("DELETE from scannerjobs", commit=True)
            if result:
                print(f"{result.rowcount} rows deleted from scannerjobs")
                success1 = True
        except Exception as e:  # pragma: no cover
            print(f"Could not deleteScannerJobs \n{e}")
            default_logger().debug(e, exc_info=True)

        try:
            result = self.execute_query(
                "UPDATE alertsubscriptions SET scannerJobs = ''", commit=True
            )
            if result:
                print(f"{result.rowcount} rows updated in alertsubscriptions")
                success2 = True
        except Exception as e:  # pragma: no cover
            print(f"Could not deleteScannerJobs \n{e}")
            default_logger().debug(e, exc_info=True)

        return success1 and success2

    def removeScannerJob(self, userID, scanId):
        """Unsubscribe user from scanner job and clean up empty jobs.

        Args:
            userID (int): User ID to unsubscribe
            scanId (str): Scanner job ID to remove

        Returns:
            bool: True if all steps completed successfully
        """
        success = False
        try:
            # Step 1: Remove job from user's alertsubscriptions table
            query_alertsubscriptions = """
                UPDATE alertsubscriptions
                SET scannerJobs =
                    CASE
                        WHEN scannerJobs = ? THEN ''
                        ELSE
                            TRIM(
                                REPLACE(
                                    REPLACE(
                                        ';' || scannerJobs || ';',
                                        ';' || ? || ';',
                                        ';'
                                    ),
                                    ';;', ';'
                                ),
                                ';'
                            )
                    END
                WHERE userId = ?;
            """
            result = self.execute_query(
                query_alertsubscriptions, (scanId, scanId, userID), commit=True
            )
            if result and result.rowcount > 0:
                default_logger().debug(
                    f"User: {userID} removed {scanId} from alertsubscriptions!"
                )
                success = True

            if success:
                # Step 2: Remove userId from scannerJobs table
                query_scanner_jobs = """
                    UPDATE scannerJobs
                    SET users =
                        CASE
                            WHEN users = ? THEN ''
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
                                )
                        END
                    WHERE scannerId = ?;
                """
                result = self.execute_query(
                    query_scanner_jobs, (str(userID), str(userID), scanId), commit=True
                )
                if result and result.rowcount > 0:
                    default_logger().debug(
                        f"User: {userID} removed {scanId} from scannerJobs!"
                    )
                    success = True

            if success:
                # Step 3: Delete row from scannerJobs if users column is empty
                query_delete_empty = """
                DELETE FROM scannerJobs WHERE scannerId = ? AND (users IS NULL OR users = '');
                """
                result = self.execute_query(
    query_delete_empty, (scanId,), commit=True)
                if result and result.rowcount > 0:
                    default_logger().debug(
                        f"{scanId} deleted from scannerJobs by User: {userID}!"
                    )
                    success = True
        except Exception as e:  # pragma: no cover
            print(
    f"Could not removeScannerJob: {scanId} for UserID: {userID}\n{e}")
            default_logger().debug(e, exc_info=True)
        return success

    def getPayingUsers(self):
        """Retrieve all users with active subscriptions or positive balance.

        Returns:
            list[PKUser]: List of paying users with subscription info
        """
        users = []
        try:
            query = """
                SELECT DISTINCT u.userId, u.username, u.subscriptionmodel, a.balance
                FROM users u
                LEFT JOIN alertsubscriptions a ON u.userId = a.userId
                WHERE COALESCE(a.balance, 0) > 0 OR (u.subscriptionmodel != '' and u.subscriptionmodel != '0');
            """
            result = self.execute_query(query)
            if result:
                for row in result.fetchall():
                    users.append(PKUser.payingUserFromDBRecord(row))
                if not users:
                    default_logger().debug("Paying Users not found!")
        except Exception as e:  # pragma: no cover
            print(f"Could not getPayingUsers\n{e}")
            default_logger().debug(e, exc_info=True)
        return users

    def addAlertSummary(self, user_id, scanner_id, timestamp=None):
        """Record that an alert was sent to a user.

        Args:
            user_id (int): Recipient user ID
            scanner_id (str): Scanner job ID that triggered alert
            timestamp (str, optional): Time of alert (defaults to now)
        """
        try:
            if timestamp is None:
                timestamp = PKDateUtilities.currentDateTime().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            query = """
                INSERT INTO alertssummary (userId, scannerId, timestamp)
                VALUES (?, ?, ?)
            """
            result = self.execute_query(
                query, (user_id, scanner_id, timestamp), commit=True
            )
            if result and result.rowcount > 0:
                default_logger().debug(
    f"addAlertSummary:User: {user_id} inserted!")
            return result.rowcount == 1
        except Exception as e:  # pragma: no cover
            print(f"Could not addAlertSummary UserID: {user_id}\n{e}")
            default_logger().debug(e, exc_info=True)
            return False

    @contextlib.contextmanager
    def transaction(self):
        """Provides a transactional scope around a series of operations."""
        conn = self.connection()
        try:
            yield conn  # The block of code inside 'with' runs here
            conn.commit()
        except Exception as e:
            conn.rollback()
            default_logger().error(f"Transaction failed: {e}")
            raise
        finally:
            pass  # Don't close connection - let the pool manage it
