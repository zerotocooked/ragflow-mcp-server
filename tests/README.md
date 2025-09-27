# RAGFlow MCP Server Tests

This directory contains organized tests for the RAGFlow MCP Server.

## Test Structure

### 🧪 Individual Test Files

- **`test_basic_functionality.py`** - Basic connectivity, upload, list, and search tests
- **`test_search_functionality.py`** - Comprehensive search and semantic testing  
- **`test_file_operations.py`** - File lifecycle tests (upload, update, delete, duplicates)
- **`test_comprehensive.py`** - Full integration test covering all functionality

### 🚀 Test Runner

- **`run_all_tests.py`** - Runs all tests in order and provides summary

## Running Tests

### Run All Tests
```bash
python tests/run_all_tests.py
```

### Run Individual Tests
```bash
# Basic functionality
python tests/test_basic_functionality.py

# Search functionality  
python tests/test_search_functionality.py

# File operations
python tests/test_file_operations.py

# Comprehensive integration test
python tests/test_comprehensive.py
```

## Prerequisites

1. **RAGFlow server running** on configured URL (default: http://localhost:9380)
2. **Valid API key** in `.env` file
3. **At least one dataset** available in RAGFlow
4. **Environment configured** with `RAGFLOW_DEFAULT_DATASET_ID`

## Test Coverage

### ✅ Functionality Tested

- **Connectivity** - Server connection and dataset listing
- **File Upload** - Single file upload with automatic embedding
- **File Status** - Real-time processing status tracking
- **File Listing** - Dataset file enumeration with metadata
- **Search (RAG)** - Semantic content search with similarity scoring
- **File Update** - Content replacement with re-embedding
- **File Deletion** - Safe file removal
- **Duplicate Handling** - Multiple uploads of same content
- **Error Handling** - Validation and API error management

### 🎯 Test Types

- **Unit Tests** - Individual function testing
- **Integration Tests** - Multi-component workflows
- **End-to-End Tests** - Complete user scenarios
- **Performance Tests** - Response time validation

## Expected Results

All tests should pass with:
- ✅ Upload times < 1 second
- ✅ Search times < 2 seconds  
- ✅ Processing completion within 30 seconds
- ✅ Accurate semantic search results
- ✅ Proper file lifecycle management

## Troubleshooting

### Common Issues

1. **Connection Failed** - Check RAGFlow server is running and URL is correct
2. **Authentication Error** - Verify API key in `.env` file
3. **No Datasets** - Create at least one dataset in RAGFlow UI
4. **Timeout Errors** - Increase `RAGFLOW_TIMEOUT` in configuration
5. **Search No Results** - Wait longer for document processing to complete

### Debug Mode

Set environment variable for detailed logging:
```bash
export RAGFLOW_LOG_LEVEL=DEBUG
python tests/test_basic_functionality.py
```