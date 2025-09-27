"""Performance tests for RAGFlow MCP Server."""

import pytest
import asyncio
import time
import tempfile
import os
import statistics
from unittest.mock import AsyncMock, patch
from typing import List, Dict, Any

from ragflow_mcp_server.server import RAGFlowMCPServer
from ragflow_mcp_server.client import RAGFlowClient
from ragflow_mcp_server.config import RAGFlowConfig
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
    """Create mock RAGFlow client with performance simulation."""
    client = AsyncMock()
    
    # Simulate realistic response times
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
    
    async def mock_list_files(*args, **kwargs):
        await asyncio.sleep(0.02)  # Simulate list operation
        return ListFilesResult(
            files=[
                FileInfo(
                    file_id=f"file_{i}",
                    name=f"test_{i}.txt",
                    size=1024,
                    created_at="2024-01-01T00:00:00Z",
                    status="completed"
                )
                for i in range(10)
            ],
            total_count=10
        )
    
    async def mock_delete_file(*args, **kwargs):
        await asyncio.sleep(0.03)  # Simulate delete operation
        return DeleteResult(
            file_id=args[0] if args else "file123",
            status="success",
            message="File deleted successfully"
        )
    
    async def mock_update_file(*args, **kwargs):
        await asyncio.sleep(0.08)  # Simulate update operation
        return UpdateResult(
            file_id=args[0] if args else "file123",
            status="success",
            message="File updated successfully"
        )
    
    async def mock_get_datasets(*args, **kwargs):
        await asyncio.sleep(0.01)  # Simulate datasets retrieval
        return DatasetsResult(
            datasets=[
                DatasetInfo(
                    dataset_id="dataset123",
                    name="Test Dataset",
                    description="A test dataset",
                    file_count=5,
                    created_at="2024-01-01T00:00:00Z"
                )
            ],
            total_count=1
        )
    
    client.upload_file = mock_upload_file
    client.search = mock_search
    client.list_files = mock_list_files
    client.delete_file = mock_delete_file
    client.update_file = mock_update_file
    client.get_datasets = mock_get_datasets
    
    return client


@pytest.fixture
def server(config, mock_client):
    """Create test server with mocked client."""
    with patch('ragflow_mcp_server.server.RAGFlowClient', return_value=mock_client):
        server = RAGFlowMCPServer(config)
        server.client = mock_client
        return server


