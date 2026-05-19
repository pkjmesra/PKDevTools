# -*- coding: utf-8 -*-
#!/usr/bin/python3
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

import fcntl
import os
import pickle
import shutil
import tempfile
import time
from typing import Any, Optional, Tuple, Callable

from PKDevTools.classes.log import default_logger


class SimplePickler:
    """
    Thread‑ and process‑safe pickler with atomic writes and robust reads.
    
    Features:
    - Atomic write: temp file + rename (no partial writes)
    - Exclusive lock during write, shared lock during read
    - Automatic retry on transient errors (file locked, incomplete read)
    - Recovery from corrupted files using backups or fallback
    - Minimum size validation
    """

    DEFAULT_RETRIES = 3
    DEFAULT_RETRY_DELAY = 0.2  # seconds
    MIN_VALID_SIZE = 1024       # 1 KB

    def __init__(self, logger=None):
        self.logger = logger or default_logger()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def atomic_dump(self, data: Any, filepath: str) -> bool:
        """
        Atomically write a pickle file.
        
        Returns:
            True if successful, False otherwise.
        """
        dirname = os.path.dirname(filepath)
        os.makedirs(dirname, exist_ok=True)

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='wb', dir=dirname, delete=False, suffix='.pkl.tmp'
            ) as tf:
                temp_path = tf.name
                # Acquire exclusive lock on the temporary file (protects against
                # concurrent writes to the same temp file – mostly for safety)
                fcntl.flock(tf, fcntl.LOCK_EX)
                pickle.dump(data, tf, protocol=pickle.HIGHEST_PROTOCOL)
                tf.flush()
                os.fsync(tf.fileno())
                fcntl.flock(tf, fcntl.LOCK_UN)

            # Atomic rename (POSIX)
            os.replace(temp_path, filepath)
            self.logger.debug(f"Atomic write successful: {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"Atomic write failed for {filepath}: {e}")
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            return False

    def safe_load(self, filepath: str,
                  retries: int = DEFAULT_RETRIES,
                  delay: float = DEFAULT_RETRY_DELAY,
                  fallback_loader: Optional[Callable[[], Any]] = None) -> Tuple[Optional[Any], bool]:
        """
        Safely load a pickle file with locking and retry.
        
        Returns:
            (data, is_fresh) where is_fresh is True if the file was intact,
            or (None, False) if unrecoverable.
        """
        if not os.path.exists(filepath):
            self.logger.debug(f"File does not exist: {filepath}")
            return None, False

        # Quick size sanity check
        size = os.path.getsize(filepath)
        if size < self.MIN_VALID_SIZE:
            self.logger.warning(f"File too small ({size} bytes): {filepath}")
            return self._recover_or_raise(filepath, fallback_loader)

        for attempt in range(retries):
            try:
                with open(filepath, 'rb') as f:
                    # Acquire shared lock (allows concurrent reads, blocks writes)
                    fcntl.flock(f, fcntl.LOCK_SH)
                    try:
                        data = pickle.load(f)
                    finally:
                        fcntl.flock(f, fcntl.LOCK_UN)

                self.logger.debug(f"Successfully loaded {filepath} (attempt {attempt+1})")
                return data, True

            except (pickle.UnpicklingError, EOFError, ValueError) as e:
                self.logger.warning(f"Pickle load error (attempt {attempt+1}/{retries}): {e}")
                if attempt == retries - 1:
                    return self._recover_or_raise(filepath, fallback_loader)
                time.sleep(delay * (attempt + 1))

            except OSError as e:
                # File may be locked by a writer – wait and retry
                self.logger.debug(f"OS error (likely locked): {e}")
                if attempt == retries - 1:
                    self.logger.error(f"Could not read {filepath} after {retries} attempts")
                    return None, False
                time.sleep(delay)

        return None, False

    def safe_load_with_fallback(self, filepath: str,
                                backup_paths: Optional[list] = None,
                                retries: int = DEFAULT_RETRIES) -> Optional[Any]:
        """
        Load a pickle, trying multiple backup paths if primary fails.
        
        Returns:
            The loaded data, or None if all attempts fail.
        """
        data, ok = self.safe_load(filepath, retries=retries)
        if ok:
            return data

        if backup_paths is None:
            backup_paths = self._find_backup_files(filepath)

        for backup in backup_paths:
            self.logger.info(f"Trying backup file: {backup}")
            data, ok = self.safe_load(backup, retries=1)
            if ok:
                self.logger.info(f"Restored from backup: {backup}")
                # Optionally restore the primary file
                self.atomic_dump(data, filepath)
                return data

        self.logger.error(f"All load attempts failed for {filepath} and its backups")
        return None

    # -------------------------------------------------------------------------
    # Recovery helpers
    # -------------------------------------------------------------------------

    def _recover_or_raise(self, filepath: str,
                          fallback_loader: Optional[Callable[[], Any]]) -> Tuple[Optional[Any], bool]:
        """Try to recover a corrupted file, else return (None, False)."""
        # 1. Try to find a valid backup
        backup = self._find_best_backup(filepath)
        if backup:
            try:
                with open(backup, 'rb') as f:
                    data = pickle.load(f)
                self.logger.info(f"Recovered {filepath} from backup {backup}")
                # Restore primary
                self.atomic_dump(data, filepath)
                return data, True
            except Exception as e:
                self.logger.error(f"Backup also corrupted: {e}")

        # 2. If fallback loader provided (e.g., regenerate from candle store)
        if fallback_loader:
            self.logger.info("Attempting to regenerate data via fallback loader")
            try:
                data = fallback_loader()
                if data:
                    self.atomic_dump(data, filepath)
                    return data, True
            except Exception as e:
                self.logger.error(f"Fallback loader failed: {e}")

        # 3. Last resort: delete the corrupt file so fresh copy can be downloaded
        self.logger.warning(f"Removing corrupted file: {filepath}")
        try:
            os.remove(filepath)
        except:
            pass
        return None, False

    def _find_best_backup(self, filepath: str) -> Optional[str]:
        """Return the most recent valid backup file."""
        backups = self._find_backup_files(filepath)
        for backup in backups:
            try:
                # Quick size check
                if os.path.getsize(backup) < self.MIN_VALID_SIZE:
                    continue
                with open(backup, 'rb') as f:
                    pickle.load(f)   # test load
                return backup
            except:
                continue
        return None

    def _find_backup_files(self, filepath: str) -> list:
        """Find candidate backup files (dated versions, .bak, etc.)."""
        candidates = []
        dirname = os.path.dirname(filepath)
        basename = os.path.basename(filepath)

        # 1. Look for date‑suffixed versions (stock_data_*.pkl)
        import glob
        pattern = os.path.join(dirname, basename.replace('.pkl', '_*.pkl'))
        for f in glob.glob(pattern):
            if f != filepath:
                candidates.append(f)

        # 2. Look for .bak file
        bak_path = filepath + '.bak'
        if os.path.exists(bak_path):
            candidates.append(bak_path)

        # 3. Look for generic fallback (e.g., daily_candles.pkl if current is stock_data_...)
        if 'stock_data' in basename:
            generic = os.path.join(dirname, 'daily_candles.pkl')
            if os.path.exists(generic):
                candidates.append(generic)

        # Sort by modification time (newest first)
        candidates.sort(key=os.path.getmtime, reverse=True)
        return candidates

    # -------------------------------------------------------------------------
    # Context managers for explicit locking (if needed)
    # -------------------------------------------------------------------------

    @staticmethod
    def lock_file(filepath: str, shared: bool = True):
        """Context manager for explicit file locking."""
        class LockContext:
            def __enter__(self_ctx):
                self_ctx.f = open(filepath, 'rb' if shared else 'wb')
                fcntl.flock(self_ctx.f, fcntl.LOCK_SH if shared else fcntl.LOCK_EX)
                return self_ctx.f
            def __exit__(self_ctx, *args):
                fcntl.flock(self_ctx.f, fcntl.LOCK_UN)
                self_ctx.f.close()
        return LockContext()