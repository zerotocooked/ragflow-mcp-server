# RAGFlow MCP Server - Project Information

## Quick Reference

| Property | Value |
|----------|-------|
| **Project Name** | RAGFlow MCP Server |
| **Version** | 0.1.0 |
| **Status** | Alpha |
| **License** | MIT |
| **Language** | Python 3.8+ |
| **Protocol** | Model Context Protocol (MCP) |
| **Primary Use Case** | RAGFlow integration with Cursor IDE |

## What This Project Does

RAGFlow MCP Server bridges the gap between RAGFlow's advanced document processing and semantic search capabilities and modern development environments. It allows developers to:

- Upload and manage documents within their IDE
- Perform semantic searches across their knowledge base
- Keep documentation synchronized with code
- Access relevant information without context switching

## Key Technologies

- **Python**: Core language (3.8+)
- **MCP Protocol**: Integration protocol for AI editors
- **aiohttp**: Async HTTP client
- **Pydantic**: Data validation and settings
- **RAGFlow API**: Backend knowledge base system

## Project Structure

```
ragflow-mcp-server/
├── ragflow_mcp_server/     # Main package
│   ├── __init__.py         # Package initialization
│   ├── __main__.py         # Entry point
│   ├── server.py           # MCP server implementation
│   ├── client.py           # RAGFlow API client
│   ├── config.py           # Configuration management
│   ├── errors.py           # Custom exceptions
│   └── models.py           # Data models
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── examples/              # Usage examples
├── docs/                  # Additional documentation
├── README.md              # Main documentation
├── DESCRIPTION.md         # Detailed project description (English)
├── DESCRIPTION_VI.md      # Detailed project description (Vietnamese)
├── FEATURES.md            # Feature documentation
├── CONTRIBUTING.md        # Contribution guidelines
├── CHANGELOG.md           # Version history
├── INSTALL.md             # Installation guide
├── pyproject.toml         # Project configuration
├── Dockerfile             # Container definition
└── Makefile              # Build automation
```

## Core Components

### 1. MCP Server (`server.py`)
- Implements Model Context Protocol
- Registers and exposes tools
- Handles request routing
- Manages server lifecycle

### 2. RAGFlow Client (`client.py`)
- API abstraction layer
- HTTP request handling
- Authentication management
- Retry logic implementation

### 3. Configuration (`config.py`)
- Environment variable management
- Default values
- Validation logic
- Settings documentation

### 4. Data Models (`models.py`)
- Pydantic models for type safety
- Request/response schemas
- Validation rules
- API contracts

### 5. Error Handling (`errors.py`)
- Custom exception hierarchy
- Error categorization
- Error messages
- Recovery suggestions

## Available MCP Tools

| Tool Name | Purpose | Key Parameters |
|-----------|---------|----------------|
| `ragflow_upload_file` | Upload documents | file_path, dataset_id, chunk_method |
| `ragflow_update_file` | Update existing files | file_id, file_path |
| `ragflow_search` | Semantic search | query, dataset_id, limit, threshold |
| `ragflow_list_files` | List dataset files | dataset_id |
| `ragflow_delete_file` | Delete files | file_id |
| `ragflow_get_datasets` | List available datasets | (none) |

## Configuration Options

### Required Environment Variables

```bash
RAGFLOW_BASE_URL=http://localhost:9380
RAGFLOW_API_KEY=your_api_key_here
```

### Optional Environment Variables

```bash
RAGFLOW_DEFAULT_DATASET_ID=dataset123
RAGFLOW_TIMEOUT=30
RAGFLOW_MAX_RETRIES=3
RAGFLOW_LOG_LEVEL=INFO
```

## Installation Methods

### 1. From Source (Development)
```bash
git clone <repository-url>
cd ragflow-mcp-server
pip install -e ".[dev]"
```

### 2. From Source (Production)
```bash
pip install -e .
```

### 3. From PyPI (Future)
```bash
pip install ragflow-mcp-server
```

### 4. Using Docker
```bash
docker build -t ragflow-mcp-server .
docker run -e RAGFLOW_BASE_URL=... -e RAGFLOW_API_KEY=... ragflow-mcp-server
```

## Usage Examples

### Basic Workflow

```python
# 1. Get available datasets
Use ragflow_get_datasets

# 2. Upload a document
Use ragflow_upload_file with:
  - file_path: "./docs/manual.pdf"
  - dataset_id: "your_dataset_id"

# 3. Search for information
Use ragflow_search with:
  - query: "how to configure authentication"
  - dataset_id: "your_dataset_id"

# 4. Update a document
Use ragflow_update_file with:
  - file_id: "file123"
  - file_path: "./docs/updated_manual.pdf"
```

