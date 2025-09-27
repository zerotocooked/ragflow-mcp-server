# RAGFlow MCP Server

A Model Context Protocol (MCP) server for integrating RAGFlow API with Cursor IDE, enabling seamless document management and semantic search capabilities directly within your development environment.

## Overview

This MCP server provides a bridge between Cursor IDE and RAGFlow, allowing developers to:

- **Upload and embed documents** into RAGFlow knowledge base
- **Update existing documents** and trigger automatic re-embedding
- **Search through documents** using semantic similarity
- **Manage files and datasets** with full CRUD operations
- **List and organize** your knowledge base content

## Features

- 🔄 **Async Operations**: All API calls are asynchronous for better performance
- 🔒 **Secure Authentication**: API key-based authentication with RAGFlow
- 🛡️ **Error Handling**: Comprehensive error handling with retry logic
- 📝 **Type Safety**: Full type hints and validation using Pydantic
- 🧪 **Well Tested**: Comprehensive unit and integration test suite
- 🔧 **Configurable**: Flexible configuration via environment variables

## Requirements

- Python 3.8+
- RAGFlow instance (local or remote)
- Cursor IDE with MCP support

## Installation

### From Source (Recommended)

```bash
git clone <repository-url>
cd ragflow-mcp-server
pip install -e .
```

This installs the package globally, allowing you to use `python -m ragflow_mcp_server` from any directory.

### Development Installation

```bash
git clone <repository-url>
cd ragflow-mcp-server
pip install -e ".[dev]"
```

### From PyPI (when available)

```bash
pip install ragflow-mcp-server
```

## Configuration

### Environment Variables

Create a `.env` file or set the following environment variables:

```bash
# Required
RAGFLOW_BASE_URL=http://localhost:9380
RAGFLOW_API_KEY=your_api_key_here

# Optional
RAGFLOW_DEFAULT_DATASET_ID=your_default_dataset_id
RAGFLOW_TIMEOUT=30
RAGFLOW_MAX_RETRIES=3
```

### Getting RAGFlow API Key

1. Access your RAGFlow web interface
2. Navigate to Settings → API Keys
3. Generate a new API key
4. Copy the key and set it as `RAGFLOW_API_KEY`

## Usage

### Running the Server

#### As a Python module
```bash
python -m ragflow_mcp_server
```

#### Direct execution
```bash
ragflow-mcp-server
```

#### With custom configuration
```bash
RAGFLOW_BASE_URL=http://your-ragflow-instance:9380 python -m ragflow_mcp_server
```

### MCP Configuration for Cursor IDE

Add the following configuration to your Cursor MCP settings file:

