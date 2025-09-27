"""MCP protocol compliance tests for RAGFlow MCP Server."""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, patch
from typing import Dict, Any, List

from ragflow_mcp_server.server import RAGFlowMCPServer
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
    """Create mock RAGFlow client."""
    client = AsyncMock()
    
    # Setup default mock responses
    client.upload_file.return_value = UploadResult(
        file_id="file123",
        status="success",
        message="File uploaded successfully",
        chunk_count=5
    )
    
    client.update_file.return_value = UpdateResult(
        file_id="file123",
        status="success",
        message="File updated successfully"
    )
    
    client.search.return_value = SearchResult(
        results=[
            SearchItem(
                content="Test search result",
                score=0.95,
                file_name="test.txt",
                file_id="file123",
                chunk_id="chunk1"
            )
        ],
        total_count=1,
        query_time=0.123
    )
    
    client.list_files.return_value = ListFilesResult(
        files=[
            FileInfo(
                file_id="file123",
                name="test.txt",
                size=1024,
                created_at="2024-01-01T00:00:00Z",
                status="completed"
            )
        ],
        total_count=1
    )
    
    client.delete_file.return_value = DeleteResult(
        file_id="file123",
        status="success",
        message="File deleted successfully"
    )
    
    client.get_datasets.return_value = DatasetsResult(
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
    
    return client


@pytest.fixture
def server(config, mock_client):
    """Create test server with mocked client."""
    with patch('ragflow_mcp_server.server.RAGFlowClient', return_value=mock_client):
        server = RAGFlowMCPServer(config)
        server.client = mock_client
        return server


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance."""
    
    @pytest.mark.asyncio
    async def test_list_tools_response_format(self, server):
        """Test that list_tools returns properly formatted MCP response."""
        tools = await server._list_tools()
        
        # Verify response is a list
        assert isinstance(tools, list)
        
        # Verify we have the expected number of tools
        expected_tools = [
            "ragflow_upload_file",
            "ragflow_update_file", 
            "ragflow_search",
            "ragflow_list_files",
            "ragflow_delete_file",
            "ragflow_get_datasets"
        ]
        assert len(tools) == len(expected_tools)
        
        # Verify each tool has required MCP fields
        for tool in tools:
            # Check required fields exist
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'inputSchema')
            
            # Verify field types
            assert isinstance(tool.name, str)
            assert isinstance(tool.description, str)
            assert isinstance(tool.inputSchema, dict)
            
            # Verify tool name is in expected list
            assert tool.name in expected_tools
            
            # Verify input schema structure
            schema = tool.inputSchema
            assert schema.get('type') == 'object'
            assert 'properties' in schema
            assert 'required' in schema
            assert isinstance(schema['properties'], dict)
            assert isinstance(schema['required'], list)
    
    @pytest.mark.asyncio
    async def test_tool_input_schemas_compliance(self, server):
        """Test that tool input schemas comply with JSON Schema specification."""
        tools = await server._list_tools()
        
        for tool in tools:
            schema = tool.inputSchema
            
            # Verify JSON Schema compliance
            assert schema['type'] == 'object'
            
            # Check properties structure
            properties = schema['properties']
            for prop_name, prop_schema in properties.items():
                assert isinstance(prop_name, str)
                assert isinstance(prop_schema, dict)
                assert 'type' in prop_schema
                assert 'description' in prop_schema
                
                # Verify property types are valid JSON Schema types
                valid_types = ['string', 'number', 'integer', 'boolean', 'array', 'object']
                assert prop_schema['type'] in valid_types
            
            # Check required fields are valid
            required = schema['required']
            for req_field in required:
                assert req_field in properties
    
    @pytest.mark.asyncio
    async def test_upload_file_tool_schema(self, server):
        """Test upload file tool schema compliance."""
        tools = await server._list_tools()
        upload_tool = next(t for t in tools if t.name == "ragflow_upload_file")
        
        schema = upload_tool.inputSchema
        properties = schema['properties']
        required = schema['required']
        
        # Verify required parameters
        assert 'file_path' in required
        assert 'dataset_id' in required
        
        # Verify optional parameters
        assert 'chunk_method' in properties
        assert 'chunk_method' not in required
        
        # Verify parameter types
        assert properties['file_path']['type'] == 'string'
        assert properties['dataset_id']['type'] == 'string'
        assert properties['chunk_method']['type'] == 'string'
        
        # Verify descriptions exist
        assert 'description' in properties['file_path']
        assert 'description' in properties['dataset_id']
        assert 'description' in properties['chunk_method']
        
        # Verify enum values for chunk_method
        assert 'enum' in properties['chunk_method']
        expected_methods = [
            "naive", "manual", "qa", "table", "paper", "book", "laws",
            "presentation", "picture", "one", "knowledge_graph", "email"
        ]
        assert set(properties['chunk_method']['enum']) == set(expected_methods)
    
    @pytest.mark.asyncio
    async def test_search_tool_schema(self, server):
        """Test search tool schema compliance."""
        tools = await server._list_tools()
        search_tool = next(t for t in tools if t.name == "ragflow_search")
        
        schema = search_tool.inputSchema
        properties = schema['properties']
        required = schema['required']
        
        # Verify required parameters
        assert 'query' in required
        assert 'dataset_id' in required
        
        # Verify optional parameters
        assert 'limit' in properties
        assert 'similarity_threshold' in properties
        assert 'limit' not in required
        assert 'similarity_threshold' not in required
        
        # Verify parameter types
        assert properties['query']['type'] == 'string'
        assert properties['dataset_id']['type'] == 'string'
        assert properties['limit']['type'] == 'integer'
        assert properties['similarity_threshold']['type'] == 'number'
        
        # Verify constraints
        assert properties['limit']['minimum'] == 1
        assert properties['limit']['maximum'] == 100
        assert properties['similarity_threshold']['minimum'] == 0.0
        assert properties['similarity_threshold']['maximum'] == 1.0
    
    @pytest.mark.asyncio
    async def test_call_tool_response_format(self, server):
        """Test that call_tool returns properly formatted MCP response."""
        import tempfile
        import os
        
        # Create temporary file for testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("test content")
            temp_file_path = tmp.name
        
        try:
            # Test each tool's response format
            test_cases = [
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
                ("ragflow_get_datasets", {}),
                ("ragflow_delete_file", {
                    "file_id": "file123"
                }),
                ("ragflow_update_file", {
                    "file_id": "file123",
                    "file_path": temp_file_path
                })
            ]
            
            for tool_name, arguments in test_cases:
                result = await server._call_tool(tool_name, arguments)
                
                # Verify response format
                assert isinstance(result, list)
                assert len(result) >= 1
                
                # Verify each response item has required fields
                for item in result:
                    assert hasattr(item, 'type')
                    assert hasattr(item, 'text')
                    assert item.type == 'text'
                    assert isinstance(item.text, str)
                    assert len(item.text) > 0
        
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_error_response_format(self, server):
        """Test that error responses follow MCP format."""
        # Test various error scenarios
        error_test_cases = [
            ("ragflow_upload_file", {}, "Missing required parameter"),
            ("ragflow_upload_file", {"file_path": ""}, "Empty parameter"),
            ("ragflow_search", {"query": "test"}, "Missing required parameter"),
            ("ragflow_search", {"query": "test", "dataset_id": "ds", "limit": 0}, "Invalid parameter value"),
            ("ragflow_list_files", {}, "Missing required parameter"),
            ("ragflow_delete_file", {}, "Missing required parameter"),
            ("ragflow_update_file", {"file_id": "123"}, "Missing required parameter")
        ]
        
        for tool_name, arguments, error_type in error_test_cases:
            result = await server._call_tool(tool_name, arguments)
            
            # Verify error response format
            assert isinstance(result, list)
            assert len(result) == 1
            
            error_item = result[0]
            assert hasattr(error_item, 'type')
            assert hasattr(error_item, 'text')
            assert error_item.type == 'text'
            assert isinstance(error_item.text, str)
            assert "Error:" in error_item.text
    
    @pytest.mark.asyncio
    async def test_parameter_validation_compliance(self, server):
        """Test parameter validation compliance with schemas."""
        import tempfile
        import os
        
        # Create temporary file for testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("test content")
            temp_file_path = tmp.name
        
        try:
            # Test valid parameters pass validation
            valid_test_cases = [
                ("ragflow_upload_file", {
                    "file_path": temp_file_path,
                    "dataset_id": "dataset123",
                    "chunk_method": "naive"
                }),
                ("ragflow_search", {
                    "query": "test query",
                    "dataset_id": "dataset123",
                    "limit": 10,
                    "similarity_threshold": 0.5
                }),
                ("ragflow_list_files", {
                    "dataset_id": "dataset123",
                    "limit": 50,
                    "offset": 0
                })
            ]
            
            for tool_name, arguments in valid_test_cases:
                result = await server._call_tool(tool_name, arguments)
                
                # Should not return validation errors
                assert len(result) == 1
                assert "Error:" not in result[0].text or "File not found" in result[0].text
            
            # Test invalid parameters fail validation
            invalid_test_cases = [
                ("ragflow_upload_file", {
                    "file_path": temp_file_path,
                    "dataset_id": "dataset123",
                    "chunk_method": "invalid_method"
                }, "chunk_method"),
                ("ragflow_search", {
                    "query": "test",
                    "dataset_id": "dataset123",
                    "limit": 101
                }, "limit"),
                ("ragflow_search", {
                    "query": "test",
                    "dataset_id": "dataset123",
                    "similarity_threshold": 1.5
                }, "similarity_threshold"),
                ("ragflow_list_files", {
                    "dataset_id": "dataset123",
                    "limit": 0
                }, "limit")
            ]
            
            for tool_name, arguments, invalid_param in invalid_test_cases:
                result = await server._call_tool(tool_name, arguments)
                
                # Should return validation error
                assert len(result) == 1
                assert "Error:" in result[0].text
                # Error message should mention the invalid parameter
                assert invalid_param in result[0].text.lower()
        
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_tool_descriptions_quality(self, server):
        """Test that tool descriptions are informative and follow conventions."""
        tools = await server._list_tools()
        
        for tool in tools:
            description = tool.description
            
            # Description should be non-empty
            assert len(description) > 0
            
            # Description should be informative (reasonable length)
            assert len(description) > 20
            
            # Description should start with a verb or action word
            first_word = description.split()[0].lower()
            action_words = ['upload', 'update', 'search', 'list', 'delete', 'get', 'retrieve', 'find']
            assert any(action_word in first_word for action_word in action_words)
            
            # Description should mention RAGFlow
            assert 'ragflow' in description.lower()
    
    @pytest.mark.asyncio
    async def test_parameter_descriptions_quality(self, server):
        """Test that parameter descriptions are informative."""
        tools = await server._list_tools()
        
        for tool in tools:
            properties = tool.inputSchema['properties']
            
            for param_name, param_schema in properties.items():
                description = param_schema['description']
                
                # Description should be non-empty
                assert len(description) > 0
                
                # Description should be informative
                assert len(description) > 10
                
                # Description should not just repeat the parameter name
                assert param_name.replace('_', ' ').lower() not in description.lower()
    
    @pytest.mark.asyncio
    async def test_response_text_formatting(self, server):
        """Test that response text is well-formatted and user-friendly."""
        import tempfile
        import os
        
        # Create temporary file for testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("test content")
            temp_file_path = tmp.name
        
        try:
            # Test successful responses
            success_test_cases = [
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
            
            for tool_name, arguments in success_test_cases:
                result = await server._call_tool(tool_name, arguments)
                
                assert len(result) == 1
                text = result[0].text
                
                # Text should be properly formatted
                assert len(text) > 0
                assert text.strip() == text  # No leading/trailing whitespace
                
                # Should contain relevant information
                if tool_name == "ragflow_upload_file":
                    assert "uploaded" in text.lower()
                    assert "file id" in text.lower()
                elif tool_name == "ragflow_search":
                    assert "found" in text.lower()
                    assert "results" in text.lower()
                elif tool_name == "ragflow_list_files":
                    assert "found" in text.lower()
                    assert "files" in text.lower()
                elif tool_name == "ragflow_get_datasets":
                    assert "found" in text.lower()
                    assert "datasets" in text.lower()
        
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_calls_compliance(self, server):
        """Test MCP compliance during concurrent tool calls."""
        import tempfile
        import os
        
        # Create temporary files
        temp_files = []
        for i in range(5):
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{i}.txt', delete=False) as tmp:
                tmp.write(f"concurrent test content {i}")
                temp_files.append(tmp.name)
        
        try:
            # Execute multiple tools concurrently
            tasks = []
            
            # Add various tool calls
            for i, file_path in enumerate(temp_files):
                tasks.append(server._call_tool("ragflow_upload_file", {
                    "file_path": file_path,
                    "dataset_id": "dataset123"
                }))
            
            for i in range(5):
                tasks.append(server._call_tool("ragflow_search", {
                    "query": f"concurrent test {i}",
                    "dataset_id": "dataset123"
                }))
            
            tasks.append(server._call_tool("ragflow_list_files", {
                "dataset_id": "dataset123"
            }))
            
            tasks.append(server._call_tool("ragflow_get_datasets", {}))
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks)
            
            # Verify all responses comply with MCP format
            assert len(results) == 12  # 5 uploads + 5 searches + 1 list + 1 datasets
            
            for result in results:
                # Each result should be a list of response items
                assert isinstance(result, list)
                assert len(result) >= 1
                
                # Each response item should have proper format
                for item in result:
                    assert hasattr(item, 'type')
                    assert hasattr(item, 'text')
                    assert item.type == 'text'
                    assert isinstance(item.text, str)
                    assert len(item.text) > 0
        
        finally:
            for file_path in temp_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_tool_name_conventions(self, server):
        """Test that tool names follow MCP conventions."""
        tools = await server._list_tools()
        
        for tool in tools:
            name = tool.name
            
            # Tool names should follow naming conventions
            assert name.startswith('ragflow_')
            assert '_' in name
            assert name.islower()
            assert name.replace('_', '').isalnum()
            
            # Should not contain spaces or special characters
            assert ' ' not in name
            assert not any(char in name for char in '!@#$%^&*()+=[]{}|;:,.<>?')
    
    @pytest.mark.asyncio
    async def test_schema_additionalProperties_compliance(self, server):
        """Test that schemas properly handle additionalProperties."""
        tools = await server._list_tools()
        
        for tool in tools:
            schema = tool.inputSchema
            
            # Should explicitly set additionalProperties to false for strict validation
            # or not set it at all (defaults to true for flexibility)
            if 'additionalProperties' in schema:
                assert isinstance(schema['additionalProperties'], bool)
    
    @pytest.mark.asyncio
    async def test_response_consistency(self, server):
        """Test that responses are consistent across multiple calls."""
        import tempfile
        import os
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("consistency test content")
            temp_file_path = tmp.name
        
        try:
            # Make multiple identical calls
            num_calls = 10
            results = []
            
            for i in range(num_calls):
                result = await server._call_tool("ragflow_search", {
                    "query": "consistency test",
                    "dataset_id": "dataset123"
                })
                results.append(result)
            
            # Verify all responses have consistent format
            for result in results:
                assert isinstance(result, list)
                assert len(result) == 1
                assert hasattr(result[0], 'type')
                assert hasattr(result[0], 'text')
                assert result[0].type == 'text'
                
                # Content should be consistent (same mock data)
                text = result[0].text
                assert "Found 1 results" in text
                assert "Test search result" in text
        
        finally:
            os.unlink(temp_file_path)