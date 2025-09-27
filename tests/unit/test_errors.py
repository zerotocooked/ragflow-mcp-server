"""Unit tests for error handling system."""

import pytest
from mcp import ErrorData

from ragflow_mcp_server.errors import (
    RAGFlowError,
    ConfigurationError,
    AuthenticationError,
    APIError,
    FileError,
    ValidationError,
    sanitize_error_message,
    format_mcp_error,
    get_error_details,
)


class TestRAGFlowError:
    """Test base RAGFlow error class."""
    
    def test_basic_error(self):
        """Test basic error creation."""
        error = RAGFlowError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details is None
    
    def test_error_with_details(self):
        """Test error with additional details."""
        details = {"key": "value"}
        error = RAGFlowError("Test error", details)
        assert error.details == details


class TestConfigurationError:
    """Test configuration error class."""
    
    def test_basic_config_error(self):
        """Test basic configuration error."""
        error = ConfigurationError("Missing config")
        assert str(error) == "Missing config"
        assert error.config_key is None
    
    def test_config_error_with_key(self):
        """Test configuration error with config key."""
        error = ConfigurationError("Missing API key", "api_key")
        assert error.config_key == "api_key"


class TestAuthenticationError:
    """Test authentication error class."""
    
    def test_default_auth_error(self):
        """Test default authentication error."""
        error = AuthenticationError()
        assert str(error) == "Authentication failed"
    
    def test_custom_auth_error(self):
        """Test custom authentication error message."""
        error = AuthenticationError("Invalid token")
        assert str(error) == "Invalid token"


class TestAPIError:
    """Test API error class."""
    
    def test_basic_api_error(self):
        """Test basic API error."""
        error = APIError("API request failed")
        assert str(error) == "API request failed"
        assert error.status_code is None
        assert error.response_data is None
    
    def test_api_error_with_status(self):
        """Test API error with status code."""
        error = APIError("Not found", 404)
        assert error.status_code == 404
    
    def test_api_error_with_response_data(self):
        """Test API error with response data."""
        response_data = {"error": "Invalid request"}
        error = APIError("Bad request", 400, response_data)
        assert error.response_data == response_data


class TestFileError:
    """Test file error class."""
    
    def test_basic_file_error(self):
        """Test basic file error."""
        error = FileError("File not found")
        assert str(error) == "File not found"
        assert error.file_path is None
    
    def test_file_error_with_path(self):
        """Test file error with file path."""
        error = FileError("File not found", "/path/to/file.txt")
        assert error.file_path == "/path/to/file.txt"


class TestValidationError:
    """Test validation error class."""
    
    def test_basic_validation_error(self):
        """Test basic validation error."""
        error = ValidationError("Invalid input")
        assert str(error) == "Invalid input"
        assert error.field is None
    
    def test_validation_error_with_field(self):
        """Test validation error with field name."""
        error = ValidationError("Invalid email", "email")
        assert error.field == "email"


class TestSanitizeErrorMessage:
    """Test error message sanitization."""
    
    def test_sanitize_api_key(self):
        """Test sanitizing API key from error message."""
        message = "Failed to authenticate with api_key=sk-1234567890abcdef"
        sanitized = sanitize_error_message(message)
        assert "sk-1234567890abcdef" not in sanitized
        assert "api_key=***" in sanitized
    
    def test_sanitize_token(self):
        """Test sanitizing token from error message."""
        message = "Invalid token: bearer_token_12345"
        sanitized = sanitize_error_message(message)
        assert "bearer_token_12345" not in sanitized
        assert "token=***" in sanitized
    
    def test_sanitize_password(self):
        """Test sanitizing password from error message."""
        message = "Authentication failed with password=secret123"
        sanitized = sanitize_error_message(message)
        assert "secret123" not in sanitized
        assert "password=***" in sanitized
    
    def test_sanitize_url_with_credentials(self):
        """Test sanitizing URL with credentials."""
        message = "Failed to connect to https://user:pass@example.com/api"
        sanitized = sanitize_error_message(message)
        assert "user:pass" not in sanitized
        assert "https://***:***@***" in sanitized
    
    def test_sanitize_file_paths(self):
        """Test sanitizing sensitive file paths."""
        message = "Cannot read /home/user/.config/secret.key"
        sanitized = sanitize_error_message(message)
        assert "/home/user/.config/secret.key" not in sanitized
        assert "/***" in sanitized
    
    def test_no_sanitization_needed(self):
        """Test message that doesn't need sanitization."""
        message = "File not found"
        sanitized = sanitize_error_message(message)
        assert sanitized == message


