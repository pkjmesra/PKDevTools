# PKDevTools API Reference

Complete API documentation for all public classes and functions in PKDevTools.

---

## Table of Contents

- [Data Providers](#data-providers)
- [Logging](#logging)
- [Database](#database)
- [Environment](#environment)
- [HTTP Client](#http-client)
- [Telegram](#telegram)
- [GitHub Integration](#github-integration)
- [Multiprocessing](#multiprocessing)
- [Events (Pub/Sub)](#events-pubsub)
- [Utilities](#utilities)

---

## Data Providers

### PKDataProvider

Unified high-performance stock data provider.

```python
from PKDevTools.classes.PKDataProvider import PKDataProvider, get_data_provider
```

#### `get_data_provider() -> PKDataProvider`

Factory function to get singleton instance.

**Returns**: `PKDataProvider` instance

---

#### `class PKDataProvider`

##### `get_stock_data(symbol: str, interval: str = "day", count: int = 100) -> pd.DataFrame`

Fetch stock data with automatic source selection.

**Parameters**:
- `symbol` (str): Stock symbol (e.g., "RELIANCE")
- `interval` (str): Candle interval ("1m", "5m", "15m", "30m", "60m", "day")
- `count` (int): Number of candles to fetch

**Returns**: `pd.DataFrame` with columns: Date, Open, High, Low, Close, Volume

**Example**:
```python
provider = get_data_provider()
df = provider.get_stock_data("RELIANCE", interval="5m", count=50)
```

---

##### `get_multiple_stocks(symbols: List[str], interval: str = "day") -> Dict[str, pd.DataFrame]`

Fetch data for multiple stocks.

**Parameters**:
- `symbols` (List[str]): List of stock symbols
- `interval` (str): Candle interval

**Returns**: Dict mapping symbol to DataFrame

---

##### `is_realtime_available() -> bool`

Check if real-time data source (PKBrokers) is available.

**Returns**: `True` if real-time data is accessible

---

##### `get_latest_price(symbol: str) -> float`

Get latest price for a symbol (real-time only).

**Parameters**:
- `symbol` (str): Stock symbol

**Returns**: Latest price or `None` if unavailable

---

##### `get_realtime_ohlcv(symbol: str, interval: str = "1m") -> Dict`

Get real-time OHLCV data.

**Returns**: Dict with keys: open, high, low, close, volume

---

### PKScalableDataFetcher

GitHub-based data fetcher without Telegram dependency.

```python
from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher, get_scalable_fetcher
```

#### `get_scalable_fetcher() -> PKScalableDataFetcher`

Factory function for singleton instance.

---

#### `class PKScalableDataFetcher`

##### `fetch_stock_data(symbol: str) -> pd.DataFrame`

Fetch stock data from GitHub raw content.

---

## Logging

### log module

Thread and process-safe logging framework.

```python
from PKDevTools.classes.log import (
    setup_custom_logger,
    default_logger,
    file_logger,
    log_to,
    tracelog,
    colors,
    suppress_stdout_stderr
)
```

#### `setup_custom_logger(name: str, levelname: int = logging.DEBUG, trace: bool = False, log_file_path: str = "PKDevTools-logs.txt", filter: str = None) -> filterlogger`

Set up and configure a custom logger.

**Parameters**:
- `name` (str): Logger name
- `levelname` (int): Logging level (10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR)
- `trace` (bool): Enable function tracing
- `log_file_path` (str): Path to log file
- `filter` (str): Only log messages containing this string

**Returns**: Configured `filterlogger` or `emptylogger` if logging disabled

**Example**:
```python
import os
os.environ["PKDevTools_Default_Log_Level"] = "10"

logger = setup_custom_logger(
    name="MyApp",
    levelname=10,
    log_file_path="./myapp.log",
    filter="IMPORTANT"
)
```

---

#### `default_logger() -> filterlogger | emptylogger`

Get the default logger instance.

**Returns**: `filterlogger` if `PKDevTools_Default_Log_Level` is set, else `emptylogger`

---

#### `file_logger() -> filterlogger | emptylogger`

Get the file logger for tracing.

---

#### `@log_to(logger_func: Callable)`

Decorator to log function calls with arguments and timing.

**Parameters**:
- `logger_func`: Function that accepts a string (e.g., `logger.info`)

**Example**:
```python
@log_to(default_logger().info)
def my_function(param1, param2):
    return param1 + param2
```

---

#### `class filterlogger`

Thread and process-safe logger implementation.

##### Properties

- `logger` -> `logging.Logger`: Underlying logger instance
- `level` -> `int`: Current logging level
- `isDebugging` -> `bool`: True if level is DEBUG

##### Methods

- `debug(message, exc_info=False)`: Log debug message
- `info(message)`: Log info message
- `warning(message)`: Log warning message
- `error(message)`: Log error with traceback (also sends to Telegram)
- `critical(message)`: Log critical message
- `flush()`: Flush all handlers
- `addHandlers(log_file_path, levelname)`: Add file and console handlers

---

#### `class emptylogger`

Null logger that performs no operations (used when logging disabled).

All methods are no-ops with same signature as `filterlogger`.

---

#### `class colors`

ANSI color codes for terminal formatting.

```python
print(colors.fg.red + "Red text" + colors.reset)
print(colors.bg.green + "Green background" + colors.reset)
print(colors.bold + "Bold text" + colors.reset)
```

**Foreground colors** (`colors.fg.*`): black, red, green, orange, blue, purple, cyan, lightgrey, darkgrey, lightred, lightgreen, yellow, lightblue, pink, lightcyan

**Background colors** (`colors.bg.*`): black, red, green, orange, blue, purple, cyan, lightgrey

**Formatting**: reset, bold, disable, underline, reverse, strikethrough, invisible

---

#### `class suppress_stdout_stderr`

Context manager for suppressing stdout and stderr.

```python
with suppress_stdout_stderr():
    noisy_function()  # Output suppressed
```

---

## Database

### DBManager

Database management with SQLite and Turso (libsql).

```python
from PKDevTools.classes.DBManager import (
    DBManager,
    PKUser,
    PKScannerJob,
    PKUserModel
)
```

#### `class DBManager`

##### `__init__(localDatabase: str = "pkscreener.db")`

Initialize database manager.

**Parameters**:
- `localDatabase` (str): Path to local SQLite database

---

##### `getUserByID(userID: int) -> List[PKUser]`

Get user by Telegram ID.

**Returns**: List of matching `PKUser` objects

---

##### `getOTP(userID: int, userName: str, fullName: str, validityIntervalInSeconds: int = 60) -> Tuple[int, str, str, PKUser]`

Generate OTP for user authentication.

**Parameters**:
- `userID`: Telegram user ID
- `userName`: Telegram username
- `fullName`: User's full name
- `validityIntervalInSeconds`: OTP validity period

**Returns**: Tuple of (otp_value, subscription_model, validity, user)

---

##### `subscribeScannerForUser(userID: int, scannerIDs: str) -> bool`

Subscribe user to scanner job alerts.

**Parameters**:
- `userID`: User's Telegram ID
- `scannerIDs`: Comma-separated scanner IDs (e.g., "X:12:9,X:12:31")

---

##### `getSubscribedScannersByUser(userID: int) -> List[str]`

Get list of scanner IDs user is subscribed to.

---

##### `unsubscribeScannerForUser(userID: int, scannerIDs: str) -> bool`

Unsubscribe user from scanner alerts.

---

#### `class PKUser`

User model with subscription management.

**Attributes**:
- `id` (int): Telegram user ID
- `username` (str): Telegram username
- `name` (str): Full name
- `email` (str): Email address
- `mobile` (str): Mobile number
- `subscriptionModel` (str): Subscription type
- `balance` (float): Account balance
- `scannerJobs` (List[str]): Subscribed scanner IDs

---

#### `class PKScannerJob`

Scanner job subscription model.

**Attributes**:
- `scannerId` (str): Unique scanner identifier
- `userIds` (List[str]): List of subscribed user IDs

---

### DatabaseSyncChecker

Check synchronization between local and remote databases.

```python
from PKDevTools.classes.DatabaseSyncChecker import DatabaseSyncChecker

checker = DatabaseSyncChecker(
    local_db_path="./local.db",
    turso_url="libsql://db.turso.io",
    turso_auth_token="token"
)

needs_sync, messages = checker.check_sync_status()
```

---

## Environment

### PKEnvironment

Centralized configuration from `.env.dev`.

```python
from PKDevTools.classes.Environment import PKEnvironment

env = PKEnvironment()  # Singleton
```

#### Properties

- `GITHUB_TOKEN` (str): GitHub API token
- `TOKEN` (str): Telegram bot token
- `CHAT_ID` (str): Default Telegram chat ID
- `chat_idADMIN` (str): Admin chat ID
- `secrets` (tuple): Legacy tuple of main secrets
- `allSecrets` (dict): All secrets as dictionary

#### Dynamic Attributes

All keys from `.env.dev` are accessible as attributes:

```python
env = PKEnvironment()
print(env.MY_CUSTOM_KEY)  # Access any key from .env.dev
```

---

## HTTP Client

### fetcher

HTTP client with caching support.

```python
from PKDevTools.classes.Fetcher import fetcher, StockDataEmptyException
```

#### `class fetcher`

##### `__init__(configManager=None)`

Initialize fetcher with optional config.

---

##### `fetchURL(url: str, headers: dict = None, stream: bool = False, timeout: int = None) -> requests.Response`

Fetch URL with caching.

**Parameters**:
- `url`: URL to fetch
- `headers`: Optional HTTP headers
- `stream`: Enable streaming response
- `timeout`: Request timeout

**Returns**: `requests.Response` object

---

##### `postURL(url: str, data: dict = None, headers: dict = None) -> requests.Response`

POST request to URL.

---

#### `class StockDataEmptyException(Exception)`

Exception raised when stock data is empty (delisted stock).

---

## Telegram

### Telegram module

Send messages and files to Telegram.

```python
from PKDevTools.classes.Telegram import (
    send_message,
    send_document,
    send_photo,
    send_media_group,
    is_token_valid
)
```

#### `send_message(message: str, userID: str, parse_type: str = "HTML", list_png: List = None, retrial: int = 0) -> bool`

Send text message to Telegram.

**Parameters**:
- `message`: Message text (supports HTML formatting)
- `userID`: Target chat/channel ID
- `parse_type`: Parse mode ("HTML" or "Markdown")
- `list_png`: Optional list of images to attach
- `retrial`: Retry count (internal)

**Returns**: `True` if successful

**Example**:
```python
send_message(
    message="<b>Alert!</b> Stock crossed target",
    userID="-1001234567890",
    parse_type="HTML"
)
```

---

#### `send_document(file_path: str, message: str, userID: str, retrial: int = 0) -> bool`

Send document file.

**Parameters**:
- `file_path`: Path to file
- `message`: Caption text
- `userID`: Target chat ID

---

#### `send_photo(photo_path: str, caption: str, userID: str) -> bool`

Send photo with caption.

---

#### `send_media_group(file_paths: List[str], message: str, userID: str) -> bool`

Send multiple files as media group.

**Parameters**:
- `file_paths`: List of file paths
- `message`: Caption for first file
- `userID`: Target chat ID

---

#### `is_token_valid() -> bool`

Check if Telegram bot token is valid.

---

## GitHub Integration

### Committer

Git operations and file management.

```python
from PKDevTools.classes.Committer import Committer
```

#### Static Methods

##### `copySourceToDestination(srcPath: str, destPath: str, showStatus: bool = False) -> bool`

Copy files from source to destination.

---

##### `commitTempOutcomes(addPath: str, commitMessage: str, branchName: str = "gh-pages", showStatus: bool = False, timeout: int = 300)`

Commit and push changes to remote.

**Parameters**:
- `addPath`: Files to add (glob pattern)
- `commitMessage`: Commit message
- `branchName`: Target branch
- `showStatus`: Show git status output
- `timeout`: Command timeout

**Example**:
```python
Committer.commitTempOutcomes(
    addPath="results/*",
    commitMessage="[Auto] Updated scan results",
    branchName="main"
)
```

---

##### `execOSCommand(command: str, showStatus: bool = False, timeout: int = 300) -> str`

Execute shell command with logging.

**Returns**: Command output

---

### WorkflowManager

GitHub Actions workflow management.

```python
from PKDevTools.classes.WorkflowManager import WorkflowManager
```

#### Methods

##### `trigger_workflow(repo: str, workflow_id: str, ref: str = "main", inputs: dict = None)`

Trigger a GitHub Actions workflow.

**Parameters**:
- `repo`: Repository (e.g., "owner/repo")
- `workflow_id`: Workflow filename (e.g., "scan.yml")
- `ref`: Branch or tag reference
- `inputs`: Workflow input parameters

---

### githubutilities

GitHub API utilities.

```python
from PKDevTools.classes.githubutilities import (
    getWorkflowRunByName,
    stopWorkflow,
    getLatestRelease,
    getAssetFromRelease
)
```

---

## Multiprocessing

### PKMultiProcessorClient

Cross-platform multiprocessing worker.

```python
from PKDevTools.classes.PKMultiProcessorClient import PKMultiProcessorClient
```

#### `class PKMultiProcessorClient(multiprocessing.Process)`

##### `__init__(processorMethod, task_queue, result_queue, ...)`

Initialize worker process.

**Key Parameters**:
- `processorMethod`: Function to call for each task
- `task_queue`: Queue for incoming tasks
- `result_queue`: Queue for results
- `objectDictionaryPrimary`: Shared dict for primary data
- `objectDictionarySecondary`: Shared dict for secondary data
- `keyboardInterruptEvent`: Event for graceful shutdown

---

### PKJoinableQueue

Enhanced multiprocessing queue.

```python
from PKDevTools.classes.PKJoinableQueue import PKJoinableQueue

queue = PKJoinableQueue()
queue.put("task")
# Worker calls queue.task_done() after processing
queue.join()  # Wait for all tasks
```

---

## Events (Pub/Sub)

### Events Module

Decoupled event system using blinker.

```python
from PKDevTools.classes.pubsub.events import globalEventsSignal
from PKDevTools.classes.pubsub.publisher import PKUserService
```

#### `globalEventsSignal`

Global blinker Signal for event pub/sub.

##### Publishing

```python
globalEventsSignal.send(
    sender=self,
    eventType="my_event",
    data={"key": "value"}
)
```

##### Subscribing

```python
def my_handler(sender, **kwargs):
    event_type = kwargs.get('eventType')
    data = kwargs.get('data')
    # Handle event

globalEventsSignal.connect(my_handler)
```

---

#### `class PKUserService`

User notification service.

##### `notify_user(scannerID: str, notification: str)`

Publish user notification event.

##### `send_event(event_name: str, event_params: dict)`

Send custom analytics event.

---

## Utilities

### Archiver

File caching and management.

```python
from PKDevTools.classes import Archiver
```

#### Functions

##### `get_user_data_dir() -> str`

Get user data directory path.

##### `get_user_outputs_dir() -> str`

Get user outputs directory path.

##### `resolveFilePath(fileName: str) -> str`

Resolve file path in temp directory.

##### `cacheFile(bData: bytes, fileName: str)`

Cache binary data to file.

##### `findFile(fileName: str) -> Tuple[bytes, str, datetime]`

Find cached file.

**Returns**: Tuple of (data, path, modified_time)

##### `get_last_modified_datetime(file_path: str) -> datetime`

Get file's last modified time.

---

### PKDateUtilities

Date and time utilities for market operations.

```python
from PKDevTools.classes.PKDateUtilities import PKDateUtilities
```

#### Static Methods

##### `isTradingTime() -> bool`

Check if market is currently open.

##### `isTradingHoliday() -> bool`

Check if today is a trading holiday.

##### `currentDateTime() -> datetime`

Get current datetime in IST.

##### `tradingDate() -> date`

Get current trading date (handles weekends/holidays).

---

### PKTimer

Execution timing context manager.

```python
from PKDevTools.classes.PKTimer import PKTimer

with PKTimer("Operation"):
    perform_operation()
# Output: "Operation completed in 1.234 seconds"
```

---

### ColorText

Terminal color formatting.

```python
from PKDevTools.classes.ColorText import colorText

print(colorText.GREEN + "Success" + colorText.END)
print(colorText.FAIL + "Error" + colorText.END)
print(colorText.WARN + "Warning" + colorText.END)
print(colorText.BOLD + "Bold" + colorText.END)
```

**Available Colors**: GREEN, FAIL, WARN, BOLD, END, etc.

---

### FunctionTimeouts

Function timeout decorator.

```python
from PKDevTools.classes.FunctionTimeouts import exit_after

@exit_after(5)  # Timeout after 5 seconds
def slow_function():
    # Long running operation
    pass
```

---

### OutputControls

Terminal output control utilities.

```python
from PKDevTools.classes.OutputControls import OutputControls

# Control output visibility
OutputControls.setRedirectOutput(True)  # Suppress output
OutputControls.setRedirectOutput(False)  # Enable output
```

---

### SuppressOutput

Context manager for output suppression.

```python
from PKDevTools.classes.SuppressOutput import SuppressOutput

with SuppressOutput(suppress=True):
    noisy_function()
```

---

## Error Codes

| Exception | Description |
|-----------|-------------|
| `StockDataEmptyException` | Stock is delisted or has no data |
| `AttributeError` | Invalid environment variable access |
| `sqlite3.Error` | Database operation failed |
| `GithubException` | GitHub API error |

---

## Constants

### Logging Levels

```python
import logging

logging.DEBUG     # 10
logging.INFO      # 20
logging.WARNING   # 30
logging.ERROR     # 40
logging.CRITICAL  # 50
```

### Message Limits

```python
MAX_MSG_LENGTH = 4096      # Telegram message limit
MAX_CAPTION_LENGTH = 1024  # Telegram caption limit
```

---

For more details, see the [source code](https://github.com/pkjmesra/PKDevTools) or [Architecture documentation](ARCHITECTURE.md).







