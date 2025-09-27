"""Error handling for RAGFlow MCP Server."""

import re
from typing import Optional, Any, Dict
from mcp import ErrorData


class RAGFlowError(Exception):
    """Base exception for RAGFlow operations."""
    
    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        """Initialize RAGFlow error.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details


class ConfigurationError(RAGFlowError):
    """Configuration related errors."""
    
    def __init__(self, message: str, config_key: Optional[str] = None) -> None:
        """Initialize configuration error.
        
        Args:
            message: Error message
            config_key: Configuration key that caused the error
        """
        super().__init__(message)
        self.config_key = config_key


class AuthenticationError(RAGFlowError):
    """Authentication related errors."""
    
    def __init__(self, message: str = "Authentication failed") -> None:
        """Initialize authentication error.
        
        Args:
            message: Error message
        """
        super().__init__(message)


class APIError(RAGFlowError):
    """RAGFlow API related errors."""
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None,
        response_data: Optional[Any] = None
    ) -> None:
        """Initialize API error.
        
        Args:
            message: Error message
            status_code: HTTP status code
            response_data: Response data from API
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class FileError(RAGFlowError):
    """File operation related errors."""
    
    def __init__(self, message: str, file_path: Optional[str] = None) -> None:
        """Initialize file error.
        
        Args:
            message: Error message
            file_path: Path to the file that caused the error
        """
        super().__init__(message)
        self.file_path = file_path


class ValidationError(RAGFlowError):
    """Input validation related errors."""
    
    def __init__(self, message: str, field: Optional[str] = None) -> None:
        """Initialize validation error.
        
        Args:
            message: Error message
            field: Field name that failed validation
        """
        super().__init__(message)
        self.field = field


def sanitize_error_message(message: str) -> str:
    """Sanitize error message to remove sensitive information.
    
    Args:
        message: Original error message
        
    Returns:
        Sanitized error message
    """
    # Remove API keys, tokens, and other sensitive patterns
    patterns = [
        (r'api[_-]?key[=:\s]+[^\s\n]+', 'api_key=***'),
        (r'token[=:\s]+[^\s\n]+', 'token=***'),
        (r'password[=:\s]+[^\s\n]+', 'password=***'),
        (r'secret[=:\s]+[^\s\n]+', 'secret=***'),
        (r'authorization[=:\s]+[^\s\n]+', 'authorization=***'),
        # Remove file paths that might contain sensitive info
        (r'/[^\s]*(?:config|secret|key|token)[^\s]*', '/***'),
        # Remove URLs with credentials
        (r'https?://[^:]+:[^@]+@[^\s]+', 'https://***:***@***'),
    ]
    
    sanitized = message
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    
    return sanitized


def format_mcp_error(error: Exception) -> ErrorData:
    """Format exception as MCP error response.
    
    Args:
        error: Exception to format
        
    Returns:
        MCP error response
    """
    # JSON-RPC error codes
    INVALID_PARAMS = -32602
    INVALID_REQUEST = -32600
    INTERNAL_ERROR = -32603
    
    if isinstance(error, ConfigurationError):
        return ErrorData(
            code=INVALID_PARAMS,
            message=sanitize_error_message(str(error))
        )
    elif isinstance(error, AuthenticationError):
        return ErrorData(
            code=INVALID_REQUEST,
            message="Authentication failed"
        )
    elif isinstance(error, ValidationError):
        return ErrorData(
            code=INVALID_PARAMS,
            message=sanitize_error_message(str(error))
        )
    elif isinstance(error, FileError):
        return ErrorData(
            code=INVALID_PARAMS,
            message=sanitize_error_message(str(error))
        )
    elif isinstance(error, APIError):
        if error.status_code == 404:
            return ErrorData(
                code=INVALID_PARAMS,
                message="Resource not found"
            )
        elif error.status_code == 401:
            return ErrorData(
                code=INVALID_REQUEST,
                message="Authentication failed"
            )
        elif error.status_code == 403:
            return ErrorData(
                code=INVALID_REQUEST,
                message="Access denied"
            )
        elif error.status_code == 429:
            return ErrorData(
                code=INVALID_REQUEST,
                message="Rate limit exceeded"
            )
        else:
            return ErrorData(
                code=INTERNAL_ERROR,
                message=sanitize_error_message(str(error))
            )
    elif isinstance(error, RAGFlowError):
        return ErrorData(
            code=INTERNAL_ERROR,
            message=sanitize_error_message(str(error))
        )
    else:
        return ErrorData(
            code=INTERNAL_ERROR,
            message="An unexpected error occurred"
        )


def get_error_details(error: Exception) -> Dict[str, Any]:
    """Get detailed error information for logging.
    
    Args:
        error: Exception to analyze
        
    Returns:
        Dictionary with error details
    """
    details = {
        "type": type(error).__name__,
        "message": str(error),
    }
    
    if isinstance(error, ConfigurationError):
        details["config_key"] = error.config_key
    elif isinstance(error, APIError):
        details["status_code"] = error.status_code
        details["response_data"] = error.response_data
    elif isinstance(error, FileError):
        details["file_path"] = error.file_path
    elif isinstance(error, ValidationError):
        details["field"] = error.field
    elif isinstance(error, RAGFlowError):
        details["details"] = error.details
    
    return details