"""Unit tests for comprehensive error scenarios and edge cases."""

import pytest
import os
import tempfile
import asyncio
from unittest.mock import Mock, patch, AsyncMock, mock_open
from pathlib import Path

from ragflow_mcp_server.server import RAGFlowMCPServer
from ragflow_mcp_server.config import RAGFlowConfig
from ragflow_mcp_server.errors import ValidationError, FileError, APIError, AuthenticationError
from ragflow_mcp_server.client import RAGFlowClient


class TestFileErrorScenarios:
    """Test various file error scenarios."""
    
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
    async def test_upload_file_not_found(self, server):
        """Test upload with non-existent file."""
        with pytest.raises(FileError) as exc_info:
            await server._handle_upload_file({
                "file_path": "/nonexistent/file.txt",
                "dataset_id": "test"
            })
        assert "File not found" in str(exc_info.value)
        assert exc_info.value.file_path is not None
    
    @pytest.mark.asyncio
    async def test_upload_directory_instead_of_file(self, server):
        """Test upload with directory path instead of file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with pytest.raises(FileError) as exc_info:
                await server._handle_upload_file({
                    "file_path": tmp_dir,
                    "dataset_id": "test"
                })
            assert "Path is not a file" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_upload_unreadable_file(self, server):
        """Test upload with unreadable file."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name
        
        try:
            # Make file unreadable (on Windows, this might not work as expected)
            try:
                os.chmod(tmp_path, 0o000)
                # Check if the file is actually unreadable
                if os.access(tmp_path, os.R_OK):
                    # On Windows, chmod might not work as expected, skip this test
                    pytest.skip("Cannot make file unreadable on this platform")
            except (OSError, PermissionError):
                pytest.skip("Cannot change file permissions on this platform")
            
            with pytest.raises(FileError) as exc_info:
                await server._handle_upload_file({
                    "file_path": tmp_path,
                    "dataset_id": "test"
                })
            assert "not readable" in str(exc_info.value)
        finally:
            # Restore permissions and cleanup
            try:
                os.chmod(tmp_path, 0o644)
                os.unlink(tmp_path)
            except (OSError, PermissionError):
                pass  # Ignore cleanup errors
    
    @pytest.mark.asyncio
    async def test_upload_empty_file(self, server):
        """Test upload with empty file."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp_path = tmp.name  # Empty file
        
        try:
            with pytest.raises(FileError) as exc_info:
                await server._handle_upload_file({
                    "file_path": tmp_path,
                    "dataset_id": "test"
                })
            assert "File is empty" in str(exc_info.value)
        finally:
            os.unlink(tmp_path)
    
    @pytest.mark.asyncio
    async def test_upload_oversized_file(self, server):
        """Test upload with file that's too large."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            # Create a file larger than 100MB (mocked)
            tmp_path = tmp.name
        
        try:
            with patch('os.path.getsize', return_value=101 * 1024 * 1024):  # 101MB
                with pytest.raises(FileError) as exc_info:
                    await server._handle_upload_file({
                        "file_path": tmp_path,
                        "dataset_id": "test"
                    })
                assert "File too large" in str(exc_info.value)
        finally:
            os.unlink(tmp_path)


class TestNetworkErrorScenarios:
    """Test network-related error scenarios."""
    
    @pytest.fixture
    def client(self):
        """Create a test client instance."""
        config = RAGFlowConfig(
            base_url="http://test.example.com",
            api_key="test_key",
            timeout=1,  # Short timeout for testing
            max_retries=2
        )
        return RAGFlowClient(config)
    
    @pytest.mark.asyncio
    async def test_connection_timeout(self, client):
        """Test connection timeout handling."""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_request.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(APIError) as exc_info:
                await client._make_request("GET", "/test")
            
            assert "timed out" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_connection_error_with_retries(self, client):
        """Test connection error with retry logic."""
        from aiohttp import ClientConnectorError
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_request.side_effect = ClientConnectorError(
                connection_key=Mock(), os_error=OSError("Connection refused")
            )
            
            with pytest.raises(APIError) as exc_info:
                await client._make_request("GET", "/test")
            
            # Should have retried max_retries times
            assert mock_request.call_count == client.config.max_retries + 1
            assert "connection" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_http_error_codes(self, client):
        """Test various HTTP error code handling."""
        from aiohttp import ClientResponseError
        
        # Test 401 Unauthorized
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = Mock()
            mock_response.status = 401
            mock_response.text = AsyncMock(return_value='{"message": "Unauthorized"}')
            mock_request.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(AuthenticationError):
                await client._make_request("GET", "/test")
        
        # Test 404 Not Found
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = Mock()
            mock_response.status = 404
            mock_response.text = AsyncMock(return_value='{"message": "Not found"}')
            mock_request.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(APIError) as exc_info:
                await client._make_request("GET", "/test")
            assert exc_info.value.status_code == 404
        
        # Test 500 Internal Server Error
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = Mock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value='{"message": "Internal error"}')
            mock_request.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(APIError) as exc_info:
                await client._make_request("GET", "/test")
            assert exc_info.value.status_code == 500


