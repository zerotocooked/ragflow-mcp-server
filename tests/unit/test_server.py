"""Unit tests for RAGFlow MCP server."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from ragflow_mcp_server.server import RAGFlowMCPServer
from ragflow_mcp_server.config import RAGFlowConfig
from ragflow_mcp_server.errors import ConfigurationError, APIError, ValidationError
from ragflow_mcp_server.models import (
    UploadResult, UpdateResult, SearchResult, SearchItem, 
    ListFilesResult, FileInfo, DeleteResult, DatasetsResult, DatasetInfo
)


@pytest.fixture
def config():
    """Create test configuration."""
    return RAGFlowConfig(
        base_url="http://test.ragflow.com",
        api_key="test_key",
        default_dataset_id="test_dataset",
        timeout=30,
        max_retries=3
    )


@pytest.fixture
def mock_client():
    """Create mock RAGFlow client."""
    client = AsyncMock()
    return client


@pytest.fixture
def server(config, mock_client):
    """Create test server with mocked client."""
    with patch('ragflow_mcp_server.server.RAGFlowClient', return_value=mock_client):
        server = RAGFlowMCPServer(config)
        server.client = mock_client
        return server


class TestRAGFlowMCPServer:
    """Test RAGFlow MCP server implementation."""
    
    def test_init(self, config):
        """Test server initialization."""
        with patch('ragflow_mcp_server.server.RAGFlowClient') as mock_client_class:
            server = RAGFlowMCPServer(config)
            
            assert server.config == config
            mock_client_class.assert_called_once_with(config)
            assert server.server is not None
    
    @pytest.mark.asyncio
    async def test_validate_config_success(self, server, mock_client):
        """Test successful configuration validation."""
        mock_client.get_datasets.return_value = DatasetsResult(datasets=[], total_count=0)
        
        # Should not raise exception
        await server._validate_config()
        mock_client.get_datasets.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_config_failure(self, server, mock_client):
        """Test configuration validation failure."""
        mock_client.get_datasets.side_effect = Exception("Connection failed")
        
        with pytest.raises(ConfigurationError, match="Cannot connect to RAGFlow API"):
            await server._validate_config()
    
    @pytest.mark.asyncio
    async def test_list_tools(self, server):
        """Test listing available tools."""
        tools = await server._list_tools()
        
        assert len(tools) == 6
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "ragflow_upload_file",
            "ragflow_update_file", 
            "ragflow_search",
            "ragflow_list_files",
            "ragflow_delete_file",
            "ragflow_get_datasets"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
        
        # Check tool schemas
        upload_tool = next(tool for tool in tools if tool.name == "ragflow_upload_file")
        assert "file_path" in upload_tool.inputSchema["properties"]
        assert "dataset_id" in upload_tool.inputSchema["properties"]
        assert upload_tool.inputSchema["required"] == ["file_path", "dataset_id"]
    
    @pytest.mark.asyncio
    async def test_call_tool_unknown(self, server):
        """Test calling unknown tool."""
        result = await server._call_tool("unknown_tool", {})
        
        assert len(result) == 1
        assert "Unknown tool: unknown_tool" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handle_upload_file_success(self, server, mock_client):
        """Test successful file upload."""
        import tempfile
        import os
        
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("test content")
            temp_file_path = tmp.name
        
        try:
            mock_result = UploadResult(
                file_id="file123",
                status="success",
                message="File uploaded",
                chunk_count=5
            )
            mock_client.upload_file.return_value = mock_result
            
            arguments = {
                "file_path": temp_file_path,
                "dataset_id": "dataset123",
                "chunk_method": "naive"
            }
            
            result = await server._handle_upload_file(arguments)
            
            assert len(result) == 1
            response_text = result[0].text
            assert "File uploaded successfully!" in response_text
            assert "file123" in response_text
            assert "Chunks created: 5" in response_text
            
            mock_client.upload_file.assert_called_once()
            call_args = mock_client.upload_file.call_args[0]
            assert os.path.basename(call_args[0]) == os.path.basename(temp_file_path)
            assert call_args[1] == "dataset123"
            assert call_args[2] == "naive"
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_handle_upload_file_error(self, server, mock_client):
        """Test file upload error handling."""
        import tempfile
        import os
        
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("test content")
            temp_file_path = tmp.name
        
        try:
            mock_client.upload_file.side_effect = Exception("Upload failed")
            
            arguments = {
                "file_path": temp_file_path,
                "dataset_id": "dataset123"
            }
            
            with pytest.raises(APIError, match="Failed to upload file"):
                await server._handle_upload_file(arguments)
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_handle_update_file_success(self, server, mock_client):
        """Test successful file update."""
        import tempfile
        import os
        
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("test content")
            temp_file_path = tmp.name
        
        try:
            mock_result = UpdateResult(
                file_id="file123",
                status="success",
                message="File updated"
            )
            mock_client.update_file.return_value = mock_result
            
            arguments = {
                "file_id": "file123",
                "file_path": temp_file_path
            }
            
            result = await server._handle_update_file(arguments)
            
            assert len(result) == 1
            response_text = result[0].text
            assert "File updated successfully!" in response_text
            assert "file123" in response_text
            
            mock_client.update_file.assert_called_once()
            call_args = mock_client.update_file.call_args[0]
            assert call_args[0] == "file123"
            assert os.path.basename(call_args[1]) == os.path.basename(temp_file_path)
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_handle_search_success(self, server, mock_client):
        """Test successful search."""
        mock_items = [
            SearchItem(
                content="This is test content",
                score=0.95,
                file_name="test.txt",
                file_id="file123",
                chunk_id="chunk1"
            ),
            SearchItem(
                content="Another test content",
                score=0.85,
                file_name="test2.txt", 
                file_id="file456",
                chunk_id="chunk2"
            )
        ]
        mock_result = SearchResult(
            results=mock_items,
            total_count=2,
            query_time=0.123
        )
        mock_client.search.return_value = mock_result
        
        arguments = {
            "query": "test query",
            "dataset_id": "dataset123",
            "limit": 10,
            "similarity_threshold": 0.1
        }
        
        result = await server._handle_search(arguments)
        
        assert len(result) == 1
        response_text = result[0].text
        assert "Found 2 results" in response_text
        assert "Score: 0.950" in response_text
        assert "test.txt" in response_text
        assert "Query time: 0.123s" in response_text
        
        mock_client.search.assert_called_once_with(
            query="test query",
            dataset_id="dataset123",
            limit=10,
            similarity_threshold=0.1
        )
    
    @pytest.mark.asyncio
    async def test_handle_search_no_results(self, server, mock_client):
        """Test search with no results."""
        mock_result = SearchResult(
            results=[],
            total_count=0,
            query_time=0.05
        )
        mock_client.search.return_value = mock_result
        
        arguments = {
            "query": "no results query",
            "dataset_id": "dataset123"
        }
        
        result = await server._handle_search(arguments)
        
        assert len(result) == 1
        assert "No results found" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handle_list_files_success(self, server, mock_client):
        """Test successful file listing."""
        from datetime import datetime
        mock_files = [
            FileInfo(
                file_id="file123",
                name="test1.txt",
                size=1024,
                created_at=datetime.fromisoformat("2024-01-01T00:00:00"),
                status="completed"
            ),
            FileInfo(
                file_id="file456",
                name="test2.txt",
                size=2048,
                created_at=datetime.fromisoformat("2024-01-02T00:00:00"),
                status="processing"
            )
        ]
        mock_result = ListFilesResult(files=mock_files, total_count=len(mock_files))
        mock_client.list_files.return_value = mock_result
        
        arguments = {"dataset_id": "dataset123"}
        
        result = await server._handle_list_files(arguments)
        
        assert len(result) == 1
        response_text = result[0].text
        assert "Found 2 files" in response_text
        assert "test1.txt" in response_text
        assert "file123" in response_text
        assert "1.0 KB" in response_text
        assert "completed" in response_text
        
        mock_client.list_files.assert_called_once_with("dataset123")
    
    @pytest.mark.asyncio
    async def test_handle_list_files_empty(self, server, mock_client):
        """Test file listing with no files."""
        mock_result = ListFilesResult(files=[], total_count=0)
        mock_client.list_files.return_value = mock_result
        
        arguments = {"dataset_id": "dataset123"}
        
        result = await server._handle_list_files(arguments)
        
        assert len(result) == 1
        assert "No files found" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handle_delete_file_success(self, server, mock_client):
        """Test successful file deletion."""
        mock_result = DeleteResult(
            file_id="file123",
            status="success", 
            message="File deleted successfully"
        )
        mock_client.delete_file.return_value = mock_result
        
        arguments = {"file_id": "file123"}
        
        result = await server._handle_delete_file(arguments)
        
        assert len(result) == 1
        response_text = result[0].text
        assert "File deleted successfully!" in response_text
        assert "file123" in response_text
        
        mock_client.delete_file.assert_called_once_with("file123")
    
    @pytest.mark.asyncio
    async def test_handle_get_datasets_success(self, server, mock_client):
        """Test successful dataset listing."""
        from datetime import datetime
        mock_datasets = [
            DatasetInfo(
                dataset_id="dataset123",
                name="Test Dataset 1",
                description="First test dataset",
                file_count=5,
                created_at=datetime.now()
            ),
            DatasetInfo(
                dataset_id="dataset456",
                name="Test Dataset 2",
                description=None,
                file_count=0,
                created_at=datetime.now()
            )
        ]
        mock_result = DatasetsResult(datasets=mock_datasets, total_count=len(mock_datasets))
        mock_client.get_datasets.return_value = mock_result
        
        arguments = {}
        
        result = await server._handle_get_datasets(arguments)
        
        assert len(result) == 1
        response_text = result[0].text
        assert "Found 2 datasets" in response_text
        assert "Test Dataset 1" in response_text
        assert "dataset123" in response_text
        assert "First test dataset" in response_text
        assert "Files: 5" in response_text
        assert "No description" in response_text
        
        mock_client.get_datasets.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_get_datasets_empty(self, server, mock_client):
        """Test dataset listing with no datasets."""
        mock_result = DatasetsResult(datasets=[], total_count=0)
        mock_client.get_datasets.return_value = mock_result
        
        arguments = {}
        
        result = await server._handle_get_datasets(arguments)
        
        assert len(result) == 1
        assert "No datasets found" in result[0].text
    
    @pytest.mark.asyncio
    async def test_call_tool_with_error_handling(self, server, mock_client):
        """Test tool call with error handling."""
        mock_client.upload_file.side_effect = Exception("API Error")
        
        arguments = {
            "file_path": "/path/to/file.txt",
            "dataset_id": "dataset123"
        }
        
        result = await server._call_tool("ragflow_upload_file", arguments)
        
        assert len(result) == 1
        assert "Error:" in result[0].text  
  # Parameter validation tests
    
    @pytest.mark.asyncio
    async def test_handle_upload_file_missing_file_path(self, server):
        """Test upload file with missing file_path parameter."""
        arguments = {"dataset_id": "dataset123"}
        
        with pytest.raises(ValidationError, match="file_path parameter is required"):
            await server._handle_upload_file(arguments)
    
    @pytest.mark.asyncio
    async def test_handle_upload_file_missing_dataset_id(self, server):
        """Test upload file with missing dataset_id parameter."""
        arguments = {"file_path": "/path/to/file.txt"}
        
        with pytest.raises(ValidationError, match="dataset_id parameter is required"):
            await server._handle_upload_file(arguments)
    
    @pytest.mark.asyncio
    async def test_handle_upload_file_empty_file_path(self, server):
        """Test upload file with empty file_path."""
        arguments = {"file_path": "", "dataset_id": "dataset123"}
        
        with pytest.raises(ValidationError, match="file_path must be a non-empty string"):
            await server._handle_upload_file(arguments)
    
    @pytest.mark.asyncio
    async def test_handle_upload_file_empty_dataset_id(self, server):
        """Test upload file with empty dataset_id."""
        arguments = {"file_path": "/path/to/file.txt", "dataset_id": ""}
        
        with pytest.raises(ValidationError, match="dataset_id must be at least 1 characters long"):
            await server._handle_upload_file(arguments)
    
    @pytest.mark.asyncio
    async def test_handle_upload_file_invalid_chunk_method(self, server):
        """Test upload file with invalid chunk_method."""
        arguments = {
            "file_path": "/path/to/file.txt",
            "dataset_id": "dataset123",
            "chunk_method": "invalid_method"
        }
        
        with pytest.raises(ValidationError, match="chunk_method must be one of"):
            await server._handle_upload_file(arguments)
    
    @pytest.mark.asyncio
    async def test_handle_update_file_missing_file_id(self, server):
        """Test update file with missing file_id parameter."""
        arguments = {"file_path": "/path/to/file.txt"}
        
        with pytest.raises(ValidationError, match="file_id parameter is required"):
            await server._handle_update_file(arguments)
    
    @pytest.mark.asyncio
    async def test_handle_update_file_empty_file_id(self, server):
        """Test update file with empty file_id."""
        arguments = {"file_id": "", "file_path": "/path/to/file.txt"}
        
        with pytest.raises(ValidationError, match="file_id must be at least 1 characters long"):
            await server._handle_update_file(arguments)
    
    @pytest.mark.asyncio
    async def test_handle_search_missing_query(self, server):
        """Test search with missing query parameter."""
        arguments = {"dataset_id": "dataset123"}
        
        with pytest.raises(ValidationError, match="query parameter is required"):
            await server._handle_search(arguments)
    
    @pytest.mark.asyncio
    async def test_handle_search_empty_query(self, server):
        """Test search with empty query."""
        arguments = {"query": "", "dataset_id": "dataset123"}
        
        with pytest.raises(ValidationError, match="query must be at least 1 characters long"):
            await server._handle_search(arguments)
    
    @pytest.mark.asyncio
    async def test_handle_search_invalid_limit(self, server):
        """Test search with invalid limit."""
        arguments = {
            "query": "test query",
            "dataset_id": "dataset123",
            "limit": -1
        }
        
        with pytest.raises(ValidationError, match="limit must be at least 1"):
            await server._handle_search(arguments)
    
    @pytest.mark.asyncio
    async def test_handle_search_limit_too_high(self, server):
        """Test search with limit too high."""
        arguments = {
            "query": "test query",
            "dataset_id": "dataset123",
            "limit": 101
        }
        
        with pytest.raises(ValidationError, match="limit cannot exceed 100"):
            await server._handle_search(arguments)
    
    @pytest.mark.asyncio
    async def test_handle_search_invalid_similarity_threshold(self, server):
        """Test search with invalid similarity_threshold."""
        arguments = {
            "query": "test query",
            "dataset_id": "dataset123",
            "similarity_threshold": 1.5
        }
        
        with pytest.raises(ValidationError, match="similarity_threshold cannot exceed 1.0"):
            await server._handle_search(arguments)
    
    @pytest.mark.asyncio
    async def test_handle_list_files_missing_dataset_id(self, server):
        """Test list files with missing dataset_id parameter."""
        arguments = {}
        
        with pytest.raises(ValidationError, match="dataset_id parameter is required"):
            await server._handle_list_files(arguments)
    
    @pytest.mark.asyncio
    async def test_handle_list_files_empty_dataset_id(self, server):
        """Test list files with empty dataset_id."""
        arguments = {"dataset_id": ""}
        
        with pytest.raises(ValidationError, match="dataset_id must be at least 1 characters long"):
            await server._handle_list_files(arguments)
    
    @pytest.mark.asyncio
    async def test_handle_delete_file_missing_file_id(self, server):
        """Test delete file with missing file_id parameter."""
        arguments = {}
        
        with pytest.raises(ValidationError, match="file_id parameter is required"):
            await server._handle_delete_file(arguments)
    
    @pytest.mark.asyncio
    async def test_handle_delete_file_empty_file_id(self, server):
        """Test delete file with empty file_id."""
        arguments = {"file_id": ""}
        
        with pytest.raises(ValidationError, match="file_id must be at least 1 characters long"):
            await server._handle_delete_file(arguments)