#### Basic Configuration
```json
{
  "mcpServers": {
    "ragflow": {
      "command": "python",
      "args": ["-m", "ragflow_mcp_server"],
      "env": {
        "RAGFLOW_BASE_URL": "http://localhost:9380",
        "RAGFLOW_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

#### Advanced Configuration
```json
{
  "mcpServers": {
    "ragflow": {
      "command": "python",
      "args": ["-m", "ragflow_mcp_server"],
      "env": {
        "RAGFLOW_BASE_URL": "http://localhost:9380",
        "RAGFLOW_API_KEY": "your_api_key_here",
        "RAGFLOW_DEFAULT_DATASET_ID": "your_dataset_id",
        "RAGFLOW_TIMEOUT": "60",
        "RAGFLOW_MAX_RETRIES": "5"
      }
    }
  }
}
```

## Available MCP Tools

### ragflow_upload_file
Upload and embed a new file into RAGFlow.

**Parameters:**
- `file_path` (string, required): Path to the file to upload
- `dataset_id` (string, required): Target dataset ID
- `chunk_method` (string, optional): Chunking method (default: "naive")

**Example:**
```
Upload document.pdf to dataset abc123 using intelligent chunking
```

### ragflow_update_file
Update an existing file and trigger re-embedding.

**Parameters:**
- `file_id` (string, required): ID of the file to update
- `file_path` (string, required): Path to the new file content

**Example:**
```
Update file xyz789 with new content from updated_document.pdf
```

### ragflow_search
Search through the RAGFlow knowledge base.

**Parameters:**
- `query` (string, required): Search query
- `dataset_id` (string, required): Dataset to search in
- `limit` (integer, optional): Maximum results (default: 10)
- `similarity_threshold` (float, optional): Minimum similarity score (default: 0.1)

**Example:**
```
Search for "machine learning algorithms" in dataset abc123 with limit 5
```

### ragflow_list_files
List all files in a dataset.

**Parameters:**
- `dataset_id` (string, required): Dataset ID to list files from

**Example:**
```
List all files in dataset abc123
```

### ragflow_delete_file
Delete a file from RAGFlow.

**Parameters:**
- `file_id` (string, required): ID of the file to delete

**Example:**
```
Delete file xyz789
```

### ragflow_get_datasets
Get list of available datasets.

**Parameters:** None

**Example:**
```
Get all available datasets
```

## Usage Examples

### Basic Workflow

1. **Get available datasets:**
   ```
   Use ragflow_get_datasets to see available datasets
   ```

2. **Upload a document:**
   ```
   Use ragflow_upload_file with file_path="./docs/manual.pdf" and dataset_id="your_dataset_id"
   ```

3. **Search for information:**
   ```
   Use ragflow_search with query="how to configure authentication" and dataset_id="your_dataset_id"
   ```

4. **Update a document:**
   ```
   Use ragflow_update_file with file_id="file123" and file_path="./docs/updated_manual.pdf"
   ```

### Integration with Development Workflow

- **Documentation Search**: Quickly find relevant documentation while coding
- **Code Context**: Upload project documentation and search for implementation details
- **Knowledge Management**: Keep your team's knowledge base up-to-date with latest documents

## Development

### Project Structure

```
ragflow_mcp_server/
├── __init__.py          # Package initialization
├── __main__.py          # CLI entry point
├── server.py            # MCP server implementation
├── client.py            # RAGFlow API client
├── config.py            # Configuration management
├── errors.py            # Custom exceptions
└── models.py            # Data models
```

### Setting Up Development Environment

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ragflow-mcp-server
   ```

2. **Install development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

3. **Set up pre-commit hooks (optional):**
   ```bash
   pre-commit install
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ragflow_mcp_server

# Run specific test categories
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black ragflow_mcp_server/
isort ragflow_mcp_server/

# Type checking
mypy ragflow_mcp_server/

# Linting
flake8 ragflow_mcp_server/
```

### Testing with RAGFlow

For integration testing, you'll need a running RAGFlow instance:

1. **Start RAGFlow locally:**
   ```bash
   # Follow RAGFlow installation instructions
   docker-compose up -d
   ```

2. **Set test environment variables:**
   ```bash
   export RAGFLOW_BASE_URL=http://localhost:9380
   export RAGFLOW_API_KEY=your_test_api_key
   ```

3. **Run integration tests:**
   ```bash
   pytest tests/integration/
   ```

## Troubleshooting

### Common Issues

#### Connection Errors
```
Error: Cannot connect to RAGFlow at http://localhost:9380
```
**Solution:** Ensure RAGFlow is running and accessible at the configured URL.

#### Authentication Errors
```
Error: Authentication failed with RAGFlow API
```
**Solution:** Verify your API key is correct and has necessary permissions.

#### File Upload Errors
```
Error: File upload failed - file too large
```
**Solution:** Check RAGFlow's file size limits and ensure your file meets the requirements.

#### Dataset Not Found
```
Error: Dataset 'abc123' not found
```
**Solution:** Use `ragflow_get_datasets` to list available datasets and verify the ID.

### Debug Mode

Enable debug logging by setting the environment variable:
```bash
export RAGFLOW_LOG_LEVEL=DEBUG
python -m ragflow_mcp_server
```

### Getting Help

- Check the [RAGFlow documentation](https://ragflow.io/docs) for API-specific issues
- Review the [MCP specification](https://modelcontextprotocol.io/docs) for protocol-related questions
- Open an issue in this repository for bugs or feature requests

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Format your code (`black . && isort .`)
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

### v0.1.0
- Initial release
- Basic MCP server implementation
- RAGFlow API integration
- File upload, update, search, and management operations
- Comprehensive test suite