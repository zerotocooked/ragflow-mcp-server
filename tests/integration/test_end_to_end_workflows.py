"""End-to-end workflow tests for RAGFlow MCP Server."""

import pytest
import asyncio
import tempfile
import os
import json
import time
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any, List

from ragflow_mcp_server.server import RAGFlowMCPServer
from ragflow_mcp_server.client import RAGFlowClient
from ragflow_mcp_server.config import RAGFlowConfig
from ragflow_mcp_server.models import (
    UploadResult, UpdateResult, SearchResult, SearchItem,
    ListFilesResult, FileInfo, DeleteResult, DatasetsResult, DatasetInfo
)
from ragflow_mcp_server.errors import APIError, ConfigurationError, AuthenticationError


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
    """Create mock RAGFlow client for end-to-end testing."""
    client = AsyncMock()
    
    # Simulate a realistic file storage
    client._files = {}
    client._datasets = {
        "dataset123": {
            "id": "dataset123",
            "name": "Test Dataset",
            "description": "A test dataset",
            "file_count": 0
        }
    }
    client._file_counter = 0
    
    async def mock_upload_file(file_path: str, dataset_id: str, **kwargs):
        client._file_counter += 1
        file_id = f"file_{client._file_counter}"
        
        # Simulate file reading
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        client._files[file_id] = {
            "id": file_id,
            "name": os.path.basename(file_path),
            "content": content,
            "size": len(content),
            "dataset_id": dataset_id,
            "status": "completed",
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        client._datasets[dataset_id]["file_count"] += 1
        
        return UploadResult(
            file_id=file_id,
            status="success",
            message="File uploaded successfully",
            chunk_count=len(content) // 100 + 1
        )
    
    async def mock_update_file(file_id: str, file_path: str, **kwargs):
        if file_id not in client._files:
            raise APIError(f"File not found: {file_id}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        client._files[file_id]["content"] = content
        client._files[file_id]["size"] = len(content)
        
        return UpdateResult(
            file_id=file_id,
            status="success",
            message="File updated successfully"
        )
    
    async def mock_search(query: str, dataset_id: str, **kwargs):
        limit = kwargs.get('limit', 10)
        similarity_threshold = kwargs.get('similarity_threshold', 0.1)
        
        results = []
        for file_id, file_info in client._files.items():
            if file_info["dataset_id"] == dataset_id:
                # Simple text matching for mock
                if query.lower() in file_info["content"].lower():
                    score = 0.9 - len(results) * 0.1  # Decreasing relevance
                    if score >= similarity_threshold and len(results) < limit:
                        results.append(SearchItem(
                            content=file_info["content"][:200] + "...",
                            score=score,
                            file_name=file_info["name"],
                            file_id=file_id,
                            chunk_id=f"chunk_{len(results)}"
                        ))
        
        return SearchResult(
            results=results,
            total_count=len(results),
            query_time=0.123
        )
    
    async def mock_list_files(dataset_id: str, **kwargs):
        limit = kwargs.get('limit', 100)
        offset = kwargs.get('offset', 0)
        
        dataset_files = [
            FileInfo(
                file_id=file_id,
                name=file_info["name"],
                size=file_info["size"],
                created_at=file_info["created_at"],
                status=file_info["status"]
            )
            for file_id, file_info in client._files.items()
            if file_info["dataset_id"] == dataset_id
        ]
        
        paginated_files = dataset_files[offset:offset + limit]
        
        return ListFilesResult(
            files=paginated_files,
            total_count=len(dataset_files)
        )
    
    async def mock_delete_file(file_id: str):
        if file_id not in client._files:
            raise APIError(f"File not found: {file_id}")
        
        dataset_id = client._files[file_id]["dataset_id"]
        client._datasets[dataset_id]["file_count"] -= 1
        del client._files[file_id]
        
        return DeleteResult(
            file_id=file_id,
            status="success",
            message="File deleted successfully"
        )
    
    async def mock_get_datasets():
        datasets = [
            DatasetInfo(
                dataset_id=dataset_id,
                name=dataset_info["name"],
                description=dataset_info["description"],
                file_count=dataset_info["file_count"],
                created_at="2024-01-01T00:00:00Z"
            )
            for dataset_id, dataset_info in client._datasets.items()
        ]
        
        return DatasetsResult(
            datasets=datasets,
            total_count=len(datasets)
        )
    
    client.upload_file = mock_upload_file
    client.update_file = mock_update_file
    client.search = mock_search
    client.list_files = mock_list_files
    client.delete_file = mock_delete_file
    client.get_datasets = mock_get_datasets
    
    return client


@pytest.fixture
def server(config, mock_client):
    """Create test server with mocked client."""
    with patch('ragflow_mcp_server.server.RAGFlowClient', return_value=mock_client):
        server = RAGFlowMCPServer(config)
        server.client = mock_client
        return server


class TestEndToEndWorkflows:
    """End-to-end workflow tests."""
    
    @pytest.mark.asyncio
    async def test_complete_document_lifecycle(self, server):
        """Test complete document lifecycle: create -> upload -> search -> update -> search -> delete."""
        # Step 1: Create a document
        document_content = """
        This is a comprehensive test document for RAGFlow MCP Server.
        It contains information about artificial intelligence, machine learning,
        and natural language processing. The document will be used to test
        the complete workflow of uploading, searching, updating, and deleting.
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write(document_content)
            original_file_path = tmp.name
        
        try:
            # Step 2: Upload the document
            upload_result = await server._call_tool("ragflow_upload_file", {
                "file_path": original_file_path,
                "dataset_id": "dataset123",
                "chunk_method": "naive"
            })
            
            assert len(upload_result) == 1
            upload_text = upload_result[0].text
            assert "File uploaded successfully!" in upload_text
            
            # Extract file ID
            import re
            file_id_match = re.search(r'File ID: (\w+)', upload_text)
            assert file_id_match
            file_id = file_id_match.group(1)
            
            # Step 3: Search for content in the uploaded document
            search_result = await server._call_tool("ragflow_search", {
                "query": "artificial intelligence",
                "dataset_id": "dataset123",
                "limit": 5,
                "similarity_threshold": 0.1
            })
            
            assert len(search_result) == 1
            search_text = search_result[0].text
            assert "Found 1 results" in search_text
            assert "artificial intelligence" in search_text.lower()
            
            # Step 4: Update the document with new content
            updated_content = document_content + """
            
            UPDATED SECTION:
            This document has been updated to include information about
            deep learning, neural networks, and computer vision.
            The update demonstrates the file update functionality.
            """
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
                tmp.write(updated_content)
                updated_file_path = tmp.name
            
            try:
                update_result = await server._call_tool("ragflow_update_file", {
                    "file_id": file_id,
                    "file_path": updated_file_path
                })
                
                assert len(update_result) == 1
                update_text = update_result[0].text
                assert "File updated successfully!" in update_text
                assert file_id in update_text
                
                # Step 5: Search for new content after update
                updated_search_result = await server._call_tool("ragflow_search", {
                    "query": "deep learning",
                    "dataset_id": "dataset123"
                })
                
                assert len(updated_search_result) == 1
                updated_search_text = updated_search_result[0].text
                assert "Found 1 results" in updated_search_text
                assert "deep learning" in updated_search_text.lower()
                
                # Step 6: Verify file listing shows the updated file
                list_result = await server._call_tool("ragflow_list_files", {
                    "dataset_id": "dataset123"
                })
                
                assert len(list_result) == 1
                list_text = list_result[0].text
                assert "Found 1 files" in list_text
                assert file_id in list_text
                
                # Step 7: Delete the file
                delete_result = await server._call_tool("ragflow_delete_file", {
                    "file_id": file_id
                })
                
                assert len(delete_result) == 1
                delete_text = delete_result[0].text
                assert "File deleted successfully!" in delete_text
                
                # Step 8: Verify file is deleted
                final_list_result = await server._call_tool("ragflow_list_files", {
                    "dataset_id": "dataset123"
                })
                
                assert len(final_list_result) == 1
                final_list_text = final_list_result[0].text
                assert "Found 0 files" in final_list_text
                
                # Step 9: Verify search returns no results after deletion
                final_search_result = await server._call_tool("ragflow_search", {
                    "query": "artificial intelligence",
                    "dataset_id": "dataset123"
                })
                
                assert len(final_search_result) == 1
                final_search_text = final_search_result[0].text
                assert "Found 0 results" in final_search_text
                
            finally:
                os.unlink(updated_file_path)
                
        finally:
            os.unlink(original_file_path)
    
    @pytest.mark.asyncio
    async def test_multi_document_knowledge_base_workflow(self, server):
        """Test workflow with multiple documents forming a knowledge base."""
        # Create multiple related documents
        documents = {
            "ai_basics.txt": """
            Artificial Intelligence (AI) is a branch of computer science that aims to create
            intelligent machines that can perform tasks that typically require human intelligence.
            AI includes machine learning, natural language processing, and computer vision.
            """,
            "machine_learning.txt": """
            Machine Learning (ML) is a subset of artificial intelligence that enables computers
            to learn and improve from experience without being explicitly programmed.
            Common ML algorithms include linear regression, decision trees, and neural networks.
            """,
            "deep_learning.txt": """
            Deep Learning is a subset of machine learning that uses artificial neural networks
            with multiple layers to model and understand complex patterns in data.
            Popular frameworks include TensorFlow, PyTorch, and Keras.
            """,
            "nlp.txt": """
            Natural Language Processing (NLP) is a field of AI that focuses on the interaction
            between computers and human language. NLP techniques include tokenization,
            sentiment analysis, and language translation.
            """
        }
        
        temp_files = {}
        file_ids = []
        
        try:
            # Step 1: Upload all documents
            for filename, content in documents.items():
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
                    tmp.write(content)
                    temp_files[filename] = tmp.name
                
                upload_result = await server._call_tool("ragflow_upload_file", {
                    "file_path": temp_files[filename],
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
            
            # Step 2: Verify all files are listed
            list_result = await server._call_tool("ragflow_list_files", {
                "dataset_id": "dataset123"
            })
            
            assert len(list_result) == 1
            list_text = list_result[0].text
            assert "Found 4 files" in list_text
            
            # Step 3: Test cross-document search queries
            search_queries = [
                ("artificial intelligence", 2),  # Should find AI basics and ML
                ("neural networks", 2),  # Should find ML and Deep Learning
                ("TensorFlow", 1),  # Should find only Deep Learning
                ("sentiment analysis", 1),  # Should find only NLP
                ("computer science", 1),  # Should find only AI basics
            ]
            
            for query, expected_count in search_queries:
                search_result = await server._call_tool("ragflow_search", {
                    "query": query,
                    "dataset_id": "dataset123",
                    "limit": 10
                })
                
                assert len(search_result) == 1
                search_text = search_result[0].text
                assert f"Found {expected_count} results" in search_text
                assert query.lower() in search_text.lower()
            
            # Step 4: Test comprehensive search
            comprehensive_search = await server._call_tool("ragflow_search", {
                "query": "learning",
                "dataset_id": "dataset123",
                "limit": 10
            })
            
            assert len(comprehensive_search) == 1
            comprehensive_text = comprehensive_search[0].text
            # Should find multiple documents containing "learning"
            assert "Found" in comprehensive_text
            assert int(re.search(r'Found (\d+) results', comprehensive_text).group(1)) >= 2
            
            # Step 5: Update one document and verify search results change
            updated_ml_content = documents["machine_learning.txt"] + """
            
            UPDATED: Recent advances in machine learning include transformer architectures,
            attention mechanisms, and large language models like GPT and BERT.
            """
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
                tmp.write(updated_ml_content)
                updated_ml_path = tmp.name
            
            try:
                # Update the ML document (second file uploaded)
                update_result = await server._call_tool("ragflow_update_file", {
                    "file_id": file_ids[1],  # ML document
                    "file_path": updated_ml_path
                })
                
                assert len(update_result) == 1
                assert "File updated successfully!" in update_result[0].text
                
                # Search for new content
                transformer_search = await server._call_tool("ragflow_search", {
                    "query": "transformer architectures",
                    "dataset_id": "dataset123"
                })
                
                assert len(transformer_search) == 1
                transformer_text = transformer_search[0].text
                assert "Found 1 results" in transformer_text
                assert "transformer" in transformer_text.lower()
                
            finally:
                os.unlink(updated_ml_path)
            
            # Step 6: Delete documents one by one and verify search results
            for i, file_id in enumerate(file_ids):
                delete_result = await server._call_tool("ragflow_delete_file", {
                    "file_id": file_id
                })
                
                assert len(delete_result) == 1
                assert "File deleted successfully!" in delete_result[0].text
                
                # Verify file count decreases
                list_result = await server._call_tool("ragflow_list_files", {
                    "dataset_id": "dataset123"
                })
                
                remaining_files = 4 - (i + 1)
                assert f"Found {remaining_files} files" in list_result[0].text
            
            # Step 7: Verify all files are deleted
            final_list = await server._call_tool("ragflow_list_files", {
                "dataset_id": "dataset123"
            })
            
            assert "Found 0 files" in final_list[0].text
            
        finally:
            for file_path in temp_files.values():
                if os.path.exists(file_path):
                    os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_dataset_management_workflow(self, server):
        """Test dataset management workflow."""
        # Step 1: Get initial datasets
        initial_datasets = await server._call_tool("ragflow_get_datasets", {})
        
        assert len(initial_datasets) == 1
        datasets_text = initial_datasets[0].text
        assert "Found 1 datasets" in datasets_text
        assert "Test Dataset" in datasets_text
        
        # Step 2: Upload files to the dataset
        test_files = []
        for i in range(3):
            content = f"Test document {i} for dataset management workflow."
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{i}.txt', delete=False) as tmp:
                tmp.write(content)
                test_files.append(tmp.name)
        
        try:
            file_ids = []
            for file_path in test_files:
                upload_result = await server._call_tool("ragflow_upload_file", {
                    "file_path": file_path,
                    "dataset_id": "dataset123"
                })
                
                assert "File uploaded successfully!" in upload_result[0].text
                
                # Extract file ID
                import re
                file_id_match = re.search(r'File ID: (\w+)', upload_result[0].text)
                file_ids.append(file_id_match.group(1))
            
            # Step 3: Verify dataset file count increased
            updated_datasets = await server._call_tool("ragflow_get_datasets", {})
            updated_text = updated_datasets[0].text
            assert "3 files" in updated_text
            
            # Step 4: List files in dataset
            list_result = await server._call_tool("ragflow_list_files", {
                "dataset_id": "dataset123"
            })
            
            assert "Found 3 files" in list_result[0].text
            
            # Step 5: Search across all files in dataset
            search_result = await server._call_tool("ragflow_search", {
                "query": "dataset management",
                "dataset_id": "dataset123"
            })
            
            assert "Found 3 results" in search_result[0].text
            
            # Step 6: Clean up - delete all files
            for file_id in file_ids:
                delete_result = await server._call_tool("ragflow_delete_file", {
                    "file_id": file_id
                })
                assert "File deleted successfully!" in delete_result[0].text
            
            # Step 7: Verify dataset is empty
            final_datasets = await server._call_tool("ragflow_get_datasets", {})
            final_text = final_datasets[0].text
            assert "0 files" in final_text
            
        finally:
            for file_path in test_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, server):
        """Test error recovery in workflows."""
        # Step 1: Try to upload non-existent file
        upload_error = await server._call_tool("ragflow_upload_file", {
            "file_path": "/nonexistent/file.txt",
            "dataset_id": "dataset123"
        })
        
        assert "Error:" in upload_error[0].text
        assert "File not found" in upload_error[0].text
        
        # Step 2: Upload a valid file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("Error recovery test content")
            temp_file_path = tmp.name
        
        try:
            upload_result = await server._call_tool("ragflow_upload_file", {
                "file_path": temp_file_path,
                "dataset_id": "dataset123"
            })
            
            assert "File uploaded successfully!" in upload_result[0].text
            
            # Extract file ID
            import re
            file_id_match = re.search(r'File ID: (\w+)', upload_result[0].text)
            file_id = file_id_match.group(1)
            
            # Step 3: Try to update with non-existent file
            update_error = await server._call_tool("ragflow_update_file", {
                "file_id": file_id,
                "file_path": "/nonexistent/update.txt"
            })
            
            assert "Error:" in update_error[0].text
            assert "File not found" in update_error[0].text
            
            # Step 4: Verify original file is still intact
            search_result = await server._call_tool("ragflow_search", {
                "query": "error recovery",
                "dataset_id": "dataset123"
            })
            
            assert "Found 1 results" in search_result[0].text
            
            # Step 5: Try to delete non-existent file
            delete_error = await server._call_tool("ragflow_delete_file", {
                "file_id": "nonexistent_file"
            })
            
            assert "Error:" in delete_error[0].text
            assert "File not found" in delete_error[0].text
            
            # Step 6: Delete the actual file
            delete_result = await server._call_tool("ragflow_delete_file", {
                "file_id": file_id
            })
            
            assert "File deleted successfully!" in delete_result[0].text
            
            # Step 7: Try to search in non-existent dataset
            search_error = await server._call_tool("ragflow_search", {
                "query": "test",
                "dataset_id": "nonexistent_dataset"
            })
            
            assert "Error:" in search_error[0].text
            
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_concurrent_workflow_operations(self, server):
        """Test concurrent operations in workflows."""
        # Create multiple test files
        temp_files = []
        for i in range(10):
            content = f"Concurrent workflow test document {i} with unique content."
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{i}.txt', delete=False) as tmp:
                tmp.write(content)
                temp_files.append(tmp.name)
        
        try:
            # Step 1: Upload all files concurrently
            upload_tasks = [
                server._call_tool("ragflow_upload_file", {
                    "file_path": file_path,
                    "dataset_id": "dataset123"
                })
                for file_path in temp_files
            ]
            
            upload_results = await asyncio.gather(*upload_tasks)
            
            # Verify all uploads succeeded
            file_ids = []
            for result in upload_results:
                assert "File uploaded successfully!" in result[0].text
                
                import re
                file_id_match = re.search(r'File ID: (\w+)', result[0].text)
                file_ids.append(file_id_match.group(1))
            
            # Step 2: Perform concurrent searches
            search_tasks = [
                server._call_tool("ragflow_search", {
                    "query": f"document {i}",
                    "dataset_id": "dataset123"
                })
                for i in range(10)
            ]
            
            search_results = await asyncio.gather(*search_tasks)
            
            # Verify searches found relevant documents
            for i, result in enumerate(search_results):
                assert "Found" in result[0].text
                assert f"document {i}" in result[0].text.lower()
            
            # Step 3: Concurrent file listing and dataset operations
            concurrent_tasks = [
                server._call_tool("ragflow_list_files", {"dataset_id": "dataset123"}),
                server._call_tool("ragflow_get_datasets", {}),
                server._call_tool("ragflow_search", {
                    "query": "concurrent workflow",
                    "dataset_id": "dataset123"
                })
            ]
            
            concurrent_results = await asyncio.gather(*concurrent_tasks)
            
            # Verify concurrent operations
            assert "Found 10 files" in concurrent_results[0][0].text
            assert "Found 1 datasets" in concurrent_results[1][0].text
            assert "Found 10 results" in concurrent_results[2][0].text
            
            # Step 4: Delete files concurrently
            delete_tasks = [
                server._call_tool("ragflow_delete_file", {"file_id": file_id})
                for file_id in file_ids
            ]
            
            delete_results = await asyncio.gather(*delete_tasks)
            
            # Verify all deletions succeeded
            for result in delete_results:
                assert "File deleted successfully!" in result[0].text
            
            # Step 5: Verify all files are deleted
            final_list = await server._call_tool("ragflow_list_files", {
                "dataset_id": "dataset123"
            })
            
            assert "Found 0 files" in final_list[0].text
            
        finally:
            for file_path in temp_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_large_scale_workflow(self, server):
        """Test large-scale workflow with many documents."""
        # Create a larger number of documents
        num_docs = 25
        temp_files = []
        
        # Create documents with varied content
        topics = ["AI", "ML", "DL", "NLP", "CV"]
        
        for i in range(num_docs):
            topic = topics[i % len(topics)]
            content = f"""
            Document {i} about {topic}.
            This document contains information about {topic.lower()} concepts,
            algorithms, and applications. Document ID: {i}.
            Topic: {topic}. Content length: medium.
            """
            
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{i}.txt', delete=False) as tmp:
                tmp.write(content)
                temp_files.append(tmp.name)
        
        try:
            start_time = time.time()
            
            # Step 1: Batch upload all documents
            upload_tasks = [
                server._call_tool("ragflow_upload_file", {
                    "file_path": file_path,
                    "dataset_id": "dataset123"
                })
                for file_path in temp_files
            ]
            
            upload_results = await asyncio.gather(*upload_tasks)
            upload_time = time.time() - start_time
            
            # Verify all uploads
            file_ids = []
            for result in upload_results:
                assert "File uploaded successfully!" in result[0].text
                
                import re
                file_id_match = re.search(r'File ID: (\w+)', result[0].text)
                file_ids.append(file_id_match.group(1))
            
            # Step 2: Verify file count
            list_result = await server._call_tool("ragflow_list_files", {
                "dataset_id": "dataset123"
            })
            
            assert f"Found {num_docs} files" in list_result[0].text
            
            # Step 3: Test topic-based searches
            search_start = time.time()
            
            topic_searches = []
            for topic in topics:
                search_result = await server._call_tool("ragflow_search", {
                    "query": topic,
                    "dataset_id": "dataset123",
                    "limit": 10
                })
                topic_searches.append(search_result)
            
            search_time = time.time() - search_start
            
            # Verify search results
            for i, result in enumerate(topic_searches):
                topic = topics[i]
                assert "Found" in result[0].text
                assert topic in result[0].text
            
            # Step 4: Test pagination with large result set
            all_search = await server._call_tool("ragflow_search", {
                "query": "Document",
                "dataset_id": "dataset123",
                "limit": 50  # Should find all documents
            })
            
            assert f"Found {num_docs} results" in all_search[0].text
            
            # Step 5: Batch delete all documents
            delete_start = time.time()
            
            delete_tasks = [
                server._call_tool("ragflow_delete_file", {"file_id": file_id})
                for file_id in file_ids
            ]
            
            delete_results = await asyncio.gather(*delete_tasks)
            delete_time = time.time() - delete_start
            
            # Verify all deletions
            for result in delete_results:
                assert "File deleted successfully!" in result[0].text
            
            # Step 6: Verify cleanup
            final_list = await server._call_tool("ragflow_list_files", {
                "dataset_id": "dataset123"
            })
            
            assert "Found 0 files" in final_list[0].text
            
            # Performance assertions
            total_time = time.time() - start_time
            assert upload_time < 5.0, f"Upload time {upload_time:.2f}s too slow"
            assert search_time < 2.0, f"Search time {search_time:.2f}s too slow"
            assert delete_time < 3.0, f"Delete time {delete_time:.2f}s too slow"
            assert total_time < 10.0, f"Total workflow time {total_time:.2f}s too slow"
            
        finally:
            for file_path in temp_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)