"""Logging configuration for the application."""

import logging
import os
import time
from logging.handlers import BaseRotatingHandler
from enum import Enum

class ErrorAction(Enum):
    """Enum defining possible actions to take when an error occurs."""
    IGNORE = 1
    RETRY = 2
    TERMINATE = 3

class LoggerConfig:
    """Configuration class for establishing logging of errors and info messages"""

    def __init__(self):
        """Initialize logging configuration with default settings."""
        self.error_actions = {
            logging.DEBUG: ErrorAction.IGNORE,
            logging.INFO: ErrorAction.IGNORE,
            logging.WARNING: ErrorAction.IGNORE,
            logging.ERROR: ErrorAction.IGNORE, # Could set to RETRY, but retry is disabled here, handled explicitly in code.
            logging.CRITICAL: ErrorAction.TERMINATE # Therefore, any troublesome errors must be flagged as CRITICAL to stop process
        }
        self.max_retries  = 3
        self.log_file     = 'logs/app.log'
        self.max_log_size = 5 * 1024 * 1024  # 5 MB
        self.backup_count = 9  # Keep 9 backup files, plus the current on

class NewFileForEachRunHandler(BaseRotatingHandler):
    def __init__(self, app, filename, mode='a', encoding=None, delay=False, max_files=10):
        self.app = app
        self.storage_manager = app.storage_manager
        self.base_filename = os.path.join('logs', os.path.basename(filename))
        self.max_files = max_files
        timestamp = int(time.time())
        self.current_filename = f"{os.path.splitext(self.base_filename)[0]}_{timestamp}.log"
        
        super().__init__(self.current_filename, mode, encoding, delay)
        
        self.rotate_files()

    def rotate_files(self):
        base_name = os.path.splitext(os.path.basename(self.base_filename))[0]
        files = self.storage_manager.list_files(f"{base_name}*.log")
        
        if len(files) > self.max_files:
            files.sort(key=lambda x: self.storage_manager.get_file_modification_time(x), reverse=True)
            for old_file in files[self.max_files:]:
                self.storage_manager.delete_file(old_file)

    def emit(self, record):
        try:
            msg = self.format(record)
            self.storage_manager.append_to_file(msg + self.terminator, self.current_filename)
        except Exception:
            self.handleError(record)

    def close(self):
        super().close()
