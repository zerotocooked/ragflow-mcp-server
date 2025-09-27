"""Integration tests with mock RAGFlow API server."""

import pytest
import pytest_asyncio
import asyncio
import json
import tempfile
import os
from unittest.mock import AsyncMock, patch, MagicMock
from aiohttp import web, ClientSession
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from typing import Dict, Any, List

from ragflow_mcp_server.server import RAGFlowMCPServer
from ragflow_mcp_server.client import RAGFlowClient
from ragflow_mcp_server.config import RAGFlowConfig
from ragflow_mcp_server.models import (
    UploadResult, UpdateResult, SearchResult, SearchItem,
    ListFilesResult, FileInfo, DeleteResult, DatasetsResult, DatasetInfo
)
from ragflow_mcp_server.errors import APIError, ConfigurationError, AuthenticationError


class MockRAGFlowServer:
    """Mock RAGFlow API server for integration testing."""
    
    def __init__(self):
        self.files = {}
        self.datasets = {
            "dataset123": {
                "id": "dataset123",
                "name": "Test Dataset",
                "description": "A test dataset for integration testing",
                "file_count": 0
            }
        }
        self.search_results = []
        self.api_key = "test_api_key"
        self.request_count = 0
        self.response_delay = 0
    
    async def handle_upload(self, request):
        """Handle file upload requests."""
        self.request_count += 1
        if self.response_delay:
            await asyncio.sleep(self.response_delay)
        
        # Check authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != f'Bearer {self.api_key}':
            return web.json_response(
                {"error": "Unauthorized"}, 
                status=401
            )
        
        # Parse multipart form data
        reader = await request.multipart()
        file_data = None
        dataset_id = None
        chunk_method = "naive"
        
        async for field in reader:
            if field.name == 'file':
                file_data = await field.read()
            elif field.name == 'dataset_id':
                dataset_id = await field.text()
            elif field.name == 'chunk_method':
                chunk_method = await field.text()
        
        if not file_data or not dataset_id:
            return web.json_response(
                {"error": "Missing file or dataset_id"}, 
                status=400
            )
        
        if dataset_id not in self.datasets:
            return web.json_response(
                {"error": "Dataset not found"}, 
                status=404
            )
        
        # Create file record
        file_id = f"file_{len(self.files) + 1}"
        self.files[file_id] = {
            "id": file_id,
            "name": f"test_file_{len(self.files) + 1}.txt",
            "size": len(file_data),
            "dataset_id": dataset_id,
            "status": "completed",
            "chunk_count": len(file_data) // 100 + 1,
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        self.datasets[dataset_id]["file_count"] += 1
        
        return web.json_response({
            "code": 0,
            "data": {
                "file_id": file_id,
                "status": "success",
                "message": "File uploaded successfully",
                "chunk_count": self.files[file_id]["chunk_count"]
            }
        })
    
    async def handle_update(self, request):
        """Handle file update requests."""
        self.request_count += 1
        if self.response_delay:
            await asyncio.sleep(self.response_delay)
        
        # Check authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != f'Bearer {self.api_key}':
            return web.json_response(
                {"error": "Unauthorized"}, 
                status=401
            )
        
        file_id = request.match_info['file_id']
        
        if file_id not in self.files:
            return web.json_response(
                {"error": "File not found"}, 
                status=404
            )
        
        # Parse multipart form data
        reader = await request.multipart()
        file_data = None
        
        async for field in reader:
            if field.name == 'file':
                file_data = await field.read()
        
        if not file_data:
            return web.json_response(
                {"error": "Missing file data"}, 
                status=400
            )
        
        # Update file record
        self.files[file_id]["size"] = len(file_data)
        self.files[file_id]["chunk_count"] = len(file_data) // 100 + 1
        
        return web.json_response({
            "code": 0,
            "data": {
                "file_id": file_id,
                "status": "success",
                "message": "File updated successfully"
            }
        })
    
    async def handle_search(self, request):
        """Handle search requests."""
        self.request_count += 1
        if self.response_delay:
            await asyncio.sleep(self.response_delay)
        
        # Check authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != f'Bearer {self.api_key}':
            return web.json_response(
                {"error": "Unauthorized"}, 
                status=401
            )
        
        data = await request.json()
        query = data.get('query', '')
        dataset_id = data.get('dataset_id', '')
        limit = data.get('limit', 10)
        similarity_threshold = data.get('similarity_threshold', 0.1)
        
        if not query or not dataset_id:
            return web.json_response(
                {"error": "Missing query or dataset_id"}, 
                status=400
            )
        
        if dataset_id not in self.datasets:
            return web.json_response(
                {"error": "Dataset not found"}, 
                status=404
            )
        
        # Generate mock search results
        results = []
        for i, (file_id, file_info) in enumerate(self.files.items()):
            if file_info["dataset_id"] == dataset_id and i < limit:
                score = 0.9 - (i * 0.1)  # Decreasing relevance
                if score >= similarity_threshold:
                    results.append({
                        "content": f"Mock content for {query} from {file_info['name']}",
                        "score": score,
                        "file_name": file_info["name"],
                        "file_id": file_id,
                        "chunk_id": f"chunk_{i}"
                    })
        
        return web.json_response({
            "code": 0,
            "data": {
                "results": results,
                "total_count": len(results),
                "query_time": 0.123
            }
        })
    
    async def handle_list_files(self, request):
        """Handle list files requests."""
        self.request_count += 1
        if self.response_delay:
            await asyncio.sleep(self.response_delay)
        
        # Check authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != f'Bearer {self.api_key}':
            return web.json_response(
                {"error": "Unauthorized"}, 
                status=401
            )
        
        dataset_id = request.query.get('dataset_id')
        limit = int(request.query.get('limit', 100))
        offset = int(request.query.get('offset', 0))
        
        if not dataset_id:
            return web.json_response(
                {"error": "Missing dataset_id"}, 
                status=400
            )
        
        if dataset_id not in self.datasets:
            return web.json_response(
                {"error": "Dataset not found"}, 
                status=404
            )
        
        # Filter files by dataset
        dataset_files = [
            {
                "file_id": file_id,
                "name": file_info["name"],
                "size": file_info["size"],
                "created_at": file_info["created_at"],
                "status": file_info["status"]
            }
            for file_id, file_info in self.files.items()
            if file_info["dataset_id"] == dataset_id
        ]
        
        # Apply pagination
        paginated_files = dataset_files[offset:offset + limit]
        
        return web.json_response({
            "code": 0,
            "data": {
                "files": paginated_files,
                "total_count": len(dataset_files)
            }
        })
    
    async def handle_delete_file(self, request):
        """Handle delete file requests."""
        self.request_count += 1
        if self.response_delay:
            await asyncio.sleep(self.response_delay)
        
        # Check authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != f'Bearer {self.api_key}':
            return web.json_response(
                {"error": "Unauthorized"}, 
                status=401
            )
        
        file_id = request.match_info['file_id']
        
        if file_id not in self.files:
            return web.json_response(
                {"error": "File not found"}, 
                status=404
            )
        
        # Update dataset file count
        dataset_id = self.files[file_id]["dataset_id"]
        self.datasets[dataset_id]["file_count"] -= 1
        
        # Delete file
        del self.files[file_id]
        
        return web.json_response({
            "code": 0,
            "data": {
                "file_id": file_id,
                "status": "success",
                "message": "File deleted successfully"
            }
        })
    
    async def handle_get_datasets(self, request):
        """Handle get datasets requests."""
        self.request_count += 1
        if self.response_delay:
            await asyncio.sleep(self.response_delay)
        
        # Check authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != f'Bearer {self.api_key}':
            return web.json_response(
                {"error": "Unauthorized"}, 
                status=401
            )
        
        datasets = [
            {
                "dataset_id": dataset_id,
                "name": dataset_info["name"],
                "description": dataset_info["description"],
                "file_count": dataset_info["file_count"],
                "created_at": "2024-01-01T00:00:00Z"
            }
            for dataset_id, dataset_info in self.datasets.items()
        ]
        
        return web.json_response({
            "code": 0,
            "data": {
                "datasets": datasets,
                "total_count": len(datasets)
            }
        })
    
    def create_app(self):
        """Create aiohttp application with mock endpoints."""
        app = web.Application()
        
        # Add routes matching RAGFlow API
        app.router.add_post('/api/v1/files/upload', self.handle_upload)
        app.router.add_put('/api/v1/files/{file_id}', self.handle_update)
        app.router.add_post('/api/v1/search', self.handle_search)
        app.router.add_get('/api/v1/files', self.handle_list_files)
        app.router.add_delete('/api/v1/files/{file_id}', self.handle_delete_file)
        app.router.add_get('/api/v1/datasets', self.handle_get_datasets)
        
        return app


@pytest_asyncio.fixture
async def mock_ragflow_server():
    """Create and start mock RAGFlow server."""
    from aiohttp.test_utils import TestServer, TestClient
    
    mock_server = MockRAGFlowServer()
    app = mock_server.create_app()
    
    async with TestServer(app) as server:
        async with TestClient(server) as client:
            # Update mock server with actual URL
            mock_server.base_url = str(server.make_url('/'))
            yield mock_server, server


@pytest.fixture
def config_with_mock_server(mock_ragflow_server):
    """Create configuration pointing to mock server."""
    mock_server, server = mock_ragflow_server
    return RAGFlowConfig(
        base_url=str(server.make_url('/')),
        api_key="test_api_key",
        default_dataset_id="dataset123",
        timeout=30,
        max_retries=3
    )


class TestRAGFlowIntegration:
    """Integration tests with mock RAGFlow API server."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow_upload_search_delete(self, mock_ragflow_server):
        """Test complete workflow: upload -> search -> delete."""
        mock_server, server = mock_ragflow_server
        
        config = RAGFlowConfig(
            base_url=str(server.make_url('/')),
            api_key="test_api_key",
            timeout=30,
            max_retries=3
        )
        
        client = RAGFlowClient(config)
        mcp_server = RAGFlowMCPServer(config)
        mcp_server.client = client
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("This is test content for integration testing")
            temp_file_path = tmp.name
        
        try:
            # Step 1: Upload file
            upload_result = await mcp_server._call_tool("ragflow_upload_file", {
                "file_path": temp_file_path,
                "dataset_id": "dataset123",
                "chunk_method": "naive"
            })
            
            assert len(upload_result) == 1
            upload_text = upload_result[0].text
            assert "File uploaded successfully!" in upload_text
            
            # Extract file ID from response
            import re
            file_id_match = re.search(r'File ID: (\w+)', upload_text)
            assert file_id_match
            file_id = file_id_match.group(1)
            
            # Step 2: Search for uploaded content
            search_result = await mcp_server._call_tool("ragflow_search", {
                "query": "test content",
                "dataset_id": "dataset123",
                "limit": 10,
                "similarity_threshold": 0.1
            })
            
            assert len(search_result) == 1
            search_text = search_result[0].text
            assert "Found 1 results" in search_text
            assert "test content" in search_text
            
            # Step 3: List files to verify upload
            list_result = await mcp_server._call_tool("ragflow_list_files", {
                "dataset_id": "dataset123"
            })
            
            assert len(list_result) == 1
            list_text = list_result[0].text
            assert "Found 1 files" in list_text
            assert file_id in list_text
            
            # Step 4: Delete file
            delete_result = await mcp_server._call_tool("ragflow_delete_file", {
                "file_id": file_id
            })
            
            assert len(delete_result) == 1
            delete_text = delete_result[0].text
            assert "File deleted successfully!" in delete_text
            assert file_id in delete_text
            
            # Step 5: Verify file is deleted
            list_result_after = await mcp_server._call_tool("ragflow_list_files", {
                "dataset_id": "dataset123"
            })
            
            assert len(list_result_after) == 1
            list_text_after = list_result_after[0].text
            assert "Found 0 files" in list_text_after
            
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_upload_update_workflow(self, mock_ragflow_server):
        """Test upload -> update workflow."""
        mock_server, server = mock_ragflow_server
        
        config = RAGFlowConfig(
            base_url=str(server.make_url('/')),
            api_key="test_api_key",
            timeout=30,
            max_retries=3
        )
        
        client = RAGFlowClient(config)
        mcp_server = RAGFlowMCPServer(config)
        mcp_server.client = client
        
        # Create temporary test files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp1:
            tmp1.write("Original content")
            original_file_path = tmp1.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp2:
            tmp2.write("Updated content with more information")
            updated_file_path = tmp2.name
        
        try:
            # Step 1: Upload original file
            upload_result = await mcp_server._call_tool("ragflow_upload_file", {
                "file_path": original_file_path,
                "dataset_id": "dataset123"
            })
            
            assert len(upload_result) == 1
            upload_text = upload_result[0].text
            assert "File uploaded successfully!" in upload_text
            
            # Extract file ID
            import re
            file_id_match = re.search(r'File ID: (\w+)', upload_text)
            assert file_id_match
            file_id = file_id_match.group(1)
            
            # Step 2: Update file with new content
            update_result = await mcp_server._call_tool("ragflow_update_file", {
                "file_id": file_id,
                "file_path": updated_file_path
            })
            
            assert len(update_result) == 1
            update_text = update_result[0].text
            assert "File updated successfully!" in update_text
            assert file_id in update_text
            
            # Step 3: Search for updated content
            search_result = await mcp_server._call_tool("ragflow_search", {
                "query": "updated content",
                "dataset_id": "dataset123"
            })
            
            assert len(search_result) == 1
            search_text = search_result[0].text
            assert "Found 1 results" in search_text
            assert "updated content" in search_text
            
        finally:
            os.unlink(original_file_path)
            os.unlink(updated_file_path)
    
    @pytest.mark.asyncio
    async def test_multiple_files_workflow(self, mock_ragflow_server):
        """Test workflow with multiple files."""
        mock_server, server = mock_ragflow_server
        
        config = RAGFlowConfig(
            base_url=str(server.make_url('/')),
            api_key="test_api_key",
            timeout=30,
            max_retries=3
        )
        
        client = RAGFlowClient(config)
        mcp_server = RAGFlowMCPServer(config)
        mcp_server.client = client
        
        # Create multiple temporary test files
        temp_files = []
        file_ids = []
        
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{i}.txt', delete=False) as tmp:
                tmp.write(f"Content for file {i} with unique identifier {i}")
                temp_files.append(tmp.name)
        
        try:
            # Upload all files
            for i, file_path in enumerate(temp_files):
                upload_result = await mcp_server._call_tool("ragflow_upload_file", {
                    "file_path": file_path,
                    "dataset_id": "dataset123"
                })
                
                assert len(upload_result) == 1
                upload_text = upload_result[0].text
                assert "File uploaded successfully!" in upload_text
                
                # Extract file ID
                import re
                file_id_match = re.search(r'File ID: (\w+)', upload_text)
                assert file_id_match
                file_ids.append(file_id_match.group(1))
            
            # List all files
            list_result = await mcp_server._call_tool("ragflow_list_files", {
                "dataset_id": "dataset123"
            })
            
            assert len(list_result) == 1
            list_text = list_result[0].text
            assert "Found 3 files" in list_text
            
            # Search should return multiple results
            search_result = await mcp_server._call_tool("ragflow_search", {
                "query": "Content for file",
                "dataset_id": "dataset123",
                "limit": 10
            })
            
            assert len(search_result) == 1
            search_text = search_result[0].text
            assert "Found 3 results" in search_text
            
            # Delete files one by one
            for file_id in file_ids:
                delete_result = await mcp_server._call_tool("ragflow_delete_file", {
                    "file_id": file_id
                })
                
                assert len(delete_result) == 1
                delete_text = delete_result[0].text
                assert "File deleted successfully!" in delete_text
            
            # Verify all files are deleted
            final_list_result = await mcp_server._call_tool("ragflow_list_files", {
                "dataset_id": "dataset123"
            })
            
            assert len(final_list_result) == 1
            final_list_text = final_list_result[0].text
            assert "Found 0 files" in final_list_text
            
        finally:
            for file_path in temp_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, mock_ragflow_server):
        """Test error handling in workflows."""
        mock_server, server = mock_ragflow_server
        
        config = RAGFlowConfig(
            base_url=str(server.make_url('/')),
            api_key="test_api_key",
            timeout=30,
            max_retries=3
        )
        
        client = RAGFlowClient(config)
        mcp_server = RAGFlowMCPServer(config)
        mcp_server.client = client
        
        # Test 1: Upload non-existent file
        upload_result = await mcp_server._call_tool("ragflow_upload_file", {
            "file_path": "/non/existent/file.txt",
            "dataset_id": "dataset123"
        })
        
        assert len(upload_result) == 1
        upload_text = upload_result[0].text
        assert "Error:" in upload_text
        assert "File not found" in upload_text
        
        # Test 2: Update non-existent file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("test content")
            temp_file_path = tmp.name
        
        try:
            update_result = await mcp_server._call_tool("ragflow_update_file", {
                "file_id": "nonexistent_file",
                "file_path": temp_file_path
            })
            
            assert len(update_result) == 1
            update_text = update_result[0].text
            assert "Error:" in update_text
            assert "File not found" in update_text
            
            # Test 3: Search in non-existent dataset
            search_result = await mcp_server._call_tool("ragflow_search", {
                "query": "test",
                "dataset_id": "nonexistent_dataset"
            })
            
            assert len(search_result) == 1
            search_text = search_result[0].text
            assert "Error:" in search_text
            assert "Dataset not found" in search_text
            
            # Test 4: List files from non-existent dataset
            list_result = await mcp_server._call_tool("ragflow_list_files", {
                "dataset_id": "nonexistent_dataset"
            })
            
            assert len(list_result) == 1
            list_text = list_result[0].text
            assert "Error:" in list_text
            assert "Dataset not found" in list_text
            
            # Test 5: Delete non-existent file
            delete_result = await mcp_server._call_tool("ragflow_delete_file", {
                "file_id": "nonexistent_file"
            })
            
            assert len(delete_result) == 1
            delete_text = delete_result[0].text
            assert "Error:" in delete_text
            assert "File not found" in delete_text
            
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_authentication_error_workflow(self, mock_ragflow_server):
        """Test authentication error handling."""
        mock_server, server = mock_ragflow_server
        
        # Use invalid API key
        config = RAGFlowConfig(
            base_url=str(server.make_url('/')),
            api_key="invalid_api_key",
            timeout=30,
            max_retries=3
        )
        
        client = RAGFlowClient(config)
        mcp_server = RAGFlowMCPServer(config)
        mcp_server.client = client
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("test content")
            temp_file_path = tmp.name
        
        try:
            # All operations should fail with authentication error
            operations = [
                ("ragflow_upload_file", {
                    "file_path": temp_file_path,
                    "dataset_id": "dataset123"
                }),
                ("ragflow_search", {
                    "query": "test",
                    "dataset_id": "dataset123"
                }),
                ("ragflow_list_files", {
                    "dataset_id": "dataset123"
                }),
                ("ragflow_get_datasets", {})
            ]
            
            for tool_name, arguments in operations:
                result = await mcp_server._call_tool(tool_name, arguments)
                
                assert len(result) == 1
                result_text = result[0].text
                assert "Error:" in result_text
                assert "Unauthorized" in result_text
                
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_workflow(self, mock_ragflow_server):
        """Test concurrent operations workflow."""
        mock_server, server = mock_ragflow_server
        
        config = RAGFlowConfig(
            base_url=str(server.make_url('/')),
            api_key="test_api_key",
            timeout=30,
            max_retries=3
        )
        
        client = RAGFlowClient(config)
        mcp_server = RAGFlowMCPServer(config)
        mcp_server.client = client
        
        # Create multiple temporary files
        temp_files = []
        for i in range(5):
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{i}.txt', delete=False) as tmp:
                tmp.write(f"Concurrent test content {i}")
                temp_files.append(tmp.name)
        
        try:
            # Upload files concurrently
            upload_tasks = [
                mcp_server._call_tool("ragflow_upload_file", {
                    "file_path": file_path,
                    "dataset_id": "dataset123"
                })
                for file_path in temp_files
            ]
            
            upload_results = await asyncio.gather(*upload_tasks)
            
            # Verify all uploads succeeded
            file_ids = []
            for result in upload_results:
                assert len(result) == 1
                result_text = result[0].text
                assert "File uploaded successfully!" in result_text
                
                # Extract file ID
                import re
                file_id_match = re.search(r'File ID: (\w+)', result_text)
                assert file_id_match
                file_ids.append(file_id_match.group(1))
            
            # Perform concurrent searches
            search_tasks = [
                mcp_server._call_tool("ragflow_search", {
                    "query": f"content {i}",
                    "dataset_id": "dataset123"
                })
                for i in range(5)
            ]
            
            search_results = await asyncio.gather(*search_tasks)
            
            # Verify all searches succeeded
            for result in search_results:
                assert len(result) == 1
                result_text = result[0].text
                assert "Found" in result_text
            
            # Delete files concurrently
            delete_tasks = [
                mcp_server._call_tool("ragflow_delete_file", {
                    "file_id": file_id
                })
                for file_id in file_ids
            ]
            
            delete_results = await asyncio.gather(*delete_tasks)
            
            # Verify all deletions succeeded
            for result in delete_results:
                assert len(result) == 1
                result_text = result[0].text
                assert "File deleted successfully!" in result_text
            
        finally:
            for file_path in temp_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_dataset_management_workflow(self, mock_ragflow_server):
        """Test dataset management workflow."""
        mock_server, server = mock_ragflow_server
        
        config = RAGFlowConfig(
            base_url=str(server.make_url('/')),
            api_key="test_api_key",
            timeout=30,
            max_retries=3
        )
        
        client = RAGFlowClient(config)
        mcp_server = RAGFlowMCPServer(config)
        mcp_server.client = client
        
        # Get available datasets
        datasets_result = await mcp_server._call_tool("ragflow_get_datasets", {})
        
        assert len(datasets_result) == 1
        datasets_text = datasets_result[0].text
        assert "Found 1 datasets" in datasets_text
        assert "Test Dataset" in datasets_text
        assert "dataset123" in datasets_text
        
        # Upload file to increase dataset file count
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("test content for dataset")
            temp_file_path = tmp.name
        
        try:
            upload_result = await mcp_server._call_tool("ragflow_upload_file", {
                "file_path": temp_file_path,
                "dataset_id": "dataset123"
            })
            
            assert len(upload_result) == 1
            upload_text = upload_result[0].text
            assert "File uploaded successfully!" in upload_text
            
            # Verify dataset file count updated
            datasets_result_after = await mcp_server._call_tool("ragflow_get_datasets", {})
            
            assert len(datasets_result_after) == 1
            datasets_text_after = datasets_result_after[0].text
            assert "Found 1 datasets" in datasets_text_after
            
        finally:
            os.unlink(temp_file_path)


class TestRAGFlowClientIntegration:
    """Direct integration tests for RAGFlow client."""
    
    @pytest.mark.asyncio
    async def test_client_direct_integration(self, mock_ragflow_server):
        """Test RAGFlow client direct integration."""
        mock_server, server = mock_ragflow_server
        
        config = RAGFlowConfig(
            base_url=str(server.make_url('/')),
            api_key="test_api_key",
            timeout=30,
            max_retries=3
        )
        
        client = RAGFlowClient(config)
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("Direct client integration test content")
            temp_file_path = tmp.name
        
        try:
            # Test upload
            upload_result = await client.upload_file(
                temp_file_path, "dataset123", "naive"
            )
            
            assert upload_result.status == "success"
            assert upload_result.file_id.startswith("file_")
            assert upload_result.chunk_count > 0
            
            file_id = upload_result.file_id
            
            # Test search
            search_result = await client.search(
                "integration test", "dataset123", limit=10, similarity_threshold=0.1
            )
            
            assert search_result.total_count >= 1
            assert len(search_result.results) >= 1
            assert search_result.query_time > 0
            
            # Test list files
            list_result = await client.list_files("dataset123")
            
            assert list_result.total_count >= 1
            assert len(list_result.files) >= 1
            assert any(f.file_id == file_id for f in list_result.files)
            
            # Test get datasets
            datasets_result = await client.get_datasets()
            
            assert datasets_result.total_count >= 1
            assert len(datasets_result.datasets) >= 1
            assert any(d.dataset_id == "dataset123" for d in datasets_result.datasets)
            
            # Test update
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp2:
                tmp2.write("Updated direct client integration test content")
                updated_file_path = tmp2.name
            
            try:
                update_result = await client.update_file(file_id, updated_file_path)
                
                assert update_result.status == "success"
                assert update_result.file_id == file_id
                
            finally:
                os.unlink(updated_file_path)
            
            # Test delete
            delete_result = await client.delete_file(file_id)
            
            assert delete_result.status == "success"
            assert delete_result.file_id == file_id
            
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_client_error_handling_integration(self, mock_ragflow_server):
        """Test client error handling integration."""
        mock_server, server = mock_ragflow_server
        
        # Test with invalid API key
        config = RAGFlowConfig(
            base_url=str(server.make_url('/')),
            api_key="invalid_key",
            timeout=30,
            max_retries=3
        )
        
        client = RAGFlowClient(config)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("test content")
            temp_file_path = tmp.name
        
        try:
            # All operations should raise APIError
            with pytest.raises(APIError, match="Unauthorized"):
                await client.upload_file(temp_file_path, "dataset123")
            
            with pytest.raises(APIError, match="Unauthorized"):
                await client.search("test", "dataset123")
            
            with pytest.raises(APIError, match="Unauthorized"):
                await client.list_files("dataset123")
            
            with pytest.raises(APIError, match="Unauthorized"):
                await client.get_datasets()
            
            with pytest.raises(APIError, match="Unauthorized"):
                await client.update_file("file123", temp_file_path)
            
            with pytest.raises(APIError, match="Unauthorized"):
                await client.delete_file("file123")
                
        finally:
            os.unlink(temp_file_path)