## Development Workflow

### Setup
```bash
git clone <repository-url>
cd ragflow-mcp-server
pip install -e ".[dev]"
```

### Testing
```bash
# All tests
pytest

# With coverage
pytest --cov=ragflow_mcp_server

# Specific categories
pytest tests/unit/
pytest tests/integration/
```

### Code Quality
```bash
# Format
black ragflow_mcp_server/
isort ragflow_mcp_server/

# Type check
mypy ragflow_mcp_server/

# Lint
flake8 ragflow_mcp_server/
```

### Running the Server
```bash
# Development mode
python -m ragflow_mcp_server

# With debug logging
RAGFLOW_LOG_LEVEL=DEBUG python -m ragflow_mcp_server
```

## Cursor IDE Configuration

Add to your Cursor MCP settings:

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

## Dependencies

### Production Dependencies
- `mcp>=1.0.0` - Model Context Protocol implementation
- `aiohttp>=3.8.0` - Async HTTP client
- `pydantic>=2.0.0` - Data validation
- `python-dotenv>=1.0.0` - Environment variable management

### Development Dependencies
- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
- `pytest-mock>=3.10.0` - Mocking support
- `pytest-cov>=4.0.0` - Coverage reporting
- `black>=23.0.0` - Code formatting
- `isort>=5.12.0` - Import sorting
- `mypy>=1.0.0` - Static type checking
- `flake8>=6.0.0` - Linting

## Supported Python Versions

- Python 3.8
- Python 3.9
- Python 3.10
- Python 3.11
- Python 3.12

## Operating Systems

- Linux (all distributions)
- macOS (10.15+)
- Windows (10+)
- Docker containers

## RAGFlow Compatibility

- RAGFlow v0.5.0+
- RAGFlow API v1+
- Self-hosted or cloud instances

## Common Use Cases

### 1. Documentation Search
Access project documentation while coding without switching windows.

### 2. Knowledge Base Management
Keep your team's knowledge base synchronized with code changes.

### 3. Code Context
Upload API documentation and search for implementation details.

### 4. Onboarding
Help new team members find information quickly.

### 5. Research
Discover related concepts and solutions in your knowledge base.

## Performance Characteristics

- **Search Latency**: < 1 second
- **Upload Speed**: Network and file size dependent
- **Memory Usage**: Low (async operations)
- **Concurrent Requests**: Supported
- **Scalability**: 10,000+ documents per dataset

## Security Considerations

- API key authentication required
- HTTPS recommended for production
- Environment variables for secrets
- Input validation on all requests
- No credential logging

## Troubleshooting

### Common Issues

**Cannot connect to RAGFlow**
- Check RAGFLOW_BASE_URL is correct
- Verify RAGFlow is running
- Check network connectivity

**Authentication failed**
- Verify RAGFLOW_API_KEY is correct
- Check API key permissions in RAGFlow

**File upload failed**
- Check file exists and is readable
- Verify file size within limits
- Confirm dataset_id is valid

**Search returns no results**
- Ensure documents are embedded
- Try different query phrasing
- Check similarity_threshold setting

## Contributing

Contributions welcome! See CONTRIBUTING.md for guidelines.

Areas for contribution:
- Bug fixes
- Feature implementations
- Documentation improvements
- Test coverage
- Performance optimizations

## Roadmap

### v0.2.0
- Batch operations
- Advanced search filters
- Enhanced embedding options

### v0.3.0
- Multi-dataset search
- Search analytics
- Cache management

### v0.4.0
- Webhook support
- Export functionality
- Audit logging

### v0.5.0
- Team collaboration features
- Role-based access control
- Cloud deployment options

## Links and Resources

- **Documentation**: README.md, DESCRIPTION.md
- **Features**: FEATURES.md
- **Installation**: INSTALL.md
- **Contributing**: CONTRIBUTING.md
- **Changelog**: CHANGELOG.md
- **RAGFlow**: https://ragflow.io
- **MCP Protocol**: https://modelcontextprotocol.io

## Support

- GitHub Issues: For bugs and feature requests
- Discussions: For questions and community support
- Documentation: For how-to guides and references

## License

MIT License - See LICENSE file for details

Free for personal and commercial use with attribution.
