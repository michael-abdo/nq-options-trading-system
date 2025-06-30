#!/usr/bin/env python3
"""
Centralized Error Handling Utilities
Consolidates error handling patterns from across the codebase
"""

import logging
import functools
from typing import Dict, Any, Optional, Callable, Union
from pathlib import Path


logger = logging.getLogger(__name__)


def safe_execute(operation_name: str, 
                default_return: Any = None,
                log_errors: bool = True,
                raise_on_error: bool = False) -> Callable:
    """
    Decorator for safe execution with standardized error handling
    
    Args:
        operation_name: Human-readable name for the operation
        default_return: Value to return on error
        log_errors: Whether to log errors
        raise_on_error: Whether to re-raise exceptions
        
    Returns:
        Decorated function with error handling
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"❌ {operation_name} failed: {str(e)}")
                
                if raise_on_error:
                    raise
                    
                return default_return
        return wrapper
    return decorator


def create_error_result(operation: str, error: Exception, 
                       include_traceback: bool = False) -> Dict[str, Any]:
    """
    Create standardized error result dictionary
    
    Args:
        operation: Name of the failed operation
        error: Exception that occurred
        include_traceback: Whether to include full traceback
        
    Returns:
        Standardized error result
    """
    import traceback
    
    result = {
        "status": "failed",
        "operation": operation,
        "error": str(error),
        "error_type": type(error).__name__
    }
    
    if include_traceback:
        result["traceback"] = traceback.format_exc()
    
    return result


def create_success_result(operation: str, data: Any = None, 
                         message: str = None) -> Dict[str, Any]:
    """
    Create standardized success result dictionary
    
    Args:
        operation: Name of the successful operation
        data: Optional data payload
        message: Optional success message
        
    Returns:
        Standardized success result
    """
    result = {
        "status": "success",
        "operation": operation
    }
    
    if data is not None:
        result["data"] = data
    
    if message:
        result["message"] = message
    
    return result


class ErrorHandler:
    """Centralized error handling with context"""
    
    def __init__(self, operation_context: str):
        self.context = operation_context
        self.errors = []
        
    def handle_error(self, error: Exception, operation: str = None) -> Dict[str, Any]:
        """Handle an error and return standardized result"""
        op_name = operation or self.context
        error_result = create_error_result(op_name, error)
        
        # Track errors for batch reporting
        self.errors.append(error_result)
        
        logger.error(f"❌ {op_name} failed: {str(error)}")
        return error_result
    
    def handle_success(self, operation: str = None, data: Any = None, 
                      message: str = None) -> Dict[str, Any]:
        """Handle success and return standardized result"""
        op_name = operation or self.context
        logger.info(f"✅ {op_name} completed successfully")
        return create_success_result(op_name, data, message)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors encountered"""
        return {
            "context": self.context,
            "error_count": len(self.errors),
            "errors": self.errors
        }


# Common error handling patterns
def handle_file_operation(operation: str, file_path: Union[str, Path]) -> Callable:
    """Decorator for file operations with standard error handling"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except FileNotFoundError:
                error_msg = f"File not found: {file_path}"
                logger.error(f"❌ {operation} failed: {error_msg}")
                return create_error_result(operation, FileNotFoundError(error_msg))
            except PermissionError:
                error_msg = f"Permission denied: {file_path}"
                logger.error(f"❌ {operation} failed: {error_msg}")
                return create_error_result(operation, PermissionError(error_msg))
            except Exception as e:
                logger.error(f"❌ {operation} failed: {str(e)}")
                return create_error_result(operation, e)
        return wrapper
    return decorator


def handle_api_operation(operation: str, endpoint: str = None) -> Callable:
    """Decorator for API operations with standard error handling"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ConnectionError as e:
                error_msg = f"Connection failed: {endpoint or 'unknown endpoint'}"
                logger.error(f"❌ {operation} failed: {error_msg}")
                return create_error_result(operation, ConnectionError(error_msg))
            except TimeoutError as e:
                error_msg = f"Request timeout: {endpoint or 'unknown endpoint'}"
                logger.error(f"❌ {operation} failed: {error_msg}")
                return create_error_result(operation, TimeoutError(error_msg))
            except Exception as e:
                logger.error(f"❌ {operation} failed: {str(e)}")
                return create_error_result(operation, e)
        return wrapper
    return decorator


# Backward compatibility functions
def safe_operation(operation_name: str, func: Callable, *args, **kwargs) -> Any:
    """Execute operation safely with error logging"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"❌ {operation_name} failed: {str(e)}")
        return None