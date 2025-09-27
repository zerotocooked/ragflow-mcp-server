"""Unit tests for RAGFlow API client."""

import pytest
import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientConnectorError, ClientResponseError, ClientTimeout
from aiohttp.web_response import Response

from ragflow_mcp_server.client import RAGFlowClient
from ragflow_mcp_server.config import RAGFlowConfig
from ragflow_mcp_server.errors import APIError, AuthenticationError, FileError, ValidationError


@pytest.fixture
def config():
    """Create test configuration."""
    return RAGFlowConfig(
        base_url="http://localhost:9380",
        api_key="test_api_key",
        timeout=30,
        max_retries=3
    )


@pytest.fixture
def client(config):
    """Create test client."""
    return RAGFlowClient(config)


class TestRAGFlowClient:
    """Test cases for RAGFlowClient."""
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, client, config):
        """Test client initialization."""
        assert client.config == config
        assert client.session is None
    
    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test async context manager."""
        async with client as c:
            assert c.session is not None
            assert c.session.headers.get("Authorization") == "Bearer test_api_key"
            assert c.session.headers.get("Content-Type") == "application/json"
            assert c.session.headers.get("User-Agent") == "RAGFlow-MCP-Server/1.0"
        
        # Session should be closed after context exit
        assert client.session is None
    
    @pytest.mark.asyncio
    async def test_ensure_session_creates_session(self, client):
        """Test session creation."""
        await client._ensure_session()
        
        assert client.session is not None
        assert client.session.timeout.total == 30
        assert client.session.headers.get("Authorization") == "Bearer test_api_key"
    
    @pytest.mark.asyncio
    async def test_ensure_session_reuses_existing(self, client):
        """Test session reuse."""
        await client._ensure_session()
        session1 = client.session
        
        await client._ensure_session()
        session2 = client.session
        
        assert session1 is session2
        await client.close()
    
    @pytest.mark.asyncio
    async def test_close_session(self, client):
        """Test session closing."""
        await client._ensure_session()
        assert client.session is not None
        
        await client.close()
        assert client.session is None


class TestHTTPRequests:
    """Test HTTP request functionality."""
    
    @pytest.mark.asyncio
    async def test_successful_get_request(self, client):
        """Test successful GET request."""
        mock_response_data = {"status": "success", "data": "test"}
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            # Mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client._make_request("GET", "/api/test")
            
            assert result == mock_response_data
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_successful_post_request_with_json(self, client):
        """Test successful POST request with JSON data."""
        request_data = {"query": "test query"}
        mock_response_data = {"results": []}
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client._make_request("POST", "/api/search", data=request_data)
            
            assert result == mock_response_data
            # Verify JSON data was passed
            call_args = mock_request.call_args
            assert call_args[1]['json'] == request_data
    
    @pytest.mark.asyncio
    async def test_authentication_error(self, client):
        """Test authentication error handling."""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_response.text = AsyncMock(return_value='{"message": "Unauthorized"}')
            mock_request.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(AuthenticationError) as exc_info:
                await client._make_request("GET", "/api/test")
            
            assert "Invalid API key or token expired" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_api_error_with_json_response(self, client):
        """Test API error with JSON error response."""
        error_response = {"message": "Bad request", "code": "INVALID_PARAMS"}
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.text = AsyncMock(return_value=json.dumps(error_response))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(APIError) as exc_info:
                await client._make_request("GET", "/api/test")
            
            assert exc_info.value.status_code == 400
            assert "Bad request" in str(exc_info.value)
            assert exc_info.value.response_data == error_response
    
    @pytest.mark.asyncio
    async def test_api_error_with_plain_text_response(self, client):
        """Test API error with plain text response."""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value="Internal Server Error")
            mock_request.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(APIError) as exc_info:
                await client._make_request("GET", "/api/test")
            
            assert exc_info.value.status_code == 500
            assert "HTTP 500: Internal Server Error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_network_error_retry_success(self, client):
        """Test network error retry logic with eventual success."""
        mock_response_data = {"status": "success"}
        
        with patch('aiohttp.ClientSession.request') as mock_request, \
             patch('asyncio.sleep') as mock_sleep:
            
            # First call raises network error, second succeeds
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            
            # Create context manager for successful response
            success_context = AsyncMock()
            success_context.__aenter__.return_value = mock_response
            
            # Mock side effect: first call raises exception, second succeeds
            mock_request.side_effect = [
                asyncio.TimeoutError("Connection timeout"),
                success_context
            ]
            
            result = await client._make_request("GET", "/api/test")
            
            assert result == mock_response_data
            assert mock_request.call_count == 2
            mock_sleep.assert_called_once_with(1)  # First retry waits 1 second
    
    @pytest.mark.asyncio
    async def test_network_error_max_retries_exceeded(self, client):
        """Test network error when max retries exceeded."""
        with patch('aiohttp.ClientSession.request') as mock_request, \
             patch('asyncio.sleep') as mock_sleep:
            
            # All calls raise network error
            mock_request.side_effect = asyncio.TimeoutError("Connection timeout")
            
            with pytest.raises(APIError) as exc_info:
                await client._make_request("GET", "/api/test")
            
            assert "timed out" in str(exc_info.value)
            assert mock_request.call_count == 4  # Initial + 3 retries
            assert mock_sleep.call_count == 3  # 3 retry delays
    
    @pytest.mark.asyncio
    async def test_timeout_error_retry(self, client):
        """Test timeout error retry logic."""
        with patch('aiohttp.ClientSession.request') as mock_request, \
             patch('asyncio.sleep') as mock_sleep:
            
            mock_request.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(APIError) as exc_info:
                await client._make_request("GET", "/api/test")
            
            assert "timed out" in str(exc_info.value)
            assert mock_request.call_count == 4  # Initial + 3 retries
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self, client):
        """Test exponential backoff timing."""
        with patch('aiohttp.ClientSession.request') as mock_request, \
             patch('asyncio.sleep') as mock_sleep:
            
            mock_request.side_effect = asyncio.TimeoutError("Connection timeout")
            
            with pytest.raises(APIError):
                await client._make_request("GET", "/api/test")
            
            # Verify exponential backoff: 1s, 2s, 4s
            expected_delays = [1, 2, 4]
            actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
            assert actual_delays == expected_delays
    
    @pytest.mark.asyncio
    async def test_multipart_file_upload_headers(self, client):
        """Test multipart file upload removes Content-Type header."""
        files = {"file": ("test.txt", b"test content", "text/plain")}
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"status": "success"}')
            mock_request.return_value.__aenter__.return_value = mock_response
            
            await client._make_request("POST", "/api/upload", files=files)
            
            # Verify Content-Type header was removed for multipart upload
            call_args = mock_request.call_args
            headers = call_args[1].get('headers', {})
            assert 'content-type' not in {k.lower() for k in headers.keys()}
            assert call_args[1]['data'] == files
    
    @pytest.mark.asyncio
    async def test_query_parameters(self, client):
        """Test query parameters handling."""
        params = {"limit": 10, "offset": 0}
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"results": []}')
            mock_request.return_value.__aenter__.return_value = mock_response
            
            await client._make_request("GET", "/api/search", params=params)
            
            call_args = mock_request.call_args
            assert call_args[1]['params'] == params
    
    @pytest.mark.asyncio
    async def test_empty_response_handling(self, client):
        """Test handling of empty response."""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 204  # No Content
            mock_response.text = AsyncMock(return_value="")
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client._make_request("DELETE", "/api/file/123")
            
            assert result == {}
    
    @pytest.mark.asyncio
    async def test_invalid_json_response(self, client):
        """Test handling of invalid JSON response."""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="invalid json {")
            mock_request.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(APIError) as exc_info:
                await client._make_request("GET", "/api/test")
            
            assert "Invalid JSON response" in str(exc_info.value)


class TestFileUpload:
    """Test cases for file upload functionality."""
    
    @pytest.mark.asyncio
    async def test_successful_file_upload(self, client):
        """Test successful file upload."""
        # Create a temporary test file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test file content")
            temp_file_path = f.name
        
        try:
            mock_response_data = {
                "status": "success",
                "message": "File uploaded successfully",
                "data": {
                    "id": "file_123",
                    "chunk_count": 1
                }
            }
            
            with patch('aiohttp.ClientSession.request') as mock_request:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
                mock_request.return_value.__aenter__.return_value = mock_response
                
                result = await client.upload_file(temp_file_path, "dataset_123")
                
                assert result.file_id == "file_123"
                assert result.status == "success"
                assert result.chunk_count == 1
                
                # Verify multipart upload was used
                call_args = mock_request.call_args
                assert 'data' in call_args[1]
                assert 'file' in call_args[1]['data']
                
        finally:
            # Clean up temp file
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_file_not_found_error(self, client):
        """Test file not found error."""
        with pytest.raises(FileError) as exc_info:
            await client.upload_file("/nonexistent/file.txt", "dataset_123")
        
        assert "File not found" in str(exc_info.value)
        assert exc_info.value.file_path == "/nonexistent/file.txt"
    
    @pytest.mark.asyncio
    async def test_empty_file_path_validation(self, client):
        """Test validation of empty file path."""
        with pytest.raises(ValidationError) as exc_info:
            await client.upload_file("", "dataset_123")
        
        assert exc_info.value.field == "file_path"
        assert "non-empty string" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_empty_dataset_id_validation(self, client):
        """Test validation of empty dataset ID."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_file_path = f.name
        
        try:
            with pytest.raises(ValidationError) as exc_info:
                await client.upload_file(temp_file_path, "")
            
            assert exc_info.value.field == "dataset_id"
            assert "non-empty string" in str(exc_info.value)
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_unsupported_file_type(self, client):
        """Test unsupported file type error."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.exe', delete=False) as f:
            f.write("Binary content")
            temp_file_path = f.name
        
        try:
            with pytest.raises(FileError) as exc_info:
                await client.upload_file(temp_file_path, "dataset_123")
            
            assert "Unsupported file type" in str(exc_info.value)
            assert ".exe" in str(exc_info.value)
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_empty_file_error(self, client):
        """Test empty file error."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            # Create empty file
            temp_file_path = f.name
        
        try:
            with pytest.raises(FileError) as exc_info:
                await client.upload_file(temp_file_path, "dataset_123")
            
            assert "File is empty" in str(exc_info.value)
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_file_too_large_error(self, client):
        """Test file too large error."""
        import tempfile
        
        # Mock os.path.getsize to return a large size
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_file_path = f.name
        
        try:
            with patch('os.path.getsize', return_value=200 * 1024 * 1024):  # 200MB
                with pytest.raises(FileError) as exc_info:
                    await client.upload_file(temp_file_path, "dataset_123")
                
                assert "File too large" in str(exc_info.value)
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_progress_callback(self, client):
        """Test progress callback functionality."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test file content")
            temp_file_path = f.name
        
        try:
            mock_response_data = {
                "status": "success",
                "data": {"id": "file_123"}
            }
            
            progress_calls = []
            def progress_callback(current, total, message):
                progress_calls.append((current, total, message))
            
            with patch('aiohttp.ClientSession.request') as mock_request:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
                mock_request.return_value.__aenter__.return_value = mock_response
                
                await client.upload_file(temp_file_path, "dataset_123", progress_callback=progress_callback)
                
                # Verify progress callbacks were called
                assert len(progress_calls) == 2
                assert progress_calls[0][2] == "Starting upload..."
                assert progress_calls[1][2] == "Upload completed"
                
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_api_error_during_upload(self, client):
        """Test API error during upload."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_file_path = f.name
        
        try:
            with patch('aiohttp.ClientSession.request') as mock_request:
                mock_response = AsyncMock()
                mock_response.status = 400
                mock_response.text = AsyncMock(return_value='{"message": "Invalid dataset"}')
                mock_request.return_value.__aenter__.return_value = mock_response
                
                with pytest.raises(APIError) as exc_info:
                    await client.upload_file(temp_file_path, "invalid_dataset")
                
                assert exc_info.value.status_code == 400
                assert "Invalid dataset" in str(exc_info.value)
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_missing_file_id_in_response(self, client):
        """Test error when file ID is missing from response."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_file_path = f.name
        
        try:
            mock_response_data = {
                "status": "success",
                "message": "Upload completed",
                # Missing file ID
            }
            
            with patch('aiohttp.ClientSession.request') as mock_request:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
                mock_request.return_value.__aenter__.return_value = mock_response
                
                with pytest.raises(APIError) as exc_info:
                    await client.upload_file(temp_file_path, "dataset_123")
                
                assert "No file ID returned" in str(exc_info.value)
        finally:
            os.unlink(temp_file_path)
    
    def test_get_content_type(self, client):
        """Test content type detection."""
        assert client._get_content_type('.txt') == 'text/plain'
        assert client._get_content_type('.pdf') == 'application/pdf'
        assert client._get_content_type('.doc') == 'application/msword'
        assert client._get_content_type('.docx') == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        assert client._get_content_type('.md') == 'text/markdown'
        assert client._get_content_type('.html') == 'text/html'
        assert client._get_content_type('.csv') == 'text/csv'
        assert client._get_content_type('.json') == 'application/json'
        assert client._get_content_type('.unknown') == 'application/octet-stream'


class TestFileUpdate:
    """Test cases for file update functionality."""
    
    @pytest.mark.asyncio
    async def test_successful_file_update(self, client):
        """Test successful file update."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Updated file content")
            temp_file_path = f.name
        
        try:
            # Mock file status check
            status_response = {
                "data": {
                    "status": "completed",
                    "chunk_count": 1
                }
            }
            
            # Mock update response
            update_response = {
                "status": "success",
                "message": "File updated successfully",
                "data": {
                    "chunk_count": 2
                }
            }
            
            # Mock re-embedding response
            reembed_response = {"status": "success"}
            
            with patch('aiohttp.ClientSession.request') as mock_request:
                mock_response = AsyncMock()
                mock_response.status = 200
                
                # Set up different responses for different endpoints
                def mock_text_side_effect():
                    call_args = mock_request.call_args
                    if 'status' in call_args[0][1]:  # GET status endpoint
                        return json.dumps(status_response)
                    elif 'reembed' in call_args[0][1]:  # POST reembed endpoint
                        return json.dumps(reembed_response)
                    else:  # PUT update endpoint
                        return json.dumps(update_response)
                
                mock_response.text = AsyncMock(side_effect=mock_text_side_effect)
                mock_request.return_value.__aenter__.return_value = mock_response
                
                result = await client.update_file("file_123", temp_file_path)
                
                assert result.file_id == "file_123"
                assert result.status == "success"
                assert result.chunk_count == 2
                
                # Verify all three API calls were made
                assert mock_request.call_count == 3  # status check, update, re-embed
                
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_file_not_found_in_ragflow(self, client):
        """Test error when file ID doesn't exist in RAGFlow."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_file_path = f.name
        
        try:
            with patch('aiohttp.ClientSession.request') as mock_request:
                mock_response = AsyncMock()
                mock_response.status = 404
                mock_response.text = AsyncMock(return_value='{"message": "File not found"}')
                mock_request.return_value.__aenter__.return_value = mock_response
                
                with pytest.raises(FileError) as exc_info:
                    await client.update_file("nonexistent_file", temp_file_path)
                
                assert "File with ID nonexistent_file not found" in str(exc_info.value)
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_empty_file_id_validation(self, client):
        """Test validation of empty file ID."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_file_path = f.name
        
        try:
            with pytest.raises(ValidationError) as exc_info:
                await client.update_file("", temp_file_path)
            
            assert exc_info.value.field == "file_id"
            assert "non-empty string" in str(exc_info.value)
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_update_with_progress_callback(self, client):
        """Test file update with progress callback."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Updated content")
            temp_file_path = f.name
        
        try:
            progress_calls = []
            def progress_callback(current, total, message):
                progress_calls.append((current, total, message))
            
            # Mock responses
            status_response = {"data": {"status": "completed"}}
            update_response = {"status": "success", "data": {"chunk_count": 1}}
            reembed_response = {"status": "success"}
            
            with patch('aiohttp.ClientSession.request') as mock_request:
                mock_response = AsyncMock()
                mock_response.status = 200
                
                def mock_text_side_effect():
                    call_args = mock_request.call_args
                    if 'status' in call_args[0][1]:
                        return json.dumps(status_response)
                    elif 'reembed' in call_args[0][1]:
                        return json.dumps(reembed_response)
                    else:
                        return json.dumps(update_response)
                
                mock_response.text = AsyncMock(side_effect=mock_text_side_effect)
                mock_request.return_value.__aenter__.return_value = mock_response
                
                await client.update_file("file_123", temp_file_path, progress_callback=progress_callback)
                
                # Verify progress callbacks were called
                assert len(progress_calls) == 2
                assert progress_calls[0][2] == "Starting update..."
                assert progress_calls[1][2] == "Update completed"
                
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_reembedding_failure_warning(self, client):
        """Test that re-embedding failure doesn't fail the update."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Updated content")
            temp_file_path = f.name
        
        try:
            status_response = {"data": {"status": "completed"}}
            update_response = {"status": "success", "data": {"chunk_count": 1}}
            
            with patch('aiohttp.ClientSession.request') as mock_request:
                mock_response = AsyncMock()
                
                def mock_status_and_text():
                    call_args = mock_request.call_args
                    if 'status' in call_args[0][1]:
                        mock_response.status = 200
                        return json.dumps(status_response)
                    elif 'reembed' in call_args[0][1]:
                        mock_response.status = 500  # Re-embedding fails
                        return '{"message": "Internal server error"}'
                    else:
                        mock_response.status = 200
                        return json.dumps(update_response)
                
                mock_response.text = AsyncMock(side_effect=mock_status_and_text)
                mock_request.return_value.__aenter__.return_value = mock_response
                
                # Update should succeed despite re-embedding failure
                result = await client.update_file("file_123", temp_file_path)
                assert result.status == "success"
                
        finally:
            os.unlink(temp_file_path)