class TestEdgeCaseValidation:
    """Test edge cases in validation."""
    
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
    
    def test_validate_string_with_unicode(self, server):
        """Test string validation with Unicode characters."""
        # Valid Unicode
        result = server._validate_string_parameter("测试文本", "test_param")
        assert result == "测试文本"
        
        # Emoji
        result = server._validate_string_parameter("test 🚀 emoji", "test_param")
        assert result == "test 🚀 emoji"
    
    def test_validate_string_with_whitespace(self, server):
        """Test string validation with various whitespace."""
        # Leading/trailing whitespace should be stripped
        result = server._validate_string_parameter("  test  ", "test_param")
        assert result == "test"
        
        # Only whitespace should fail
        with pytest.raises(ValidationError):
            server._validate_string_parameter("   ", "test_param")
    
    def test_validate_integer_edge_cases(self, server):
        """Test integer validation edge cases."""
        # Very large integer
        result = server._validate_integer_parameter(2**31 - 1, "test_param")
        assert result == 2**31 - 1
        
        # Negative integer
        result = server._validate_integer_parameter(-42, "test_param")
        assert result == -42
        
        # Zero
        result = server._validate_integer_parameter(0, "test_param", min_value=0)
        assert result == 0
    
    def test_validate_float_edge_cases(self, server):
        """Test float validation edge cases."""
        # Very small float
        result = server._validate_float_parameter(1e-10, "test_param")
        assert result == 1e-10
        
        # Very large float
        result = server._validate_float_parameter(1e10, "test_param")
        assert result == 1e10
        
        # Negative zero
        result = server._validate_float_parameter(-0.0, "test_param")
        assert result == -0.0
    
    def test_file_path_edge_cases(self, server):
        """Test file path validation edge cases."""
        # Path with spaces
        with tempfile.NamedTemporaryFile(suffix='.txt', prefix='test file ', delete=False) as tmp:
            tmp.write(b"content")
            tmp_path = tmp.name
        
        try:
            result = server._validate_file_path(tmp_path)
            assert os.path.isabs(result)
        finally:
            os.unlink(tmp_path)
        
        # Path with special characters (but safe)
        with tempfile.NamedTemporaryFile(suffix='.txt', prefix='test-file_123.', delete=False) as tmp:
            tmp.write(b"content")
            tmp_path = tmp.name
        
        try:
            result = server._validate_file_path(tmp_path)
            assert os.path.isabs(result)
        finally:
            os.unlink(tmp_path)


class TestConcurrentOperations:
    """Test concurrent operation handling."""
    
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
    async def test_concurrent_tool_calls(self, server):
        """Test handling multiple concurrent tool calls."""
        # Mock successful operations
        server.client.get_datasets = AsyncMock(return_value=Mock(datasets=[]))
        
        # Create multiple concurrent calls
        tasks = []
        for i in range(5):
            task = server._call_tool("ragflow_get_datasets", {})
            tasks.append(task)
        
        # All should complete successfully
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            assert not isinstance(result, Exception)
            assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_validation_errors(self, server):
        """Test handling concurrent validation errors."""
        # Create multiple concurrent calls with invalid parameters
        tasks = []
        for i in range(3):
            task = server._call_tool("ragflow_search", {"query": "", "dataset_id": "test"})
            tasks.append(task)
        
        # All should return error messages (not raise exceptions)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            assert not isinstance(result, Exception)
            assert len(result) == 1
            assert "error" in result[0].text.lower()


class TestMemoryAndResourceHandling:
    """Test memory and resource handling in error scenarios."""
    
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
    async def test_large_response_handling(self, client):
        """Test handling of very large API responses."""
        # Mock a very large response
        large_response = '{"data": "' + 'x' * (10 * 1024 * 1024) + '"}'  # 10MB response
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=large_response)
            mock_request.return_value.__aenter__.return_value = mock_response
            
            # Should handle large response without memory issues
            result = await client._make_request("GET", "/test")
            assert "data" in result
    
    @pytest.mark.asyncio
    async def test_malformed_json_response(self, client):
        """Test handling of malformed JSON responses."""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"invalid": json}')  # Malformed JSON
            mock_request.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(APIError) as exc_info:
                await client._make_request("GET", "/test")
            assert "Invalid JSON response" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_empty_response_handling(self, client):
        """Test handling of empty responses."""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='')  # Empty response
            mock_request.return_value.__aenter__.return_value = mock_response
            
            # Should handle empty response gracefully
            result = await client._make_request("GET", "/test")
            assert result == {}


if __name__ == "__main__":
    pytest.main([__file__])