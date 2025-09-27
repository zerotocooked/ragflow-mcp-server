"""Simple end-to-end integration test for RAGFlow MCP Server."""

import pytest
import tempfile
import os
from unittest.mock import AsyncMock, patch

from ragflow_mcp_server.server import RAGFlowMCPServer
from ragflow_mcp_server.config import RAGFlowConfig
from ragflow_mcp_server.models import (
    UploadResult, SearchResult, SearchItem, DeleteResult
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
    
    client.upload_file.return_value = UploadResult(
        file_id="file123",
        status="success",
        message="File uploaded successfully",
        chunk_count=5
    )
    
    client.search.return_value = SearchResult(
        results=[
            SearchItem(
                content="Test content from uploaded file",
                score=0.95,
                file_name="test.txt",
                file_id="file123",
                chunk_id="chunk1"
            )
        ],
        total_count=1,
        query_time=0.123
    )
    
    client.delete_file.return_value = DeleteResult(
        file_id="file123",
        status="success",
        message="File deleted successfully"
    )
    
    return client


@pytest.fixture
def server(config, mock_client):
    """Create test server with mocked client."""
    with patch('ragflow_mcp_server.server.RAGFlowClient', return_value=mock_client):
        server = RAGFlowMCPServer(config)
        server.client = mock_client
        return server


class TestSimpleEndToEnd:
    """Simple end-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_upload_search_delete_workflow(self, server):
        """Test basic upload -> search -> delete workflow."""
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("This is test content for integration testing")
            temp_file_path = tmp.name
        
        try:
            # Step 1: Upload file
            upload_result = await server._call_tool("ragflow_upload_file", {
                "file_path": temp_file_path,
                "dataset_id": "dataset123"
            })
            
            assert len(upload_result) == 1
            upload_text = upload_result[0].text
            assert "File uploaded successfully!" in upload_text
            
            # Step 2: Search for content
            search_result = await server._call_tool("ragflow_search", {
                "query": "test content",
                "dataset_id": "dataset123"
            })
            
            assert len(search_result) == 1
            search_text = search_result[0].text
            assert "Found 1 results" in search_text
            
            # Step 3: Delete file
            delete_result = await server._call_tool("ragflow_delete_file", {
                "file_id": "file123"
            })
            
            assert len(delete_result) == 1
            delete_text = delete_result[0].text
            assert "File deleted successfully!" in delete_text
            
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, server):
        """Test error handling in workflow."""
        # Test upload with non-existent file
        upload_error = await server._call_tool("ragflow_upload_file", {
            "file_path": "/nonexistent/file.txt",
            "dataset_id": "dataset123"
        })
        
        assert len(upload_error) == 1
        assert "Error:" in upload_error[0].text
        assert "File not found" in upload_error[0].text