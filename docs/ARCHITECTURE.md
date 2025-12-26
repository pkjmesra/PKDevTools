# PKDevTools Architecture

This document provides a detailed technical overview of PKDevTools architecture for developers who want to contribute or integrate with the toolkit.

## Table of Contents

1. [System Overview](#system-overview)
2. [Layer Architecture](#layer-architecture)
3. [Data Flow](#data-flow)
4. [Component Details](#component-details)
5. [Design Patterns](#design-patterns)
6. [Extension Points](#extension-points)
7. [Thread Safety](#thread-safety)
8. [Error Handling](#error-handling)

---

## System Overview

PKDevTools is designed as a modular toolkit with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Application Layer                               │
│                    (PKScreener, PKBrokers, PKNSETools)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                              PKDevTools API Layer                            │
│          PKDataProvider | DBManager | Telegram | GitHub Integration          │
├─────────────────────────────────────────────────────────────────────────────┤
│                              Core Services Layer                             │
│      Logging | Environment | Fetcher | Archiver | DateUtilities              │
├─────────────────────────────────────────────────────────────────────────────┤
│                           Infrastructure Layer                               │
│     Multiprocessing | Pub/Sub Events | Singleton | Output Controls           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Layer Architecture

### 1. Application Layer (External)

Applications built on PKDevTools:
- **PKScreener**: Stock screening and analysis
- **PKBrokers**: Broker integrations and real-time data
- **PKNSETools**: NSE-specific market data tools

### 2. API Layer

High-level APIs for common operations:

| Component | Responsibility |
|-----------|----------------|
| `PKDataProvider` | Unified stock data access |
| `PKScalableDataFetcher` | GitHub-based data fetching |
| `DBManager` | Database operations |
| `Telegram` | Messaging integration |
| `Committer` | Git operations |
| `WorkflowManager` | GitHub Actions automation |

### 3. Core Services Layer

Foundational services used across the toolkit:

| Service | Responsibility |
|---------|----------------|
| `filterlogger` | Thread-safe logging |
| `PKEnvironment` | Configuration management |
| `fetcher` | HTTP requests with caching |
| `Archiver` | File caching and management |
| `PKDateUtilities` | Date/time utilities |

### 4. Infrastructure Layer

Low-level utilities and patterns:

| Component | Responsibility |
|-----------|----------------|
| `PKMultiProcessorClient` | Cross-platform multiprocessing |
| `PKJoinableQueue` | Enhanced multiprocessing queue |
| `globalEventsSignal` | Pub/Sub event system |
| `SingletonType` | Metaclass for singletons |

---

## Data Flow

### Stock Data Flow

```
┌─────────────────┐
│ Application     │
│ requests data   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ PKDataProvider  │ ─── Priority-based source selection
└────────┬────────┘
         │
    ┌────┴────┬──────────────┐
    ▼         ▼              ▼
┌───────┐ ┌───────┐   ┌────────────┐
│Real-  │ │Local  │   │Remote      │
│time   │ │Pickle │   │GitHub      │
│(PKB)  │ │Cache  │   │Pickle      │
└───────┘ └───────┘   └────────────┘
    │         │              │
    └────┬────┴──────────────┘
         │
         ▼
┌─────────────────┐
│ Merged DataFrame│
│ returned to app │
└─────────────────┘
```

### Logging Flow

```
┌─────────────────┐
│ Application     │
│ logs message    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Check env var   │────▶│ PKDevTools_     │
│                 │     │ Default_Log_    │
└────────┬────────┘     │ Level set?      │
         │              └────────┬────────┘
    ┌────┴────┐                  │
    │         │           ┌──────┴──────┐
    ▼         ▼           ▼             ▼
┌───────┐ ┌───────┐   ┌───────┐   ┌───────┐
│empty  │ │filter │   │ YES   │   │  NO   │
│logger │ │logger │   └───┬───┘   └───┬───┘
│(no-op)│ │(logs) │       │           │
└───────┘ └───┬───┘       │           │
              │           ▼           ▼
              │     ┌───────┐   ┌───────┐
              └────▶│Process│   │Discard│
                    │message│   │message│
                    └───┬───┘   └───────┘
                        │
               ┌────────┴────────┐
               ▼                 ▼
          ┌───────┐         ┌───────┐
          │Console│         │ File  │
          │Handler│         │Handler│
          └───────┘         └───────┘
```

### Event Flow (Pub/Sub)

```
┌─────────────────┐
│ Publisher       │
│ (PKUserService) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│globalEventsSignal│ ─── blinker Signal
└────────┬────────┘
         │
    ┌────┴────┬────────────┐
    ▼         ▼            ▼
┌───────┐ ┌───────┐   ┌───────┐
│Sub 1  │ │Sub 2  │   │Sub N  │
│Handler│ │Handler│   │Handler│
└───────┘ └───────┘   └───────┘
```

---

## Component Details

### PKDataProvider

**Purpose**: Unified interface for stock data from multiple sources

**Source Priority**:
1. `InMemoryCandleStore` (PKBrokers) - Real-time during market hours
2. Local pickle files - Cached historical data
3. Remote GitHub pickle files - Fallback

**Key Methods**:
```python
get_stock_data(symbol, interval, count)
get_multiple_stocks(symbols, interval)
is_realtime_available()
get_latest_price(symbol)
get_realtime_ohlcv(symbol)
```

**Thread Safety**: Uses internal locks for data access

### filterlogger

**Purpose**: Thread and process-safe logging

**Features**:
- Process-specific handler management
- Automatic caller info injection
- Filter-based message filtering
- Error messages sent to Telegram

**Implementation**:
```python
class filterlogger:
    _instance = None  # Process-safe singleton
    
    def __new__(cls, logger=None):
        with _process_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
```

### DBManager

**Purpose**: Database operations with SQLite + Turso

**Connection Strategy**:
1. Try Turso (libsql) for cloud sync
2. Fallback to local SQLite cache
3. Emergency GitHub-based OTP for new users
4. Automatic reconnection on failure

**Key Operations**:
- User CRUD operations
- OTP generation and validation
- Scanner job subscriptions
- Subscription model management

### Authentication Architecture

**OTP Generation Flow with Fallbacks**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    User requests /otp                            │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: Try Turso DB (Primary)                                   │
│ - Connect via libsql                                             │
│ - Retrieve user record with TOTP token                           │
│ - Generate OTP using pyotp.TOTP(token, interval)                │
└─────────────────────────────────┬───────────────────────────────┘
           │                      │
      SUCCESS                 FAILURE
           │                      │
           ▼                      ▼
┌──────────────────┐   ┌──────────────────────────────────────────┐
│ Cache user in    │   │ Step 2: Try LocalOTPCache (Fallback)     │
│ LocalOTPCache    │   │ - Check ~/.pkscreener/otp_cache.db       │
│ (SQLite)         │   │ - Generate OTP from cached TOTP token    │
└──────────────────┘   └─────────────────────┬────────────────────┘
                                │             │
                           CACHE HIT      CACHE MISS
                                │             │
                                ▼             ▼
                       ┌────────────┐  ┌─────────────────────────┐
                       │ Return OTP │  │ Step 3: GitHub PDF-based│
                       └────────────┘  │ (Emergency Fallback)    │
                                       │ - Generate new TOTP     │
                                       │ - Create OTP            │
                                       │ - Push password-         │
                                       │   protected PDF to repo │
                                       └─────────────────────────┘
```

**Key Components**:

| Component | Location | Purpose |
|-----------|----------|---------|
| `DBManager` | `PKDevTools/classes/DBManager.py` | Primary Turso DB operations |
| `LocalOTPCache` | `PKDevTools/classes/DBManager.py` | SQLite fallback cache |
| `PKUserRegistration` | `pkscreener/classes/PKUserRegistration.py` | CLI authentication |
| `SubData` branch | GitHub repo | Stores password-protected PDFs |

**PDF-based Authentication**:
1. Bot generates OTP and creates PDF protected with that OTP
2. PDF is pushed to `SubData` branch as `{userID}.pdf`
3. Console app downloads PDF from GitHub
4. App attempts to open PDF with user-provided OTP
5. Success = authenticated, Failure = bad credentials

### PKEnvironment

**Purpose**: Centralized configuration from `.env.dev`

**Pattern**: Singleton with dynamic attribute creation

```python
class PKEnvironment(metaclass=SingletonType):
    def __init__(self):
        self._load_secrets()
        
    def __getattr__(self, name):
        # Dynamic attribute access from secrets dict
        if name in self._allSecrets:
            return self._allSecrets[name]
        raise AttributeError(...)
```

---

## Design Patterns

### 1. Singleton Pattern

Used for: `PKEnvironment`, `filterlogger`, `PKDataProvider`

**Implementation** (via metaclass):
```python
class SingletonType(type):
    def __new__(mcs, name, bases, attrs):
        cls = super().__new__(mcs, name, bases, attrs)
        cls.__shared_instance_lock__ = Lock()
        return cls
        
    def __call__(cls, *args, **kwargs):
        with cls.__shared_instance_lock__:
            try:
                return cls.__shared_instance__
            except AttributeError:
                cls.__shared_instance__ = super().__call__(*args, **kwargs)
                return cls.__shared_instance__
```

### 2. Factory Pattern

Used for: Logger creation, data provider instantiation

```python
def get_data_provider():
    """Factory function for PKDataProvider"""
    global _data_provider_instance
    if _data_provider_instance is None:
        _data_provider_instance = PKDataProvider()
    return _data_provider_instance
```

### 3. Strategy Pattern

Used for: Data source selection in PKDataProvider

```python
class PKDataProvider:
    def _select_data_source(self, symbol, interval):
        # Priority-based strategy selection
        if self._is_realtime_available():
            return self._fetch_realtime(symbol, interval)
        elif self._has_local_cache(symbol):
            return self._load_from_cache(symbol, interval)
        else:
            return self._fetch_from_github(symbol, interval)
```

### 4. Observer Pattern (Pub/Sub)

Used for: Event notification system

```python
# Publisher
globalEventsSignal.send(sender, scannerID=id, notification=msg)

# Subscriber
globalEventsSignal.connect(handler_function)
```

### 5. Decorator Pattern

Used for: Logging, timing, timeouts

```python
@log_to(default_logger().info)
def my_function():
    pass

@exit_after(5)  # Timeout decorator
def slow_function():
    pass
```

---

## Extension Points

### Adding a New Data Source

1. Create source class implementing the interface:
```python
class MyDataSource:
    def get_data(self, symbol, interval, count):
        """Fetch data from source"""
        pass
    
    def is_available(self):
        """Check if source is accessible"""
        pass
```

2. Register in PKDataProvider:
```python
class PKDataProvider:
    def __init__(self):
        self._sources = [
            RealTimeSource(),
            LocalCacheSource(),
            MyDataSource(),  # Add your source
            GitHubSource(),
        ]
```

### Adding a New Event Type

1. Define event data structure:
```python
# In your module
MY_EVENT_TYPE = "my_custom_event"
```

2. Publish event:
```python
from PKDevTools.classes.pubsub.events import globalEventsSignal

globalEventsSignal.send(
    self,
    eventType=MY_EVENT_TYPE,
    data={"key": "value"}
)
```

3. Subscribe to event:
```python
def my_handler(sender, **kwargs):
    if kwargs.get('eventType') == MY_EVENT_TYPE:
        # Handle event
        pass

globalEventsSignal.connect(my_handler)
```

### Adding a New Database Table

1. Add model enum:
```python
class MyModel(Enum):
    id = 0
    field1 = 1
    field2 = 2
```

2. Add to DBManager:
```python
class DBManager:
    def create_my_table(self):
        query = """
            CREATE TABLE IF NOT EXISTS my_table (
                id INTEGER PRIMARY KEY,
                field1 TEXT,
                field2 INTEGER
            )
        """
        self._execute(query)
```

---

## Thread Safety

### Process-Level Safety

- `_process_lock` (multiprocessing.Lock): Singleton instantiation
- Process-specific handler tracking in logging

### Thread-Level Safety

- `_thread_lock` (threading.Lock): Within-process operations
- Thread-safe logging operations
- Locked database connections

### Safe Patterns

```python
# Correct: Using locks
with _thread_lock:
    self.logger.info(message)

# Correct: Process-safe singleton
with _process_lock:
    if cls._instance is None:
        cls._instance = super().__new__(cls)
```

### Unsafe Patterns to Avoid

```python
# Wrong: No lock protection
self.shared_state += 1

# Wrong: Checking then acting without lock
if self._instance is None:  # Race condition!
    self._instance = create_instance()
```

---

## Error Handling

### Logging Errors

Errors are automatically logged with traceback:

```python
logger.error("Database connection failed")
# Output includes:
# - Caller file, function, line number
# - Full traceback
# - Message sent to Telegram (DEV_CHANNEL_ID)
```

### Database Error Handling

```python
try:
    result = self._execute_query(query)
except Exception as e:
    if "BLOCKED" in str(e).upper():
        # Handle Turso quota exceeded
        return self._fallback_to_local()
    raise
```

### Graceful Degradation

PKDevTools follows graceful degradation:

1. **Data Provider**: Real-time → Cache → Remote
2. **Database**: Turso → SQLite
3. **Logging**: filterlogger → emptylogger (no-op)

---

## Best Practices for Contributors

### 1. Always Use the Logger

```python
from PKDevTools.classes.log import default_logger

logger = default_logger()
logger.debug("Detailed diagnostic info")
logger.info("General operational info")
logger.warning("Warning conditions")
logger.error("Error conditions")
```

### 2. Respect Environment Variables

```python
import os

# Check before logging
if "PKDevTools_Default_Log_Level" in os.environ:
    logger.info("This will be logged")
```

### 3. Use Thread-Safe Operations

```python
from threading import Lock

_lock = Lock()

def thread_safe_operation():
    with _lock:
        # Critical section
        pass
```

### 4. Handle Exceptions Gracefully

```python
try:
    result = risky_operation()
except SpecificException as e:
    logger.warning(f"Expected error: {e}")
    result = fallback_value
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

### 5. Write Tests

```python
import pytest
from PKDevTools.classes.MyClass import MyClass

class TestMyClass:
    def test_method_success(self):
        obj = MyClass()
        assert obj.method() == expected_result
    
    def test_method_failure(self):
        with pytest.raises(ExpectedException):
            obj.method_that_fails()
```

---

## Performance Considerations

### Caching

- HTTP responses cached for 6 hours (via requests_cache)
- Pickle files cached locally
- In-memory candle store for real-time data

### Lazy Loading

```python
# PKBrokers imported only when needed
_PKBROKERS_AVAILABLE = False
try:
    from pkbrokers.kite.inMemoryCandleStore import get_candle_store
    _PKBROKERS_AVAILABLE = True
except ImportError:
    pass
```

### Connection Pooling

- Database connections managed per-process
- HTTP session reused across requests

---

## Configuration Files

### .env.dev

```env
GITHUB_TOKEN=ghp_xxxx
TOKEN=123456789:ABCdefGHI
CHAT_ID=-1001234567890
chat_idADMIN=123456789
TURSO_DB_URL=libsql://your-db.turso.io
TURSO_DB_AUTH_TOKEN=eyJhbGc...
```

### setup.cfg

```ini
[metadata]
name = PKDevTools
version = attr: PKDevTools.classes.__init__.VERSION

[options]
packages = find:
python_requires = >=3.9
```

---

For questions or contributions, please open an issue or submit a pull request on [GitHub](https://github.com/pkjmesra/PKDevTools).










