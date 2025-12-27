
# PKDevTools

[![MADE-IN-INDIA][MADE-IN-INDIA-badge]][MADE-IN-INDIA] [![GitHub release (latest by date)][GitHub release (latest by date)-badge]][GitHub release (latest by date)] [![GitHub all releases][GitHub all releases]](#) [![GitHub][License-badge]][License] [![CodeFactor][Codefactor-badge]][Codefactor] [![BADGE][PR-Guidelines-badge]][PR-Guidelines]

![github license][github-license] [![Downloads][Downloads-badge]][Downloads]
![latest download][Latest-Downloads-badge] [![PyPI][pypi-badge]][pypi] [![is wheel][wheel-badge]][pypi] [![Coverage Status][Coverage-Status-badge]][Coverage-Status] [![codecov][codecov-badge]][codecov]

[![Documentation][Documentation-badge]][Documentation] 
 [![PKDevTools Test - New Features][New Features-badge]][New Features] [![1. PKDevTools Build - New Release][New Release-badge]][New Release]

---

## Table of Contents

- [What is PKDevTools?](#what-is-pkdevtools)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture Overview](#architecture-overview)
- [Core Modules](#core-modules)
  - [Data Provider System](#1-data-provider-system)
  - [Logging Framework](#2-logging-framework)
  - [Database Management](#3-database-management)
  - [Environment & Configuration](#4-environment--configuration)
  - [Multiprocessing](#5-multiprocessing)
  - [Telegram Integration](#6-telegram-integration)
  - [GitHub Integration](#7-github-integration)
  - [Pub/Sub Event System](#8-pubsub-event-system)
  - [Utilities](#9-utilities)
- [API Reference](#api-reference)
- [Environment Variables](#environment-variables)
- [Contributing](#contributing)
- [License](#license)

---

## What is PKDevTools?

**PKDevTools** is a comprehensive Python toolkit designed for building high-performance financial applications. It provides:

- 🚀 **Unified Data Provider** - Multi-source stock data with automatic failover
- 📝 **Thread-Safe Logging** - Process-safe logging with filtering and caller info
- 🗄️ **Database Management** - SQLite + Turso (libsql) with sync capabilities
- ⚡ **Multiprocessing** - Cross-platform multiprocessing with shared state
- 📱 **Telegram Integration** - Send messages, documents, and media
- 🔄 **GitHub Automation** - Workflow triggers, commits, and API integration
- 📡 **Event System** - Pub/Sub pattern for decoupled components
- 🛠️ **Utilities** - Caching, archiving, HTTP fetching, and more

This toolkit serves as the foundation for [PKScreener](https://github.com/pkjmesra/PKScreener), [PKBrokers](https://github.com/pkjmesra/PKBrokers), and [PKNSETools](https://github.com/pkjmesra/PKNSETools).

---

## Installation

### From PyPI (Recommended)

```bash
pip install PKDevTools
```

### From Source

```bash
git clone https://github.com/pkjmesra/PKDevTools.git
cd PKDevTools
pip install -r requirements.txt
pip install -e .
```

### Requirements

- Python 3.9+
- See `requirements.txt` for full dependency list

---

## Quick Start

```python
from PKDevTools.classes import get_data_provider, get_scalable_fetcher
from PKDevTools.classes.log import default_logger, setup_custom_logger

# Initialize logging (set environment variable first)
import os
os.environ["PKDevTools_Default_Log_Level"] = "10"  # DEBUG level

# Get stock data
provider = get_data_provider()
df = provider.get_stock_data("RELIANCE", interval="day", count=100)

# Use the logger
logger = default_logger()
logger.info("Data fetched successfully!")
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PKDevTools Architecture                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐       │
│  │  PKDataProvider  │  │ PKScalableData   │  │  DBManager       │       │
│  │  (Stock Data)    │  │ Fetcher (GitHub) │  │  (Turso/SQLite)  │       │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘       │
│           │                     │                     │                 │
│           └─────────────────────┼─────────────────────┘                 │
│                                 │                                       │
│                    ┌────────────▼────────────┐                          │
│                    │     Core Services       │                          │
│                    ├─────────────────────────┤                          │
│                    │ • Logging (filterlogger)│                          │
│                    │ • Environment Config    │                          │
│                    │ • HTTP Fetcher          │                          │
│                    │ • Archiver (Caching)    │                          │
│                    └────────────┬────────────┘                          │
│                                 │                                       │
│           ┌─────────────────────┼─────────────────────┐                 │
│           │                     │                     │                 │
│  ┌────────▼─────────┐  ┌────────▼───────┐  ┌──────────▼───────┐         │
│  │   Telegram       │  │  GitHub        │  │  Pub/Sub Events  │         │
│  │   Integration    │  │  Integration   │  │  (blinker)       │         │
│  └──────────────────┘  └────────────────┘  └──────────────────┘         │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │                    Multiprocessing Layer                     │       │
│  │  PKMultiProcessorClient | PKJoinableQueue | Process Logging  │       │
│  └──────────────────────────────────────────────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```
See Also: 
    1. [Architecture](https://github.com/pkjmesra/PKDevTools/blob/main/docs/ARCHITECTURE.md)
    2. [API Reference](https://github.com/pkjmesra/PKDevTools/blob/main/docs/API_REFERENCE.md)

---

## Core Modules

### 1. Data Provider System

The unified data provider fetches stock OHLCV data from multiple sources with automatic failover.

#### PKDataProvider

```python
from PKDevTools.classes.PKDataProvider import PKDataProvider, get_data_provider

# Get singleton instance
provider = get_data_provider()

# Fetch stock data with automatic source selection
# Priority: Real-time (PKBrokers) → Local Pickle → Remote GitHub Pickle
df = provider.get_stock_data("RELIANCE", interval="5m", count=50)

# Fetch multiple stocks
data = provider.get_multiple_stocks(["RELIANCE", "TCS", "INFY"], interval="day")

# Check real-time availability
if provider.is_realtime_available():
    price = provider.get_latest_price("INFY")
    ohlcv = provider.get_realtime_ohlcv("INFY")
```

**Supported Intervals:**
| Interval | Description |
|----------|-------------|
| `1m`, `2m`, `3m`, `4m`, `5m` | Minute candles |
| `10m`, `15m`, `30m`, `60m` | Extended minute candles |
| `day` | Daily candles |

#### PKScalableDataFetcher

GitHub-based data fetcher without Telegram dependency:

```python
from PKDevTools.classes.PKScalableDataFetcher import PKScalableDataFetcher, get_scalable_fetcher

fetcher = get_scalable_fetcher()

# Fetch from GitHub raw content
data = fetcher.fetch_stock_data("RELIANCE")
```

---

### 2. Logging Framework

Thread and process-safe logging with automatic caller information injection.

#### Setup and Usage

```python
import os
from PKDevTools.classes.log import (
    setup_custom_logger,
    default_logger,
    log_to,
    tracelog
)

# Enable logging via environment variable
os.environ["PKDevTools_Default_Log_Level"] = "10"  # DEBUG=10, INFO=20, WARNING=30, ERROR=40

# Setup custom logger
logger = setup_custom_logger(
    name="MyApp",
    levelname=10,  # DEBUG
    log_file_path="/path/to/logs.txt",
    filter="IMPORTANT"  # Only log messages containing "IMPORTANT"
)

# Use default logger
logger = default_logger()
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")  # Automatically includes traceback
logger.critical("Critical message")
```

#### Decorator for Function Tracing

```python
from PKDevTools.classes.log import log_to, default_logger

@log_to(default_logger().info)
def my_function(param1, param2):
    """Function calls are automatically logged with arguments and timing"""
    return param1 + param2
```

#### Log Levels

| Level | Value | Description |
|-------|-------|-------------|
| DEBUG | 10 | Detailed diagnostic information |
| INFO | 20 | General operational messages |
| WARNING | 30 | Warning messages |
| ERROR | 40 | Error messages with traceback |
| CRITICAL | 50 | Critical failures |

#### Key Classes

- **`filterlogger`**: Thread/process-safe logger with filtering
- **`emptylogger`**: No-op logger when logging is disabled
- **`colors`**: ANSI color codes for terminal formatting

---

### 3. Database Management

Dual database support with SQLite (local) and Turso/libsql (cloud).

#### DBManager

```python
from PKDevTools.classes.DBManager import DBManager, PKUser

# Initialize manager (uses environment variables for Turso connection)
db = DBManager()

# User operations
user = db.getUserByID(12345)
otp, subscription_model, validity, user = db.getOTP(
    userID=12345,
    userName="john_doe",
    fullName="John Doe"
)

# Scanner job subscriptions
db.subscribeScannerForUser(userID=12345, scannerIDs="X:12:9,X:12:31")
subscriptions = db.getSubscribedScannersByUser(userID=12345)
```

#### DatabaseSyncChecker

```python
from PKDevTools.classes.DatabaseSyncChecker import DatabaseSyncChecker

checker = DatabaseSyncChecker(
    local_db_path="./local.db",
    turso_url="libsql://your-db.turso.io",
    turso_auth_token="your-token"
)

needs_sync, messages = checker.check_sync_status()
checker.print_counts()
```

#### Key Models

- **`PKUser`**: User model with subscription management
- **`PKScannerJob`**: Scanner job subscription model
- **`PKUserModel`**: Enum for database column mapping

---

### 4. Environment & Configuration

Centralized environment variable and secrets management.

#### PKEnvironment

```python
from PKDevTools.classes.Environment import PKEnvironment

# Singleton instance - loads from .env.dev file
env = PKEnvironment()

# Access secrets as attributes
github_token = env.GITHUB_TOKEN
chat_id = env.CHAT_ID
telegram_token = env.TOKEN

# Access all secrets
all_secrets = env.allSecrets  # Returns dict
```

#### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub API token for repository operations |
| `CHAT_ID` | Telegram channel/chat ID |
| `TOKEN` | Telegram bot token |
| `chat_idADMIN` | Admin chat ID for notifications |
| `PKDevTools_Default_Log_Level` | Logging level (10=DEBUG, 20=INFO, etc.) |

---

### 5. Multiprocessing

Cross-platform multiprocessing with shared state and logging support.

#### PKMultiProcessorClient

```python
from PKDevTools.classes.PKMultiProcessorClient import PKMultiProcessorClient
from PKDevTools.classes.PKJoinableQueue import PKJoinableQueue
from multiprocessing import Manager

# Create shared resources
manager = Manager()
task_queue = PKJoinableQueue()
result_queue = PKJoinableQueue()

# Define processor method
def process_task(stock_code, data_dict, result_dict):
    # Process stock data
    result = analyze_stock(stock_code)
    return result

# Create worker processes
workers = []
for i in range(4):  # 4 worker processes
    worker = PKMultiProcessorClient(
        processorMethod=process_task,
        task_queue=task_queue,
        result_queue=result_queue,
        objectDictionaryPrimary=manager.dict(),
        keyboardInterruptEvent=manager.Event()
    )
    worker.start()
    workers.append(worker)

# Add tasks
for stock in ["RELIANCE", "TCS", "INFY"]:
    task_queue.put(stock)

# Signal completion and wait
task_queue.join()
```

#### PKJoinableQueue

Enhanced multiprocessing queue with join support:

```python
from PKDevTools.classes.PKJoinableQueue import PKJoinableQueue

queue = PKJoinableQueue()
queue.put("task1")
queue.put("task2")

# Worker processes call task_done() after processing
queue.join()  # Blocks until all tasks completed
```

---

### 6. Telegram Integration

Send messages, documents, and media to Telegram.

#### Basic Usage

```python
from PKDevTools.classes.Telegram import (
    send_message,
    send_document,
    send_photo,
    send_media_group
)

# Send text message
send_message(
    message="Hello from PKDevTools!",
    userID="-1001234567890",
    parse_type="HTML"
)

# Send document
send_document(
    file_path="/path/to/file.pdf",
    message="Here's your report",
    userID="-1001234567890"
)

# Send photo
send_photo(
    photo_path="/path/to/image.png",
    caption="Analysis results",
    userID="-1001234567890"
)

# Send multiple documents as media group
send_media_group(
    file_paths=["/path/to/file1.pdf", "/path/to/file2.pdf"],
    message="Multiple reports",
    userID="-1001234567890"
)
```

#### Message Formatting

Messages support HTML formatting:

```python
send_message(
    message="<b>Bold</b> <i>Italic</i> <code>Code</code>",
    userID=chat_id,
    parse_type="HTML"
)
```

---

### 7. GitHub Integration

Automate GitHub operations including commits, workflow triggers, and API calls.

#### Committer

```python
from PKDevTools.classes.Committer import Committer

# Copy files
Committer.copySourceToDestination(
    srcPath="results/*.pkl",
    destPath="backup/"
)

# Commit and push changes
Committer.commitTempOutcomes(
    addPath="results/*",
    commitMessage="[Auto] Updated results",
    branchName="main"
)

# Execute OS command with logging
Committer.execOSCommand("git status", showStatus=True)
```

#### WorkflowManager

```python
from PKDevTools.classes.WorkflowManager import WorkflowManager

# Trigger GitHub Actions workflow
WorkflowManager.trigger_workflow(
    repo="pkjmesra/PKScreener",
    workflow_id="scan.yml",
    ref="main",
    inputs={"scan_type": "full"}
)
```

#### githubutilities

```python
from PKDevTools.classes.githubutilities import (
    getWorkflowRunByName,
    stopWorkflow,
    getLatestRelease
)

# Get latest release
release = getLatestRelease("pkjmesra/PKScreener")

# Get workflow run
run = getWorkflowRunByName("pkjmesra/PKScreener", "Build")
```

---

### 8. Pub/Sub Event System

Decoupled event publishing and subscription using blinker.

#### Publishing Events

```python
from PKDevTools.classes.pubsub.publisher import PKUserService
from PKDevTools.classes.pubsub.events import globalEventsSignal

# Using PKUserService
service = PKUserService()
service.notify_user(scannerID="X:12:9", notification="Scan complete!")

# Direct signal publishing
globalEventsSignal.send(
    sender=self,
    eventType="custom",
    data={"key": "value"}
)
```

#### Subscribing to Events

```python
from PKDevTools.classes.pubsub.events import globalEventsSignal

def my_handler(sender, **kwargs):
    scanner_id = kwargs.get('scannerID')
    notification = kwargs.get('notification')
    print(f"Received: {scanner_id} - {notification}")

# Subscribe to events
globalEventsSignal.connect(my_handler)
```

---

### 9. Utilities

#### Archiver (Caching & File Management)

```python
from PKDevTools.classes import Archiver

# Get user data directory
data_dir = Archiver.get_user_data_dir()

# Get user outputs directory
outputs_dir = Archiver.get_user_outputs_dir()

# Cache binary data
Archiver.cacheFile(binary_data, "cache_file.bin")

# Find cached file
data, path, modified_time = Archiver.findFile("cache_file.bin")

# Get last modified datetime
modified = Archiver.get_last_modified_datetime("/path/to/file")
```

#### Fetcher (HTTP Requests)

```python
from PKDevTools.classes.Fetcher import fetcher

f = fetcher()

# Fetch URL with caching
response = f.fetchURL("https://api.example.com/data")

# Fetch with custom headers
response = f.fetchURL(
    url="https://api.example.com/data",
    headers={"Authorization": "Bearer token"}
)
```

#### PKDateUtilities

```python
from PKDevTools.classes.PKDateUtilities import PKDateUtilities

# Check if market is open
is_open = PKDateUtilities.isTradingTime()

# Check if today is a holiday
is_holiday = PKDateUtilities.isTradingHoliday()

# Get current IST time
ist_now = PKDateUtilities.currentDateTime()

# Get trading day offset
trading_date = PKDateUtilities.tradingDate()
```

#### PKTimer

```python
from PKDevTools.classes.PKTimer import PKTimer

# Measure execution time
with PKTimer("Operation name"):
    # Code to measure
    perform_operation()
```

#### ColorText

```python
from PKDevTools.classes.ColorText import colorText

# Print colored text
print(colorText.GREEN + "Success!" + colorText.END)
print(colorText.FAIL + "Error!" + colorText.END)
print(colorText.WARN + "Warning!" + colorText.END)
```

#### FunctionTimeouts

```python
from PKDevTools.classes.FunctionTimeouts import exit_after

@exit_after(5)  # Timeout after 5 seconds
def slow_function():
    # Long running operation
    pass
```

---

## API Reference

### Main Exports

```python
from PKDevTools.classes import (
    # Data Providers
    PKDataProvider,
    get_data_provider,
    PKScalableDataFetcher,
    get_scalable_fetcher,
    
    # Version
    VERSION,
)
```

### Module Structure

```
PKDevTools/
├── classes/
│   ├── __init__.py              # Main exports
│   ├── PKDataProvider.py        # Unified data provider
│   ├── PKScalableDataFetcher.py # GitHub-based fetcher
│   ├── log.py                   # Logging framework
│   ├── DBManager.py             # Database management
│   ├── Environment.py           # Environment/secrets
│   ├── Fetcher.py               # HTTP client
│   ├── Telegram.py              # Telegram integration
│   ├── Committer.py             # Git operations
│   ├── WorkflowManager.py       # GitHub Actions
│   ├── PKMultiProcessorClient.py # Multiprocessing
│   ├── PKJoinableQueue.py       # Enhanced queue
│   ├── Archiver.py              # Caching/files
│   ├── PKDateUtilities.py       # Date/time utilities
│   ├── pubsub/                  # Event system
│   │   ├── events.py            # Signal definitions
│   │   ├── publisher.py         # Event publishing
│   │   └── subscriber.py        # Event handling
│   └── ...                      # Other utilities
└── release.md                   # Release notes
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PKDevTools_Default_Log_Level` | No | Logging level (10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR) |
| `GITHUB_TOKEN` | Yes* | GitHub API token |
| `TOKEN` | Yes* | Telegram bot token |
| `CHAT_ID` | Yes* | Default Telegram chat ID |
| `chat_idADMIN` | No | Admin notification chat ID |
| `TURSO_DB_URL` | No | Turso database URL |
| `TURSO_DB_AUTH_TOKEN` | No | Turso authentication token |

*Required for respective functionality

---

## Contributing

We welcome contributions! Please follow these guidelines:

### Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/PKDevTools.git
   cd PKDevTools
   ```
3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   ```
4. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

### Running Tests

```bash
# Run all tests
pytest test/

# Run with coverage
pytest --cov=PKDevTools test/

# Run specific test file
pytest test/DBManager_test.py
```

### Code Style

We use `ruff` for linting:

```bash
ruff check PKDevTools/
ruff format PKDevTools/
```

### Pull Request Guidelines

1. Create a feature branch from `main`
2. Write tests for new functionality
3. Ensure all tests pass
4. Update documentation as needed
5. Submit a pull request with a clear description

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Related Projects

- [PKScreener](https://github.com/pkjmesra/PKScreener) - Stock screening application
- [PKBrokers](https://github.com/pkjmesra/PKBrokers) - Broker integration and real-time data
- [PKNSETools](https://github.com/pkjmesra/PKNSETools) - NSE market data tools

---

## Support

- 📖 [Documentation](https://PKDevTools.readthedocs.io/)
- 🐛 [Issue Tracker](https://github.com/pkjmesra/PKDevTools/issues)
- 💬 [Discussions](https://github.com/pkjmesra/PKDevTools/discussions)

---

[MADE-IN-INDIA-badge]:https://img.shields.io/badge/MADE%20WITH%20%E2%9D%A4%20IN-INDIA-orange?style=for-the-badge
[MADE-IN-INDIA]:https://en.wikipedia.org/wiki/India
[GitHub release (latest by date)-badge]:https://img.shields.io/github/v/release/pkjmesra/PKDevTools?style=for-the-badge
[GitHub release (latest by date)]:https://github.com/pkjmesra/PKTools/releases/latest
[pypi-badge]: https://img.shields.io/pypi/v/PKDevTools.svg?style=flat-square
[pypi]: https://pypi.python.org/pypi/PKDevTools
[coveralls]: https://coveralls.io/github/pkjmesra/PKDevTools?branch=main
[cover-badge]: https://coveralls.io/repos/github/pkjmesra/PKTools/badge.svg?branch=main
[wheel-badge]: https://img.shields.io/pypi/wheel/PKDevTools.svg?style=flat-square
[GitHub all releases]: https://img.shields.io/github/downloads/pkjmesra/PKTools/total?color=Green&label=Downloads&style=for-the-badge
[License-badge]: https://img.shields.io/github/license/pkjmesra/PKDevTools?style=for-the-badge
[License]: https://github.com/pkjmesra/PKTools/blob/main/LICENSE
[Codefactor-badge]: https://www.codefactor.io/repository/github/pkjmesra/PKTools/badge?style=for-the-badge
[Codefactor]: https://www.codefactor.io/repository/github/pkjmesra/PKDevTools
[PR-Guidelines-badge]: https://img.shields.io/badge/PULL%20REQUEST-GUIDELINES-red?style=for-the-badge
[PR-Guidelines]: https://github.com/pkjmesra/PKTools/blob/new-features/CONTRIBUTING.md
[github-license]: https://img.shields.io/pypi/l/gspread?logo=github
[Downloads-badge]: https://static.pepy.tech/personalized-badge/PKDevTools?period=total&units=international_system&left_color=black&right_color=brightgreen&left_text=PyPi%20Downloads
[Downloads]: https://pepy.tech/project/PKDevTools
[Latest-Downloads-badge]: https://img.shields.io/github/downloads-pre/pkjmesra/PKTools/latest/total?logo=github
[Coverage-Status-badge]: https://coveralls.io/repos/github/pkjmesra/PKTools/badge.svg?branch=main
[Coverage-Status]: https://coveralls.io/github/pkjmesra/PKDevTools?branch=main
[codecov-badge]: https://codecov.io/gh/pkjmesra/PKTools/branch/main/graph/badge.svg
[codecov]: https://codecov.io/gh/pkjmesra/PKDevTools
[Documentation-badge]: https://readthedocs.org/projects/PKDevTools/badge/?version=latest
[Documentation]: https://PKDevTools.readthedocs.io/en/latest/?badge=latest
[New Features-badge]: https://github.com/pkjmesra/PKTools/actions/workflows/w10-workflow-features-test.yml/badge.svg?branch=new-features
[New Features]: https://github.com/pkjmesra/PKTools/actions/workflows/w10-workflow-features-test.yml
[New Release-badge]: https://github.com/pkjmesra/PKTools/actions/workflows/w1-workflow-build-matrix.yml/badge.svg
[New Release]: https://github.com/pkjmesra/PKTools/actions/workflows/w1-workflow-build-matrix.yml
