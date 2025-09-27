"""Unit tests for comprehensive validation and error handling."""

import pytest
import os
import tempfile
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from ragflow_mcp_server.server import RAGFlowMCPServer
from ragflow_mcp_server.config import RAGFlowConfig
from ragflow_mcp_server.errors import ValidationError, FileError, APIError, ConfigurationError
from ragflow_mcp_server.client import RAGFlowClient


class TestParameterValidation:
    """Test parameter validation methods."""
    
    @pytest.fixture
    def server(self):
        """Create a test server instance."""
        config = RAGFlowConfig(
            base_url="http://test.example.com",
            api_key="test_key",
            timeout=30,
            max_retries=3
        )
        return RAGFlowMCPServer(config)
    
    def test_validate_string_parameter_valid(self, server):
        """Test valid string parameter validation."""
        result = server._validate_string_parameter("test_value", "test_param")
        assert result == "test_value"
    
    def test_validate_string_parameter_empty(self, server):
        """Test empty string parameter validation."""
        with pytest.raises(ValidationError) as exc_info:
            server._validate_string_parameter("", "test_param")
        assert "must be at least 1 characters long" in str(exc_info.value)
        assert exc_info.value.field == "test_param"
    
    def test_validate_string_parameter_too_long(self, server):
        """Test string parameter that's too long."""
        long_string = "x" * 1001
        with pytest.raises(ValidationError) as exc_info:
            server._validate_string_parameter(long_string, "test_param")
        assert "cannot exceed 1000 characters" in str(exc_info.value)
    
    def test_validate_string_parameter_not_string(self, server):
        """Test non-string parameter validation."""
        with pytest.raises(ValidationError) as exc_info:
            server._validate_string_parameter(123, "test_param")
        assert "must be a string" in str(exc_info.value)
    
    def test_validate_string_parameter_control_chars(self, server):
        """Test string with control characters."""
        with pytest.raises(ValidationError) as exc_info:
            server._validate_string_parameter("test\x00value", "test_param")
        assert "contains invalid control characters" in str(exc_info.value)
    
    def test_validate_integer_parameter_valid(self, server):
        """Test valid integer parameter validation."""
        result = server._validate_integer_parameter(42, "test_param")
        assert result == 42
    
    def test_validate_integer_parameter_string_conversion(self, server):
        """Test integer parameter from string conversion."""
        result = server._validate_integer_parameter("42", "test_param")
        assert result == 42
    
    def test_validate_integer_parameter_float_conversion(self, server):
        """Test integer parameter from float conversion."""
        result = server._validate_integer_parameter(42.0, "test_param")
        assert result == 42
    
    def test_validate_integer_parameter_invalid_float(self, server):
        """Test integer parameter with non-integer float."""
        with pytest.raises(ValidationError) as exc_info:
            server._validate_integer_parameter(42.5, "test_param")
        assert "must be an integer" in str(exc_info.value)
    
    def test_validate_integer_parameter_range(self, server):
        """Test integer parameter range validation."""
        with pytest.raises(ValidationError) as exc_info:
            server._validate_integer_parameter(5, "test_param", min_value=10, max_value=20)
        assert "must be at least 10" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            server._validate_integer_parameter(25, "test_param", min_value=10, max_value=20)
        assert "cannot exceed 20" in str(exc_info.value)
    
    def test_validate_float_parameter_valid(self, server):
        """Test valid float parameter validation."""
        result = server._validate_float_parameter(3.14, "test_param")
        assert result == 3.14
    
    def test_validate_float_parameter_nan(self, server):
        """Test float parameter with NaN."""
        with pytest.raises(ValidationError) as exc_info:
            server._validate_float_parameter(float('nan'), "test_param")
        assert "cannot be NaN" in str(exc_info.value)
    
    def test_validate_float_parameter_infinity(self, server):
        """Test float parameter with infinity."""
        with pytest.raises(ValidationError) as exc_info:
            server._validate_float_parameter(float('inf'), "test_param")
        assert "cannot be infinite" in str(exc_info.value)
    
    def test_validate_chunk_method_valid(self, server):
        """Test valid chunk method validation."""
        result = server._validate_chunk_method("naive")
        assert result == "naive"
    
    def test_validate_chunk_method_case_insensitive(self, server):
        """Test chunk method case insensitive validation."""
        result = server._validate_chunk_method("NAIVE")
        assert result == "naive"
    
    def test_validate_chunk_method_invalid(self, server):
        """Test invalid chunk method validation."""
        with pytest.raises(ValidationError) as exc_info:
            server._validate_chunk_method("invalid_method")
        assert "chunk_method must be one of" in str(exc_info.value)


