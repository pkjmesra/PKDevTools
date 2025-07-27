import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta
import libsql
from PKDevTools.classes.DBManager import DBManager, PKUser, PKScannerJob, PKUserModel
from PKDevTools.classes.PKDateUtilities import PKDateUtilities

@pytest.fixture
def db_manager():
    """Fixture that provides a DBManager instance with mocked connection."""
    with patch('libsql.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        manager = DBManager()
        manager.url = "test.db"
        manager.token = "test_token"
        manager.conn = mock_conn
        
        # Common mock setup
        mock_cursor.execute.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        yield manager, mock_conn, mock_cursor

@pytest.fixture
def sample_user():
    """Fixture that provides a sample PKUser instance."""
    user = PKUser()
    user.userid = 123
    user.username = "testuser"
    user.name = "Test User"
    user.email = "test@example.com"
    user.mobile = "1234567890"
    user.totptoken = "TESTTOKEN123"
    user.subscriptionmodel = "premium"
    return user

@pytest.fixture
def sample_scanner_job():
    """Fixture that provides a sample PKScannerJob instance."""
    job = PKScannerJob()
    job.scannerId = "SCAN1"
    job.userIds = ["123", "456"]
    return job

class TestDBManager:
    
    def test_connection(self, db_manager):
        """Test establishing a database connection."""
        manager, mock_conn, _ = db_manager
        conn = manager.connection()
        assert conn == mock_conn
        libsql.connect.assert_called_once_with(database="test.db", auth_token="test_token")

    def test_validate_otp_valid(self, db_manager, sample_user):
        """Test OTP validation with valid OTP."""
        manager, _, mock_cursor = db_manager
        mock_cursor.fetchall.return_value = [
            (123, "testuser", "Test User", "test@example.com", 
             "1234567890", None, "TESTTOKEN123", "premium", "123456")
        ]
        
        # Mock pyotp verification
        with patch('pyotp.TOTP.verify', return_value=True):
            result = manager.validateOTP(123, "123456")
            assert result is True

    def test_get_user_by_id(self, db_manager, sample_user):
        """Test retrieving user by ID."""
        manager, _, mock_cursor = db_manager
        mock_cursor.fetchall.return_value = [
            (123, "testuser", "Test User", "test@example.com", 
             "1234567890", None, "TESTTOKEN123", "premium", None)
        ]
        
        users = manager.getUserByID(123)
        assert len(users) == 1
        assert users[0].userid == 123
        mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM users WHERE userid = ?", (123,)
        )

    def test_insert_user(self, db_manager, sample_user):
        """Test inserting a new user."""
        manager, mock_conn, mock_cursor = db_manager
        mock_cursor.rowcount = 1
        
        manager.insertUser(sample_user)
        
        expected_query = """
            INSERT INTO users(userid, username, name, email, mobile, 
            otpvaliduntil, totptoken, subscriptionmodel)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        mock_cursor.execute.assert_called_once_with(
            expected_query.strip(),
            (123, "testuser", "Test User", "test@example.com", 
             "1234567890", None, "TESTTOKEN123", "premium")
        )
        mock_conn.commit.assert_called_once()

    def test_update_user(self, db_manager, sample_user):
        """Test updating user information."""
        manager, mock_conn, mock_cursor = db_manager
        mock_cursor.rowcount = 1
        
        manager.updateUser(sample_user)
        
        expected_query = """
            UPDATE users 
            SET username = ?, name = ?, email = ?, mobile = ?, 
                otpvaliduntil = ?, totptoken = ?, subscriptionmodel = ?, lastotp = ?
            WHERE userid = ?
        """
        mock_cursor.execute.assert_called_once_with(
            expected_query.strip(),
            ("testuser", "Test User", "test@example.com", "1234567890",
             None, "TESTTOKEN123", "premium", None, 123)
        )
        mock_conn.commit.assert_called_once()

    def test_get_scanner_jobs_with_active_users(self, db_manager, sample_scanner_job):
        """Test retrieving scanner jobs with active users."""
        manager, _, mock_cursor = db_manager
        mock_cursor.fetchall.return_value = [
            ("SCAN1", "123;456")
        ]
        
        jobs = manager.scannerJobsWithActiveUsers()
        assert len(jobs) == 1
        assert jobs[0].scannerId == "SCAN1"
        assert jobs[0].userIds == ["123", "456"]
        mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM scannerjobs where users != ''"
        )

    def test_top_up_alert_subscription_balance(self, db_manager):
        """Test adding funds to user's alert subscription balance."""
        manager, mock_conn, mock_cursor = db_manager
        mock_cursor.rowcount = 1
        
        result = manager.topUpAlertSubscriptionBalance(123, 50.0)
        assert result is True
        
        expected_query = """
            INSERT INTO alertsubscriptions (userId, balance) 
            VALUES (?, ?) 
            ON CONFLICT(userId) DO UPDATE 
            SET balance = balance + excluded.balance;
        """
        mock_cursor.execute.assert_called_once_with(
            expected_query.strip(), (123, 50.0)
        )
        mock_conn.commit.assert_called_once()

    def test_reset_scanner_jobs(self, db_manager):
        """Test resetting all scanner jobs."""
        manager, mock_conn, mock_cursor = db_manager
        mock_cursor.rowcount = 1
        
        result = manager.resetScannerJobs()
        assert result is True
        
        # Check delete call
        calls = [
            call("DELETE from scannerjobs"),
            call("UPDATE alertsubscriptions SET scannerJobs = ''")
        ]
        mock_cursor.execute.assert_has_calls(calls, any_order=False)
        assert mock_conn.commit.call_count == 2

    def test_add_alert_summary(self, db_manager):
        """Test recording an alert summary."""
        manager, mock_conn, mock_cursor = db_manager
        mock_cursor.rowcount = 1
        
        test_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with patch('PKDevTools.classes.PKDateUtilities.PKDateUtilities.currentDateTime') as mock_dt:
            mock_dt.return_value.strftime.return_value = test_time
            
            manager.addAlertSummary(123, "SCAN1")
            
            expected_query = """
                INSERT INTO alertssummary (userId, scannerId, timestamp)
                VALUES (?, ?, ?)
            """
            mock_cursor.execute.assert_called_once_with(
                expected_query.strip(), (123, "SCAN1", test_time)
            )
            mock_conn.commit.assert_called_once()

    def test_remove_scanner_job(self, db_manager):
        """Test removing a scanner job subscription."""
        manager, mock_conn, mock_cursor = db_manager
        mock_cursor.rowcount = 1
        
        result = manager.removeScannerJob(123, "SCAN1")
        assert result is True
        
        # Check the sequence of queries executed
        expected_calls = [
            call("""
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
            """.strip(), ("SCAN1", "SCAN1", 123)),
            call("""
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
            """.strip(), ("123", "123", "SCAN1")),
            call("""
                DELETE FROM scannerJobs WHERE scannerId = ? AND (users IS NULL OR users = '');
            """.strip(), ("SCAN1",))
        ]
        
        mock_cursor.execute.assert_has_calls(expected_calls)
        assert mock_conn.commit.call_count == 3