class TestFormatMcpError:
    """Test MCP error formatting."""
    
    # JSON-RPC error codes
    INVALID_PARAMS = -32602
    INVALID_REQUEST = -32600
    INTERNAL_ERROR = -32603
    
    def test_format_configuration_error(self):
        """Test formatting configuration error."""
        error = ConfigurationError("Missing API key")
        mcp_error = format_mcp_error(error)
        assert mcp_error.code == self.INVALID_PARAMS
        assert "Missing API key" in mcp_error.message
    
    def test_format_authentication_error(self):
        """Test formatting authentication error."""
        error = AuthenticationError("Invalid credentials")
        mcp_error = format_mcp_error(error)
        assert mcp_error.code == self.INVALID_REQUEST
        assert mcp_error.message == "Authentication failed"
    
    def test_format_validation_error(self):
        """Test formatting validation error."""
        error = ValidationError("Invalid email format")
        mcp_error = format_mcp_error(error)
        assert mcp_error.code == self.INVALID_PARAMS
        assert "Invalid email format" in mcp_error.message
    
    def test_format_file_error(self):
        """Test formatting file error."""
        error = FileError("File not found")
        mcp_error = format_mcp_error(error)
        assert mcp_error.code == self.INVALID_PARAMS
        assert "File not found" in mcp_error.message
    
    def test_format_api_error_404(self):
        """Test formatting 404 API error."""
        error = APIError("Resource not found", 404)
        mcp_error = format_mcp_error(error)
        assert mcp_error.code == self.INVALID_PARAMS
        assert mcp_error.message == "Resource not found"
    
    def test_format_api_error_401(self):
        """Test formatting 401 API error."""
        error = APIError("Unauthorized", 401)
        mcp_error = format_mcp_error(error)
        assert mcp_error.code == self.INVALID_REQUEST
        assert mcp_error.message == "Authentication failed"
    
    def test_format_api_error_403(self):
        """Test formatting 403 API error."""
        error = APIError("Forbidden", 403)
        mcp_error = format_mcp_error(error)
        assert mcp_error.code == self.INVALID_REQUEST
        assert mcp_error.message == "Access denied"
    
    def test_format_api_error_429(self):
        """Test formatting 429 API error."""
        error = APIError("Too many requests", 429)
        mcp_error = format_mcp_error(error)
        assert mcp_error.code == self.INVALID_REQUEST
        assert mcp_error.message == "Rate limit exceeded"
    
    def test_format_api_error_500(self):
        """Test formatting 500 API error."""
        error = APIError("Internal server error", 500)
        mcp_error = format_mcp_error(error)
        assert mcp_error.code == self.INTERNAL_ERROR
        assert "Internal server error" in mcp_error.message
    
    def test_format_generic_ragflow_error(self):
        """Test formatting generic RAGFlow error."""
        error = RAGFlowError("Something went wrong")
        mcp_error = format_mcp_error(error)
        assert mcp_error.code == self.INTERNAL_ERROR
        assert "Something went wrong" in mcp_error.message
    
    def test_format_unknown_error(self):
        """Test formatting unknown error type."""
        error = ValueError("Unknown error")
        mcp_error = format_mcp_error(error)
        assert mcp_error.code == self.INTERNAL_ERROR
        assert mcp_error.message == "An unexpected error occurred"


class TestGetErrorDetails:
    """Test error details extraction."""
    
    def test_configuration_error_details(self):
        """Test getting configuration error details."""
        error = ConfigurationError("Missing API key", "api_key")
        details = get_error_details(error)
        assert details["type"] == "ConfigurationError"
        assert details["message"] == "Missing API key"
        assert details["config_key"] == "api_key"
    
    def test_api_error_details(self):
        """Test getting API error details."""
        response_data = {"error": "Not found"}
        error = APIError("Resource not found", 404, response_data)
        details = get_error_details(error)
        assert details["type"] == "APIError"
        assert details["status_code"] == 404
        assert details["response_data"] == response_data
    
    def test_file_error_details(self):
        """Test getting file error details."""
        error = FileError("File not found", "/path/to/file.txt")
        details = get_error_details(error)
        assert details["type"] == "FileError"
        assert details["file_path"] == "/path/to/file.txt"
    
    def test_validation_error_details(self):
        """Test getting validation error details."""
        error = ValidationError("Invalid email", "email")
        details = get_error_details(error)
        assert details["type"] == "ValidationError"
        assert details["field"] == "email"
    
    def test_ragflow_error_details(self):
        """Test getting RAGFlow error details."""
        error_details = {"code": "UPLOAD_FAILED"}
        error = RAGFlowError("Upload failed", error_details)
        details = get_error_details(error)
        assert details["type"] == "RAGFlowError"
        assert details["details"] == error_details
    
    def test_generic_error_details(self):
        """Test getting generic error details."""
        error = ValueError("Invalid value")
        details = get_error_details(error)
        assert details["type"] == "ValueError"
        assert details["message"] == "Invalid value"
        assert "config_key" not in details
        assert "status_code" not in details