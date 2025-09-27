"""Simple performance tests for RAGFlow MCP Server."""

import pytest
import asyncio
import time
import tempfile
import os
from unittest.mock import AsyncMock, patch

from ragflow_mcp_server.server import RAGFlowMCPServer
from ragflow_mcp_server.config import RAGFlowConfig
from ragflow_mcp_server.models import (
    UploadResult, SearchResult, SearchItem
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
    """Create mock RAGFlow client with performance simulation."""
    client = AsyncMock()
    
    async def mock_upload_file(*args, **kwargs):
        await asyncio.sleep(0.1)  # Simulate network delay
        return UploadResult(
            file_id=f"file_{int(time.time() * 1000)}",
            status="success",
            message="File uploaded successfully",
            chunk_count=10
        )
    
    async def mock_search(*args, **kwargs):
        await asyncio.sleep(0.05)  # Simulate search time
        return SearchResult(
            results=[
                SearchItem(
                    content="Mock search result",
                    score=0.95,
                    file_name="test.txt",
                    file_id="file123",
                    chunk_id="chunk1"
                )
            ],
            total_count=1,
            query_time=0.05
        )
    
    client.upload_file = mock_upload_file
    client.search = mock_search
    
    return client


@pytest.fixture
def server(config, mock_client):
    """Create test server with mocked client."""
    with patch('ragflow_mcp_server.server.RAGFlowClient', return_value=mock_client):
        server = RAGFlowMCPServer(config)
        server.client = mock_client
        return server


class TestSimplePerformance:
    """Simple performance tests for RAGFlow MCP Server."""
    
    @pytest.mark.asyncio
    async def test_single_upload_performance(self, server):
        """Test performance of single file upload."""
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("Performance test content")
            temp_file_path = tmp.name
        
        try:
            start_time = time.time()
            
            result = await server._call_tool("ragflow_upload_file", {
                "file_path": temp_file_path,
                "dataset_id": "dataset123"
            })
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Verify result
            assert len(result) == 1
            assert "File uploaded successfully!" in result[0].text
            
            # Performance assertion - should complete within reasonable time
            assert execution_time < 1.0, f"Upload took {execution_time:.3f}s, expected < 1.0s"
            
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self, server):
        """Test performance of concurrent operations."""
        num_operations = 10
        
        start_time = time.time()
        
        # Execute multiple searches concurrently
        tasks = [
            server._call_tool("ragflow_search", {
                "query": f"test query {i}",
                "dataset_id": "dataset123"
            })
            for i in range(num_operations)
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verify all operations succeeded
        assert len(results) == num_operations
        for result in results:
            assert len(result) == 1
            assert "Found" in result[0].text
        
        # Performance assertion - concurrent should be faster than sequential
        assert execution_time < 1.0, f"Concurrent operations took {execution_time:.3f}s, expected < 1.0s"
        
        # Calculate throughput
        throughput = num_operations / execution_time
        assert throughput > 10, f"Throughput {throughput:.1f} ops/s, expected > 10 ops/s"