class TestFilePathValidation:
    """Test file path validation and security."""
    
    @pytest.fixture
    def server(self):
        """Create a test server instance."""
        config = RAGFlowConfig(
            base_url="http://test.example.com",
            api_key="test_key",
            timeout=30,
            max_retries=3
        )
        return RAGFlowMCPServer(config)
    
    def test_validate_file_path_valid(self, server):
        """Test valid file path validation."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name
        
        try:
            result = server._validate_file_path(tmp_path)
            assert os.path.isabs(result)
            assert tmp_path in result
        finally:
            os.unlink(tmp_path)
    
    def test_validate_file_path_empty(self, server):
        """Test empty file path validation."""
        with pytest.raises(ValidationError) as exc_info:
            server._validate_file_path("")
        assert "must be a non-empty string" in str(exc_info.value)
    
    def test_validate_file_path_null_bytes(self, server):
        """Test file path with null bytes."""
        with pytest.raises(ValidationError) as exc_info:
            server._validate_file_path("test\x00file.txt")
        assert "contains null bytes" in str(exc_info.value)
    
    def test_validate_file_path_invalid_extension(self, server):
        """Test file path with invalid extension."""
        with pytest.raises(ValidationError) as exc_info:
            server._validate_file_path("test.exe")
        assert "Unsupported file type" in str(exc_info.value)
    
    def test_validate_file_path_no_extension(self, server):
        """Test file path without extension (should be allowed)."""
        result = server._validate_file_path("testfile")
        assert "testfile" in result


class TestToolValidation:
    """Test tool parameter validation."""
    
    @pytest.fixture
    def server(self):
        """Create a test server instance."""
        config = RAGFlowConfig(
            base_url="http://test.example.com",
            api_key="test_key",
            timeout=30,
            max_retries=3
        )
        server = RAGFlowMCPServer(config)
        server.client = Mock()
        return server
    
    @pytest.mark.asyncio
    async def test_upload_file_missing_parameters(self, server):
        """Test upload file with missing parameters."""
        # Missing file_path
        with pytest.raises(ValidationError) as exc_info:
            await server._handle_upload_file({"dataset_id": "test"})
        assert "file_path parameter is required" in str(exc_info.value)
        
        # Missing dataset_id
        with pytest.raises(ValidationError) as exc_info:
            await server._handle_upload_file({"file_path": "test.txt"})
        assert "dataset_id parameter is required" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_query_validation(self, server):
        """Test search query validation."""
        # Empty query
        with pytest.raises(ValidationError) as exc_info:
            await server._handle_search({"query": "", "dataset_id": "test"})
        assert "must be at least 1 characters long" in str(exc_info.value)
        
        # Query too long
        long_query = " ".join(["word"] * 51)  # 51 words
        with pytest.raises(ValidationError) as exc_info:
            await server._handle_search({"query": long_query, "dataset_id": "test"})
        assert "Query is too long" in str(exc_info.value)
        
        # Suspicious query patterns
        with pytest.raises(ValidationError) as exc_info:
            await server._handle_search({"query": "<script>alert('xss')</script>", "dataset_id": "test"})
        assert "potentially unsafe content" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_parameter_validation(self, server):
        """Test search parameter validation."""
        # Invalid limit
        with pytest.raises(ValidationError) as exc_info:
            await server._handle_search({
                "query": "test", 
                "dataset_id": "test", 
                "limit": 0
            })
        assert "must be at least 1" in str(exc_info.value)
        
        # Limit too high
        with pytest.raises(ValidationError) as exc_info:
            await server._handle_search({
                "query": "test", 
                "dataset_id": "test", 
                "limit": 101
            })
        assert "cannot exceed 100" in str(exc_info.value)
        
        # Invalid similarity threshold
        with pytest.raises(ValidationError) as exc_info:
            await server._handle_search({
                "query": "test", 
                "dataset_id": "test", 
                "similarity_threshold": 1.5
            })
        assert "cannot exceed 1.0" in str(exc_info.value)


class TestTimeoutHandling:
    """Test timeout handling in operations."""
    
    @pytest.fixture
    def server(self):
        """Create a test server instance."""
        config = RAGFlowConfig(
            base_url="http://test.example.com",
            api_key="test_key",
            timeout=1,  # Short timeout for testing
            max_retries=1
        )
        return RAGFlowMCPServer(config)
    
    @pytest.mark.asyncio
    async def test_tool_timeout(self, server):
        """Test tool operation timeout."""
        # Mock a slow operation
        async def slow_operation(*args, **kwargs):
            await asyncio.sleep(5)  # Longer than timeout
            return []
        
        server._handle_search = slow_operation
        
        result = await server._call_tool("ragflow_search", {"query": "test", "dataset_id": "test"})
        
        # Should return timeout error message
        assert len(result) == 1
        assert "timed out" in result[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_config_validation_timeout(self, server):
        """Test configuration validation timeout."""
        # Mock a slow client method that actually times out
        async def slow_operation():
            await asyncio.sleep(5)  # Longer than timeout
            return Mock(datasets=[])
        
        server.client.get_datasets = slow_operation
        
        with pytest.raises(ConfigurationError) as exc_info:
            await server._validate_config()
        assert "timed out" in str(exc_info.value)


class TestErrorMessageSanitization:
    """Test error message sanitization for security."""
    
    def test_sanitize_api_key(self):
        """Test API key sanitization in error messages."""
        from ragflow_mcp_server.errors import sanitize_error_message
        
        message = "Authentication failed with api_key=secret123"
        sanitized = sanitize_error_message(message)
        assert "secret123" not in sanitized
        assert "api_key=***" in sanitized
    
    def test_sanitize_token(self):
        """Test token sanitization in error messages."""
        from ragflow_mcp_server.errors import sanitize_error_message
        
        message = "Invalid token: bearer_token_12345"
        sanitized = sanitize_error_message(message)
        assert "bearer_token_12345" not in sanitized
        assert "token=***" in sanitized
    
    def test_sanitize_file_paths(self):
        """Test sensitive file path sanitization."""
        from ragflow_mcp_server.errors import sanitize_error_message
        
        message = "Cannot access /home/user/.config/secret_file"
        sanitized = sanitize_error_message(message)
        assert "/home/user/.config/secret_file" not in sanitized
        assert "/***" in sanitized
    
    def test_sanitize_urls_with_credentials(self):
        """Test URL credential sanitization."""
        from ragflow_mcp_server.errors import sanitize_error_message
        
        message = "Failed to connect to https://user:pass@example.com/api"
        sanitized = sanitize_error_message(message)
        assert "user:pass" not in sanitized
        assert "https://***:***@***" in sanitized


class TestClientValidation:
    """Test client-side validation."""
    
    @pytest.fixture
    def client(self):
        """Create a test client instance."""
        config = RAGFlowConfig(
            base_url="http://test.example.com",
            api_key="test_key",
            timeout=30,
            max_retries=3
        )
        return RAGFlowClient(config)
    
    @pytest.mark.asyncio
    async def test_upload_file_validation(self, client):
        """Test upload file parameter validation."""
        # Invalid file path type
        with pytest.raises(ValidationError) as exc_info:
            await client.upload_file(123, "dataset_id")
        assert "File path must be a non-empty string" in str(exc_info.value)
        
        # Invalid dataset ID type
        with pytest.raises(ValidationError) as exc_info:
            await client.upload_file("test.txt", None)
        assert "Dataset ID must be a non-empty string" in str(exc_info.value)
        
        # Invalid chunk method
        with pytest.raises(ValidationError) as exc_info:
            await client.upload_file("test.txt", "dataset_id", chunk_method="invalid")
        assert "Invalid chunk method" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_validation(self, client):
        """Test search parameter validation."""
        # Invalid query type
        with pytest.raises(ValidationError) as exc_info:
            await client.search(123, "dataset_id")
        assert "Query must be a non-empty string" in str(exc_info.value)
        
        # Invalid limit range
        with pytest.raises(ValidationError) as exc_info:
            await client.search("test", "dataset_id", limit=0)
        assert "Limit must be an integer between 1 and 100" in str(exc_info.value)
        
        # Invalid similarity threshold
        with pytest.raises(ValidationError) as exc_info:
            await client.search("test", "dataset_id", similarity_threshold=2.0)
        assert "Similarity threshold must be a number between 0 and 1" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__])