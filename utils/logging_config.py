#!/usr/bin/env python3
"""
Comprehensive logging configuration for NQ Options EV Trading System
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
import sys


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log output for console"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(log_level=logging.DEBUG, console_level=logging.INFO):
    """
    Set up comprehensive logging configuration
    
    Args:
        log_level: Level for file logging (default: DEBUG)
        console_level: Level for console logging (default: INFO)
    
    Returns:
        tuple: (log_dir, session_id) for reference
    """
    # Create session-specific log directory
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_dir = Path('logs') / timestamp
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    
    # File formatters
    file_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s | %(name)-20s | %(funcName)-20s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s | %(name)s | %(pathname)s:%(lineno)d | %(funcName)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S.%f'[:-3]
    )
    
    # Console formatter (with colors)
    console_formatter = ColoredFormatter(
        '[%(asctime)s] %(levelname)-8s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Main log file - all messages
    main_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'main.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    main_handler.setLevel(log_level)
    main_handler.setFormatter(file_formatter)
    
    # Calculations log - detailed calculation steps
    calc_handler = logging.FileHandler(log_dir / 'calculations.log')
    calc_handler.setLevel(logging.DEBUG)
    calc_handler.setFormatter(detailed_formatter)
    calc_filter = logging.Filter()
    calc_filter.filter = lambda record: 'calc' in record.name.lower() or 'probability' in record.msg.lower() or 'factor' in record.msg.lower()
    calc_handler.addFilter(calc_filter)
    
    # Data log - data fetching and parsing
    data_handler = logging.FileHandler(log_dir / 'data.log')
    data_handler.setLevel(logging.DEBUG)
    data_handler.setFormatter(detailed_formatter)
    data_filter = logging.Filter()
    data_filter.filter = lambda record: 'data' in record.name.lower() or 'scrape' in record.msg.lower() or 'fetch' in record.msg.lower()
    data_handler.addFilter(data_filter)
    
    # Error log - warnings and errors only
    error_handler = logging.FileHandler(log_dir / 'errors.log')
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(detailed_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_formatter)
    
    # Add all handlers to root logger
    root_logger.addHandler(main_handler)
    root_logger.addHandler(calc_handler)
    root_logger.addHandler(data_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)
    
    # Log session start
    logging.info("="*80)
    logging.info(f"NQ Options EV Trading System - Session Started")
    logging.info(f"Log Directory: {log_dir.absolute()}")
    logging.info(f"Session ID: {timestamp}")
    logging.info(f"Python Version: {sys.version}")
    logging.info("="*80)
    
    return str(log_dir), timestamp


def get_logger(name):
    """
    Get a logger instance with the given name
    
    Args:
        name: Logger name (usually __name__ from the calling module)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


def log_function_call(func):
    """
    Decorator to log function calls with arguments and return values
    """
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        func_name = func.__name__
        
        # Log function entry
        logger.debug(f">>> Entering {func_name}")
        if args:
            logger.debug(f"    Args: {args}")
        if kwargs:
            logger.debug(f"    Kwargs: {kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"<<< Exiting {func_name} with result: {result}")
            return result
        except Exception as e:
            logger.error(f"!!! ERROR in {func_name}: {type(e).__name__}: {str(e)}")
            raise
    
    return wrapper


def log_section(title, level=logging.INFO):
    """
    Log a section header for better readability
    
    Args:
        title: Section title
        level: Logging level (default: INFO)
    """
    logger = logging.getLogger()
    separator = "=" * 60
    logger.log(level, separator)
    logger.log(level, f"{title.center(60)}")
    logger.log(level, separator)