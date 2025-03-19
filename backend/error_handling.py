import logging
from typing import Dict, Any, Optional, Union
from fastapi import HTTPException, status
import sqlite3

# Configure logger
logger = logging.getLogger("f1dashboard")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("f1dashboard.log")
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class F1DashboardError(Exception):
    """Base exception class for F1 Dashboard application."""
    def __init__(
        self, 
        message: str, 
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        error_dict = {
            "error": self.message,
            "status_code": self.status_code
        }
        if self.details:
            error_dict["details"] = self.details
        return error_dict

# Common error instances
class DatabaseError(F1DashboardError):
    """Database-related errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )
        logger.error(f"Database error: {message}", exc_info=True)

class ResourceNotFoundError(F1DashboardError):
    """Resource not found errors."""
    def __init__(self, resource_type: str, identifier: Union[str, int], details: Optional[Dict[str, Any]] = None):
        message = f"{resource_type} with id {identifier} not found"
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )
        logger.warning(f"Resource not found: {message}")

class ValidationError(F1DashboardError):
    """Input validation errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )
        logger.warning(f"Validation error: {message}")

# Utility functions
def log_and_raise(error: F1DashboardError) -> None:
    """Log the error and raise it for the exception handler."""
    # Additional logging can be done here if needed
    raise error

def handle_exception(func_name: str, e: Exception) -> F1DashboardError:
    """Convert standard exceptions to F1DashboardError with logging."""
    if isinstance(e, sqlite3.Error):
        return DatabaseError(f"SQLite error in {func_name}: {str(e)}")
    elif isinstance(e, F1DashboardError):
        return e
    else:
        message = f"Unexpected error in {func_name}: {str(e)}"
        logger.error(message, exc_info=True)
        return F1DashboardError(message)