class TestFileStatus:
    """Test cases for file status functionality."""
    
    @pytest.mark.asyncio
    async def test_get_file_status_success(self, client):
        """Test successful file status retrieval."""
        mock_response_data = {
            "data": {
                "status": "processing",
                "progress": 0.5,
                "chunk_count": 3
            }
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client.get_file_status("file_123")
            
            assert result.file_id == "file_123"
            assert result.status == "processing"
            assert result.progress == 0.5
            assert result.chunk_count == 3
            assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_get_file_status_with_error(self, client):
        """Test file status with error message."""
        mock_response_data = {
            "data": {
                "status": "failed",
                "error_message": "Processing failed due to invalid format"
            }
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client.get_file_status("file_123")
            
            assert result.status == "failed"
            assert result.error_message == "Processing failed due to invalid format"
    
    @pytest.mark.asyncio
    async def test_get_file_status_empty_file_id(self, client):
        """Test validation of empty file ID."""
        with pytest.raises(ValidationError) as exc_info:
            await client.get_file_status("")
        
        assert exc_info.value.field == "file_id"
        assert "non-empty string" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_file_status_not_found(self, client):
        """Test file status for non-existent file."""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_response.text = AsyncMock(return_value='{"message": "File not found"}')
            mock_request.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(APIError) as exc_info:
                await client.get_file_status("nonexistent_file")
            
            assert exc_info.value.status_code == 404


class TestSearch:
    """Test cases for search functionality."""
    
    @pytest.mark.asyncio
    async def test_successful_search(self, client):
        """Test successful search operation."""
        mock_response_data = {
            "data": {
                "results": [
                    {
                        "content": "This is the first search result",
                        "score": 0.95,
                        "file_name": "document1.txt",
                        "file_id": "file_123",
                        "chunk_id": "chunk_1"
                    },
                    {
                        "content": "This is the second search result",
                        "score": 0.85,
                        "file_name": "document2.txt",
                        "file_id": "file_456",
                        "chunk_id": "chunk_2"
                    }
                ],
                "total": 2
            }
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client.search("test query", "dataset_123")
            
            assert len(result.results) == 2
            assert result.total_count == 2
            assert result.query_time > 0
            
            # Check first result
            first_result = result.results[0]
            assert first_result.content == "This is the first search result"
            assert first_result.score == 0.95
            assert first_result.file_name == "document1.txt"
            assert first_result.file_id == "file_123"
            assert first_result.chunk_id == "chunk_1"
            
            # Verify request was made correctly
            call_args = mock_request.call_args
            assert call_args[0][0] == "POST"
            assert "/api/v1/dataset/search" in call_args[0][1]
            
            # Check request data
            request_data = call_args[1]['json']
            assert request_data['query'] == "test query"
            assert request_data['dataset_id'] == "dataset_123"
            assert request_data['limit'] == 10
            assert request_data['similarity_threshold'] == 0.1
    
    @pytest.mark.asyncio
    async def test_search_with_custom_parameters(self, client):
        """Test search with custom parameters."""
        mock_response_data = {
            "data": {
                "results": [
                    {
                        "content": "High relevance result",
                        "score": 0.9,
                        "file_name": "doc.txt",
                        "file_id": "file_1",
                        "chunk_id": "chunk_1"
                    }
                ]
            }
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client.search(
                query="specific query",
                dataset_id="dataset_456",
                limit=5,
                similarity_threshold=0.8,
                offset=10
            )
            
            assert len(result.results) == 1
            
            # Verify custom parameters were sent
            call_args = mock_request.call_args
            request_data = call_args[1]['json']
            assert request_data['limit'] == 5
            assert request_data['similarity_threshold'] == 0.8
            assert request_data['offset'] == 10
    
    @pytest.mark.asyncio
    async def test_search_with_similarity_filtering(self, client):
        """Test search results are filtered by similarity threshold."""
        mock_response_data = {
            "data": {
                "results": [
                    {
                        "content": "High relevance result",
                        "score": 0.9,
                        "file_name": "doc1.txt",
                        "file_id": "file_1",
                        "chunk_id": "chunk_1"
                    },
                    {
                        "content": "Low relevance result",
                        "score": 0.3,
                        "file_name": "doc2.txt",
                        "file_id": "file_2",
                        "chunk_id": "chunk_2"
                    }
                ]
            }
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            # Search with high similarity threshold
            result = await client.search("test query", "dataset_123", similarity_threshold=0.5)
            
            # Only high relevance result should be returned
            assert len(result.results) == 1
            assert result.results[0].score == 0.9
    
    @pytest.mark.asyncio
    async def test_search_results_sorted_by_score(self, client):
        """Test search results are sorted by score in descending order."""
        mock_response_data = {
            "data": {
                "results": [
                    {
                        "content": "Medium relevance",
                        "score": 0.7,
                        "file_name": "doc1.txt",
                        "file_id": "file_1",
                        "chunk_id": "chunk_1"
                    },
                    {
                        "content": "High relevance",
                        "score": 0.9,
                        "file_name": "doc2.txt",
                        "file_id": "file_2",
                        "chunk_id": "chunk_2"
                    },
                    {
                        "content": "Low relevance",
                        "score": 0.5,
                        "file_name": "doc3.txt",
                        "file_id": "file_3",
                        "chunk_id": "chunk_3"
                    }
                ]
            }
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client.search("test query", "dataset_123")
            
            # Results should be sorted by score (highest first)
            assert len(result.results) == 3
            assert result.results[0].score == 0.9
            assert result.results[1].score == 0.7
            assert result.results[2].score == 0.5
    
    @pytest.mark.asyncio
    async def test_search_empty_results(self, client):
        """Test search with no results."""
        mock_response_data = {
            "data": {
                "results": [],
                "total": 0
            }
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client.search("nonexistent query", "dataset_123")
            
            assert len(result.results) == 0
            assert result.total_count == 0
            assert result.query_time > 0
    
    @pytest.mark.asyncio
    async def test_search_empty_query_validation(self, client):
        """Test validation of empty query."""
        with pytest.raises(ValidationError) as exc_info:
            await client.search("", "dataset_123")
        
        assert exc_info.value.field == "query"
        assert "non-empty string" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_empty_dataset_id_validation(self, client):
        """Test validation of empty dataset ID."""
        with pytest.raises(ValidationError) as exc_info:
            await client.search("test query", "")
        
        assert exc_info.value.field == "dataset_id"
        assert "non-empty string" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_invalid_limit_validation(self, client):
        """Test validation of invalid limit."""
        with pytest.raises(ValidationError) as exc_info:
            await client.search("test query", "dataset_123", limit=0)
        
        assert exc_info.value.field == "limit"
        assert "between 1 and 100" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            await client.search("test query", "dataset_123", limit=101)
        
        assert exc_info.value.field == "limit"
        assert "between 1 and 100" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_invalid_similarity_threshold_validation(self, client):
        """Test validation of invalid similarity threshold."""
        with pytest.raises(ValidationError) as exc_info:
            await client.search("test query", "dataset_123", similarity_threshold=-0.1)
        
        assert exc_info.value.field == "similarity_threshold"
        assert "between 0 and 1" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            await client.search("test query", "dataset_123", similarity_threshold=1.1)
        
        assert exc_info.value.field == "similarity_threshold"
        assert "between 0 and 1" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_invalid_offset_validation(self, client):
        """Test validation of invalid offset."""
        with pytest.raises(ValidationError) as exc_info:
            await client.search("test query", "dataset_123", offset=-1)
        
        assert exc_info.value.field == "offset"
        assert "non-negative integer" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_api_error(self, client):
        """Test search API error handling."""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.text = AsyncMock(return_value='{"message": "Invalid dataset"}')
            mock_request.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(APIError) as exc_info:
                await client.search("test query", "invalid_dataset")
            
            assert exc_info.value.status_code == 400
            assert "Invalid dataset" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_alternative_response_format(self, client):
        """Test search with alternative response format."""
        # Some APIs might return results in different format
        mock_response_data = {
            "chunks": [
                {
                    "text": "Alternative format result",
                    "similarity": 0.8,
                    "filename": "alt_doc.txt",
                    "document_id": "alt_file_1",
                    "id": "alt_chunk_1"
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client.search("test query", "dataset_123")
            
            assert len(result.results) == 1
            assert result.results[0].content == "Alternative format result"
            assert result.results[0].score == 0.8
            assert result.results[0].file_name == "alt_doc.txt"
            assert result.results[0].file_id == "alt_file_1"
            assert result.results[0].chunk_id == "alt_chunk_1"
    
    @pytest.mark.asyncio
    async def test_search_with_additional_kwargs(self, client):
        """Test search with additional keyword arguments."""
        mock_response_data = {"data": {"results": []}}
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            await client.search(
                "test query", 
                "dataset_123", 
                custom_param="custom_value",
                another_param=42
            )
            
            # Verify additional parameters were included
            call_args = mock_request.call_args
            request_data = call_args[1]['json']
            assert request_data['custom_param'] == "custom_value"
            assert request_data['another_param'] == 42


class TestFileManagement:
    """Test cases for file management operations."""
    
    @pytest.mark.asyncio
    async def test_list_files_success(self, client):
        """Test successful file listing."""
        mock_response_data = {
            "data": {
                "files": [
                    {
                        "id": "file_123",
                        "name": "document1.txt",
                        "size": 1024,
                        "status": "completed",
                        "chunk_count": 5,
                        "created_at": "2024-01-01T10:00:00Z"
                    },
                    {
                        "id": "file_456",
                        "name": "document2.pdf",
                        "size": 2048,
                        "status": "processing",
                        "chunk_count": 0,
                        "created_at": "2024-01-02T11:00:00Z"
                    }
                ],
                "total": 2
            }
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client.list_files("dataset_123")
            
            assert len(result.files) == 2
            assert result.total_count == 2
            
            # Check first file
            first_file = result.files[0]
            assert first_file.file_id == "file_123"
            assert first_file.name == "document1.txt"
            assert first_file.size == 1024
            assert first_file.status == "completed"
            assert first_file.chunk_count == 5
            
            # Verify request parameters
            call_args = mock_request.call_args
            params = call_args[1]['params']
            assert params['dataset_id'] == "dataset_123"
            assert params['limit'] == 100
            assert params['offset'] == 0
    
    @pytest.mark.asyncio
    async def test_list_files_with_pagination(self, client):
        """Test file listing with pagination parameters."""
        mock_response_data = {"data": {"files": [], "total": 0}}
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            await client.list_files("dataset_123", limit=50, offset=10)
            
            # Verify pagination parameters
            call_args = mock_request.call_args
            params = call_args[1]['params']
            assert params['limit'] == 50
            assert params['offset'] == 10
    
    @pytest.mark.asyncio
    async def test_list_files_empty_dataset_id(self, client):
        """Test validation of empty dataset ID."""
        with pytest.raises(ValidationError) as exc_info:
            await client.list_files("")
        
        assert exc_info.value.field == "dataset_id"
        assert "non-empty string" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_files_invalid_limit(self, client):
        """Test validation of invalid limit."""
        with pytest.raises(ValidationError) as exc_info:
            await client.list_files("dataset_123", limit=0)
        
        assert exc_info.value.field == "limit"
        assert "between 1 and 1000" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_delete_file_success(self, client):
        """Test successful file deletion."""
        mock_response_data = {
            "status": "success",
            "message": "File deleted successfully"
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client.delete_file("file_123", confirm=True)
            
            assert result.file_id == "file_123"
            assert result.status == "success"
            assert "deleted successfully" in result.message
            
            # Verify DELETE request was made
            call_args = mock_request.call_args
            assert call_args[0][0] == "DELETE"
            assert "file_123" in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, client):
        """Test file deletion when file doesn't exist."""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_response.text = AsyncMock(return_value='{"message": "File not found"}')
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client.delete_file("nonexistent_file", confirm=True)
            
            assert result.file_id == "nonexistent_file"
            assert result.status == "not_found"
            assert "not found" in result.message
    
    @pytest.mark.asyncio
    async def test_delete_file_without_confirmation(self, client):
        """Test file deletion without confirmation."""
        with pytest.raises(ValidationError) as exc_info:
            await client.delete_file("file_123", confirm=False)
        
        assert exc_info.value.field == "confirm"
        assert "must be confirmed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_delete_file_empty_file_id(self, client):
        """Test validation of empty file ID."""
        with pytest.raises(ValidationError) as exc_info:
            await client.delete_file("", confirm=True)
        
        assert exc_info.value.field == "file_id"
        assert "non-empty string" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_datasets_success(self, client):
        """Test successful dataset listing."""
        mock_response_data = {
            "data": {
                "datasets": [
                    {
                        "id": "dataset_123",
                        "name": "My Dataset",
                        "description": "A test dataset",
                        "file_count": 10,
                        "created_at": "2024-01-01T10:00:00Z"
                    },
                    {
                        "id": "dataset_456",
                        "name": "Another Dataset",
                        "description": None,
                        "file_count": 5,
                        "created_at": "2024-01-02T11:00:00Z"
                    }
                ],
                "total": 2
            }
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client.get_datasets()
            
            assert len(result.datasets) == 2
            assert result.total_count == 2
            
            # Check first dataset
            first_dataset = result.datasets[0]
            assert first_dataset.dataset_id == "dataset_123"
            assert first_dataset.name == "My Dataset"
            assert first_dataset.description == "A test dataset"
            assert first_dataset.file_count == 10
            
            # Verify request was made correctly
            call_args = mock_request.call_args
            assert call_args[0][0] == "GET"
            assert "/api/v1/datasets" in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_get_datasets_with_pagination(self, client):
        """Test dataset listing with pagination."""
        mock_response_data = {"data": {"datasets": [], "total": 0}}
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            await client.get_datasets(limit=25, offset=5)
            
            # Verify pagination parameters
            call_args = mock_request.call_args
            params = call_args[1]['params']
            assert params['limit'] == 25
            assert params['offset'] == 5
    
    @pytest.mark.asyncio
    async def test_get_datasets_invalid_limit(self, client):
        """Test validation of invalid limit for datasets."""
        with pytest.raises(ValidationError) as exc_info:
            await client.get_datasets(limit=0)
        
        assert exc_info.value.field == "limit"
        assert "between 1 and 1000" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_datasets_invalid_offset(self, client):
        """Test validation of invalid offset for datasets."""
        with pytest.raises(ValidationError) as exc_info:
            await client.get_datasets(offset=-1)
        
        assert exc_info.value.field == "offset"
        assert "non-negative integer" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_files_alternative_response_format(self, client):
        """Test file listing with alternative response format."""
        mock_response_data = {
            "documents": [
                {
                    "file_id": "alt_file_1",
                    "filename": "alt_doc.txt",
                    "file_size": 512,
                    "status": "completed",
                    "chunks": 3,
                    "upload_time": "1704110400"  # Timestamp format
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client.list_files("dataset_123")
            
            assert len(result.files) == 1
            file_info = result.files[0]
            assert file_info.file_id == "alt_file_1"
            assert file_info.name == "alt_doc.txt"
            assert file_info.size == 512
            assert file_info.chunk_count == 3
    
    @pytest.mark.asyncio
    async def test_get_datasets_alternative_response_format(self, client):
        """Test dataset listing with alternative response format."""
        mock_response_data = {
            "items": [
                {
                    "dataset_id": "alt_dataset_1",
                    "title": "Alternative Dataset",
                    "desc": "Alternative description",
                    "document_count": 15,
                    "create_time": "1704110400"  # Timestamp format
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_request.return_value.__aenter__.return_value = mock_response
            
            result = await client.get_datasets()
            
            assert len(result.datasets) == 1
            dataset = result.datasets[0]
            assert dataset.dataset_id == "alt_dataset_1"
            assert dataset.name == "Alternative Dataset"
            assert dataset.description == "Alternative description"
            assert dataset.file_count == 15