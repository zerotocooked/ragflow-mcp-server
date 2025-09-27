"""RAGFlow MCP Server - Model Context Protocol server for RAGFlow API integration.

This package provides a Model Context Protocol (MCP) server that enables seamless
integration between Cursor IDE and RAGFlow, allowing developers to:

- Upload and embed documents into RAGFlow knowledge base
- Update existing documents and trigger automatic re-embedding  
- Search through documents using semantic similarity
- Manage files and datasets with full CRUD operations
- List and organize knowledge base content

Example usage:
    >>> from ragflow_mcp_server import RAGFlowConfig, RAGFlowClient
    >>> config = RAGFlowConfig.from_env()
    >>> async with RAGFlowClient(config) as client:
    ...     result = await client.search("machine learning", "dataset_id")
    ...     print(f"Found {len(result.results)} results")

For MCP server usage, configure in Cursor IDE:
    {
      "mcpServers": {
        "ragflow": {
          "command": "python",
          "args": ["-m", "ragflow_mcp_server"],
          "env": {
            "RAGFLOW_BASE_URL": "http://localhost:9380",
            "RAGFLOW_API_KEY": "your_api_key"
          }
        }
      }
    }
"""

__version__ = "0.1.0"
__author__ = "Developer"
__email__ = "developer@example.com"
__description__ = "MCP server for RAGFlow API integration with Cursor IDE"
__url__ = "https://github.com/your-username/ragflow-mcp-server"

from .server import RAGFlowMCPServer
from .client import RAGFlowClient
from .config import RAGFlowConfig
from .errors import (
    RAGFlowError,
    ConfigurationError,
    AuthenticationError,
    APIError,
    FileError,
    ValidationError,
)
from .models import (
    UploadResult,
    UpdateResult,
    SearchResult,
    SearchItem,
    ListFilesResult,
    DeleteResult,
    FileStatus,
    DatasetsResult,
)

__all__ = [
    # Core classes
    "RAGFlowMCPServer",
    "RAGFlowClient", 
    "RAGFlowConfig",
    
    # Exceptions
    "RAGFlowError",
    "ConfigurationError",
    "AuthenticationError",
    "APIError",
    "FileError",
    "ValidationError",
    
    # Data models
    "UploadResult",
    "UpdateResult", 
    "SearchResult",
    "SearchItem",
    "ListFilesResult",
    "DeleteResult",
    "FileStatus",
    "DatasetsResult",
]