class TestPerformance:
    """Performance tests for RAGFlow MCP Server."""
    
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
    async def test_concurrent_uploads_performance(self, server):
        """Test performance of concurrent file uploads."""
        num_files = 10
        temp_files = []
        
        # Create multiple temporary files
        for i in range(num_files):
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{i}.txt', delete=False) as tmp:
                tmp.write(f"Performance test content {i}")
                temp_files.append(tmp.name)
        
        try:
            start_time = time.time()
            
            # Execute uploads concurrently
            tasks = [
                server._call_tool("ragflow_upload_file", {
                    "file_path": file_path,
                    "dataset_id": "dataset123"
                })
                for file_path in temp_files
            ]
            
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Verify all uploads succeeded
            assert len(results) == num_files
            for result in results:
                assert len(result) == 1
                assert "File uploaded successfully!" in result[0].text
            
            # Performance assertion - concurrent should be faster than sequential
            # With 0.1s mock delay per upload, concurrent should be ~0.1s, sequential would be ~1.0s
            assert execution_time < 0.5, f"Concurrent uploads took {execution_time:.3f}s, expected < 0.5s"
            
            # Calculate throughput
            throughput = num_files / execution_time
            assert throughput > 20, f"Throughput {throughput:.1f} files/s, expected > 20 files/s"
            
        finally:
            for file_path in temp_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_search_performance(self, server):
        """Test search operation performance."""
        num_searches = 20
        
        start_time = time.time()
        
        # Execute multiple searches concurrently
        tasks = [
            server._call_tool("ragflow_search", {
                "query": f"test query {i}",
                "dataset_id": "dataset123",
                "limit": 10
            })
            for i in range(num_searches)
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verify all searches succeeded
        assert len(results) == num_searches
        for result in results:
            assert len(result) == 1
            assert "Found" in result[0].text
        
        # Performance assertion
        assert execution_time < 1.0, f"Concurrent searches took {execution_time:.3f}s, expected < 1.0s"
        
        # Calculate search throughput
        search_throughput = num_searches / execution_time
        assert search_throughput > 20, f"Search throughput {search_throughput:.1f} searches/s, expected > 20 searches/s"
    
    @pytest.mark.asyncio
    async def test_mixed_operations_performance(self, server):
        """Test performance of mixed operations."""
        num_operations = 30
        
        # Create temporary files for upload/update operations
        temp_files = []
        for i in range(10):
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{i}.txt', delete=False) as tmp:
                tmp.write(f"Mixed operations test content {i}")
                temp_files.append(tmp.name)
        
        try:
            start_time = time.time()
            
            # Create mixed operations
            tasks = []
            
            # Add upload tasks
            for i in range(10):
                tasks.append(server._call_tool("ragflow_upload_file", {
                    "file_path": temp_files[i],
                    "dataset_id": "dataset123"
                }))
            
            # Add search tasks
            for i in range(10):
                tasks.append(server._call_tool("ragflow_search", {
                    "query": f"mixed test {i}",
                    "dataset_id": "dataset123"
                }))
            
            # Add list and dataset operations
            for i in range(5):
                tasks.append(server._call_tool("ragflow_list_files", {
                    "dataset_id": "dataset123"
                }))
            
            for i in range(5):
                tasks.append(server._call_tool("ragflow_get_datasets", {}))
            
            # Execute all operations concurrently
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Verify all operations succeeded
            assert len(results) == num_operations
            for result in results:
                assert len(result) == 1
                assert isinstance(result[0].text, str)
            
            # Performance assertion
            assert execution_time < 1.0, f"Mixed operations took {execution_time:.3f}s, expected < 1.0s"
            
            # Calculate overall throughput
            overall_throughput = num_operations / execution_time
            assert overall_throughput > 30, f"Overall throughput {overall_throughput:.1f} ops/s, expected > 30 ops/s"
            
        finally:
            for file_path in temp_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_large_file_upload_performance(self, server):
        """Test performance with large file uploads."""
        # Create a large temporary file (1MB)
        large_content = "Large file content " * 50000  # ~1MB
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write(large_content)
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
            
            # Performance assertion - large files should still complete reasonably quickly
            assert execution_time < 2.0, f"Large file upload took {execution_time:.3f}s, expected < 2.0s"
            
            # Calculate throughput in MB/s
            file_size_mb = len(large_content.encode('utf-8')) / (1024 * 1024)
            throughput_mbps = file_size_mb / execution_time
            
            # Should achieve reasonable throughput
            assert throughput_mbps > 0.5, f"Throughput {throughput_mbps:.2f} MB/s, expected > 0.5 MB/s"
            
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_response_time_consistency(self, server):
        """Test response time consistency across multiple operations."""
        num_iterations = 50
        response_times = []
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("Consistency test content")
            temp_file_path = tmp.name
        
        try:
            # Measure response times for multiple identical operations
            for i in range(num_iterations):
                start_time = time.time()
                
                result = await server._call_tool("ragflow_search", {
                    "query": f"consistency test {i}",
                    "dataset_id": "dataset123"
                })
                
                end_time = time.time()
                response_times.append(end_time - start_time)
                
                # Verify result
                assert len(result) == 1
                assert "Found" in result[0].text
            
            # Calculate statistics
            mean_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            std_dev = statistics.stdev(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            # Performance assertions
            assert mean_time < 0.2, f"Mean response time {mean_time:.3f}s, expected < 0.2s"
            assert median_time < 0.2, f"Median response time {median_time:.3f}s, expected < 0.2s"
            assert std_dev < 0.1, f"Standard deviation {std_dev:.3f}s, expected < 0.1s"
            assert max_time < 0.5, f"Max response time {max_time:.3f}s, expected < 0.5s"
            
            # Consistency check - 95% of requests should be within 2 standard deviations
            outliers = [t for t in response_times if abs(t - mean_time) > 2 * std_dev]
            outlier_percentage = len(outliers) / num_iterations * 100
            assert outlier_percentage < 5, f"Outlier percentage {outlier_percentage:.1f}%, expected < 5%"
            
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, server):
        """Test memory usage stability during operations."""
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create temporary files
        temp_files = []
        for i in range(20):
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{i}.txt', delete=False) as tmp:
                tmp.write(f"Memory test content {i} " * 1000)  # ~20KB each
                temp_files.append(tmp.name)
        
        try:
            # Perform many operations
            for iteration in range(5):
                tasks = []
                
                # Upload files
                for file_path in temp_files:
                    tasks.append(server._call_tool("ragflow_upload_file", {
                        "file_path": file_path,
                        "dataset_id": "dataset123"
                    }))
                
                # Search operations
                for i in range(20):
                    tasks.append(server._call_tool("ragflow_search", {
                        "query": f"memory test {i}",
                        "dataset_id": "dataset123"
                    }))
                
                # Execute all tasks
                results = await asyncio.gather(*tasks)
                
                # Verify results
                assert len(results) == 40
                for result in results:
                    assert len(result) == 1
                
                # Force garbage collection
                gc.collect()
                
                # Check memory usage
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = current_memory - initial_memory
                
                # Memory should not increase significantly
                assert memory_increase < 50, f"Memory increased by {memory_increase:.1f}MB, expected < 50MB"
            
        finally:
            for file_path in temp_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_error_handling_performance(self, server):
        """Test performance of error handling scenarios."""
        num_errors = 100
        
        start_time = time.time()
        
        # Create tasks that will result in errors
        tasks = [
            server._call_tool("ragflow_upload_file", {
                "file_path": f"/nonexistent/file_{i}.txt",
                "dataset_id": "dataset123"
            })
            for i in range(num_errors)
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verify all operations returned error responses
        assert len(results) == num_errors
        for result in results:
            assert len(result) == 1
            assert "Error:" in result[0].text
            assert "File not found" in result[0].text
        
        # Performance assertion - error handling should be fast
        assert execution_time < 1.0, f"Error handling took {execution_time:.3f}s, expected < 1.0s"
        
        # Calculate error handling throughput
        error_throughput = num_errors / execution_time
        assert error_throughput > 100, f"Error throughput {error_throughput:.1f} errors/s, expected > 100 errors/s"
    
    @pytest.mark.asyncio
    async def test_parameter_validation_performance(self, server):
        """Test performance of parameter validation."""
        num_validations = 200
        
        start_time = time.time()
        
        # Create tasks with invalid parameters
        tasks = []
        
        # Missing required parameters
        for i in range(50):
            tasks.append(server._call_tool("ragflow_upload_file", {
                "dataset_id": "dataset123"  # Missing file_path
            }))
        
        # Empty parameters
        for i in range(50):
            tasks.append(server._call_tool("ragflow_search", {
                "query": "",  # Empty query
                "dataset_id": "dataset123"
            }))
        
        # Invalid parameter types
        for i in range(50):
            tasks.append(server._call_tool("ragflow_search", {
                "query": "test",
                "dataset_id": "dataset123",
                "limit": "invalid"  # Should be integer
            }))
        
        # Invalid parameter values
        for i in range(50):
            tasks.append(server._call_tool("ragflow_search", {
                "query": "test",
                "dataset_id": "dataset123",
                "similarity_threshold": 2.0  # Should be <= 1.0
            }))
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verify all validations returned error responses
        assert len(results) == num_validations
        for result in results:
            assert len(result) == 1
            assert "Error:" in result[0].text
        
        # Performance assertion - validation should be very fast
        assert execution_time < 0.5, f"Validation took {execution_time:.3f}s, expected < 0.5s"
        
        # Calculate validation throughput
        validation_throughput = num_validations / execution_time
        assert validation_throughput > 400, f"Validation throughput {validation_throughput:.1f} validations/s, expected > 400 validations/s"
    
    @pytest.mark.asyncio
    async def test_stress_test_mixed_load(self, server):
        """Stress test with mixed high load."""
        # Create temporary files
        temp_files = []
        for i in range(50):
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{i}.txt', delete=False) as tmp:
                tmp.write(f"Stress test content {i} " * 100)
                temp_files.append(tmp.name)
        
        try:
            start_time = time.time()
            
            # Create high load with mixed operations
            tasks = []
            
            # 50 upload operations
            for file_path in temp_files:
                tasks.append(server._call_tool("ragflow_upload_file", {
                    "file_path": file_path,
                    "dataset_id": "dataset123"
                }))
            
            # 100 search operations
            for i in range(100):
                tasks.append(server._call_tool("ragflow_search", {
                    "query": f"stress test {i}",
                    "dataset_id": "dataset123"
                }))
            
            # 25 list operations
            for i in range(25):
                tasks.append(server._call_tool("ragflow_list_files", {
                    "dataset_id": "dataset123"
                }))
            
            # 25 dataset operations
            for i in range(25):
                tasks.append(server._call_tool("ragflow_get_datasets", {}))
            
            # Execute all 200 operations concurrently
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Verify all operations completed
            assert len(results) == 200
            success_count = 0
            for result in results:
                assert len(result) == 1
                if "Error:" not in result[0].text:
                    success_count += 1
            
            # Most operations should succeed (allowing for some file not found errors)
            success_rate = success_count / 200 * 100
            assert success_rate > 75, f"Success rate {success_rate:.1f}%, expected > 75%"
            
            # Performance assertion - should handle high load
            assert execution_time < 2.0, f"Stress test took {execution_time:.3f}s, expected < 2.0s"
            
            # Calculate overall throughput under stress
            stress_throughput = 200 / execution_time
            assert stress_throughput > 100, f"Stress throughput {stress_throughput:.1f} ops/s, expected > 100 ops/s"
            
        finally:
            for file_path in temp_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)