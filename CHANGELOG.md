# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup and documentation

## [0.1.0] - 2024-01-XX

### Added
- Initial release of RAGFlow MCP Server
- MCP server implementation for RAGFlow API integration
- Support for file upload, update, search, and management operations
- Comprehensive error handling and validation
- Async HTTP client with connection pooling and retry logic
- Configuration management via environment variables
- Full type hints and Pydantic data models
- Comprehensive test suite (unit and integration tests)
- Documentation and usage examples
- Docker support and example configurations

### Features
- **File Operations**:
  - Upload files to RAGFlow with automatic embedding
  - Update existing files and trigger re-embedding
  - Delete files from RAGFlow datasets
  - List files with metadata and status information
  
- **Search Operations**:
  - Semantic search through RAGFlow knowledge base
  - Configurable similarity thresholds and result limits
  - Support for multiple datasets
  
- **Dataset Management**:
  - List available datasets
  - Get dataset information and statistics
  
- **MCP Tools**:
  - `ragflow_upload_file` - Upload and embed documents
  - `ragflow_update_file` - Update existing documents
  - `ragflow_search` - Search through knowledge base
  - `ragflow_list_files` - List files in datasets
  - `ragflow_delete_file` - Delete files
  - `ragflow_get_datasets` - Get available datasets

### Technical Features
- Async/await support for all operations
- HTTP connection pooling and reuse
- Exponential backoff retry logic
- Comprehensive error handling with sanitization
- Input validation and type safety
- Configurable timeouts and retry limits
- Debug logging support

### Documentation
- Comprehensive README with installation and usage instructions
- Example configurations for Cursor IDE
- Usage examples and common workflows
- API documentation with parameter descriptions
- Troubleshooting guide
- Development setup instructions

### Testing
- Unit tests for all components
- Integration tests with mock RAGFlow API
- Performance tests for large file operations
- MCP protocol compliance tests
- Error scenario testing
- Configuration validation tests

[Unreleased]: https://github.com/your-username/ragflow-mcp-server/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-username/ragflow-mcp-server/releases/tag/v0.1.0