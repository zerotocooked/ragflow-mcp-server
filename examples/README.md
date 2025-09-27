# RAGFlow MCP Server Examples

This directory contains example configurations and usage patterns for the RAGFlow MCP Server.

## Files Overview

### Configuration Examples

- **`.env.example`** - Environment variables template
- **`cursor_mcp_settings.json`** - Complete MCP configuration for Cursor IDE
- **`cursor_mcp_config.json`** - Alternative MCP configuration format
- **`docker-compose.yml`** - Docker setup for RAGFlow and MCP server

### Usage Examples

- **`usage_examples.py`** - Python script demonstrating programmatic usage
- **`sample_document.txt`** - Sample document for testing (created by usage_examples.py)

## Quick Start

### 1. Set up Environment

Copy the environment template and fill in your values:
```bash
cp .env.example ../.env
# Edit .env with your RAGFlow configuration
```

### 2. Configure Cursor IDE

Copy the MCP configuration to your Cursor settings:
```bash
# Copy the content of cursor_mcp_settings.json to your Cursor MCP configuration
```

### 3. Test the Setup

Run the usage examples to verify everything works:
```bash
cd ..
python examples/usage_examples.py
```

## Configuration Details

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RAGFLOW_BASE_URL` | Yes | - | RAGFlow instance URL |
| `RAGFLOW_API_KEY` | Yes | - | Your RAGFlow API key |
| `RAGFLOW_DEFAULT_DATASET_ID` | No | - | Default dataset for operations |
| `RAGFLOW_TIMEOUT` | No | 30 | Request timeout in seconds |
| `RAGFLOW_MAX_RETRIES` | No | 3 | Maximum retry attempts |
| `RAGFLOW_LOG_LEVEL` | No | INFO | Logging level |

### Cursor MCP Configuration

The MCP server can be configured in Cursor IDE by adding the configuration to your MCP settings file. The location varies by operating system:

- **macOS**: `~/Library/Application Support/Cursor/User/globalStorage/mcp.json`
- **Windows**: `%APPDATA%\Cursor\User\globalStorage\mcp.json`
- **Linux**: `~/.config/Cursor/User/globalStorage/mcp.json`

## Usage Patterns

### Basic Document Management

1. **Upload documents**: Use `ragflow_upload_file` to add new documents
2. **Search content**: Use `ragflow_search` to find relevant information
3. **Update documents**: Use `ragflow_update_file` to refresh content
4. **Manage files**: Use `ragflow_list_files` and `ragflow_delete_file`

### Development Workflow Integration

1. **Project Documentation**: Upload your project's documentation files
2. **Code Context**: Search for implementation details while coding
3. **Knowledge Base**: Maintain team knowledge with regular updates
4. **Research**: Search across multiple documents for comprehensive answers

### Advanced Usage

- **Batch Operations**: Upload multiple files programmatically
- **Custom Chunking**: Use different chunking strategies for different document types
- **Similarity Tuning**: Adjust similarity thresholds for better search results
- **Dataset Management**: Organize documents into different datasets by topic

## Troubleshooting

### Common Issues

1. **Connection Failed**: Check if RAGFlow is running and accessible
2. **Authentication Error**: Verify your API key is correct
3. **File Not Found**: Ensure file paths are correct and accessible
4. **Dataset Error**: Use `ragflow_get_datasets` to list available datasets

### Debug Mode

Enable debug logging by setting:
```bash
export RAGFLOW_LOG_LEVEL=DEBUG
```

### Testing Configuration

Use the provided usage examples to test your configuration:
```bash
python usage_examples.py
```

This will create a sample document and test all major operations.

## Docker Setup

If you want to run RAGFlow in Docker for development:

1. **Start RAGFlow**:
   ```bash
   docker-compose up -d ragflow
   ```

2. **Access RAGFlow**: Open http://localhost:9380 in your browser

3. **Create API Key**: Generate an API key in the RAGFlow interface

4. **Update Configuration**: Add your API key to the environment variables

5. **Test Connection**: Run the usage examples to verify connectivity

## Support

For issues with:
- **RAGFlow setup**: Check the [RAGFlow documentation](https://ragflow.io/docs)
- **MCP configuration**: Review the [MCP specification](https://modelcontextprotocol.io/docs)
- **This server**: Open an issue in the project repository