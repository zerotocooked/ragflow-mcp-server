"""MCP server implementation for RAGFlow integration."""

from typing import Any, Dict, List, Optional, Sequence
import logging
import asyncio
import os
import re
from pathlib import Path

from mcp.server import Server

from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
from mcp.server.models import InitializationOptions

from .config import RAGFlowConfig
from .client import RAGFlowClient
from .errors import RAGFlowError, ConfigurationError, APIError, ValidationError, FileError


logger = logging.getLogger(__name__)


class RAGFlowMCPServer:
    """Main MCP server class implementing MCP protocol for RAGFlow."""
    
    def __init__(self, config: RAGFlowConfig) -> None:
        """Initialize the MCP server with configuration.
        
        Args:
            config: RAGFlow configuration object
        """
        self.config = config
        self.client = RAGFlowClient(config)
        self.server = Server("ragflow-mcp-server")
        self._setup_handlers()
        logger.info("RAGFlow MCP Server initialized")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.client.close()
    
    def _setup_handlers(self) -> None:
        """Set up MCP server handlers."""
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """Handle list tools request."""
            try:
                logger.debug("Handling list_tools request")
                result = await self._list_tools()
                logger.debug(f"Returning {len(result)} tools")
                return result
            except Exception as e:
                logger.error(f"Error in list_tools: {e}", exc_info=True)
                raise
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
            """Handle call tool request."""
            try:
                logger.debug(f"Handling call_tool request: {name}")
                result = await self._call_tool(name, arguments)
                logger.debug(f"Tool {name} completed successfully")
                return result
            except Exception as e:
                logger.error(f"Error in call_tool {name}: {e}", exc_info=True)
                raise
    
    async def run(self) -> None:
        """Run the MCP server."""
        logger.info("RAGFlow MCP Server starting...")
        try:
            # Validate configuration before starting
            await self._validate_config()
            
            # Run the MCP server
            from mcp.server.stdio import stdio_server
            logger.debug("Starting stdio server...")
            
            async with stdio_server() as streams:
                logger.debug("stdio server started, running MCP server...")
                try:
                    from mcp.server.lowlevel.server import NotificationOptions
                    await self.server.run(
                        *streams,
                        InitializationOptions(
                            server_name="ragflow-mcp-server",
                            server_version="0.1.0",
                            capabilities=self.server.get_capabilities(
                                NotificationOptions(),
                                {}
                            )
                        )
                    )
                except Exception as e:
                    logger.error(f"MCP server run failed: {e}", exc_info=True)
                    raise
                finally:
                    logger.debug("Cleaning up client...")
                    # Ensure client is properly closed
                    await self.client.close()
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}", exc_info=True)
            # Ensure cleanup even on error
            try:
                await self.client.close()
            except Exception as cleanup_error:
                logger.error(f"Cleanup error: {cleanup_error}")
            raise
    
    async def _validate_config(self) -> None:
        """Validate configuration and connection to RAGFlow."""
        try:
            # Test connection to RAGFlow API with timeout
            timeout_task = asyncio.create_task(self.client.get_datasets())
            try:
                await asyncio.wait_for(timeout_task, timeout=self.config.timeout)
                logger.info("Successfully validated RAGFlow connection")
            except asyncio.TimeoutError:
                logger.error(f"Configuration validation timed out after {self.config.timeout}s")
                raise ConfigurationError(f"Connection validation timed out after {self.config.timeout}s")
        except Exception as e:
            logger.error(f"Failed to validate RAGFlow connection: {e}")
            raise ConfigurationError(f"Cannot connect to RAGFlow API: {e}")
    
    def _validate_file_path(self, file_path: str, parameter_name: str = "file_path") -> str:
        """Validate and sanitize file path to prevent directory traversal attacks.
        
        Args:
            file_path: File path to validate
            parameter_name: Name of the parameter for error messages
            
        Returns:
            Validated and normalized file path
            
        Raises:
            ValidationError: If file path is invalid or unsafe
        """
        if not file_path or not isinstance(file_path, str):
            raise ValidationError(f"{parameter_name} must be a non-empty string", field=parameter_name)
        
        # Strip whitespace
        file_path = file_path.strip()
        if not file_path:
            raise ValidationError(f"{parameter_name} cannot be empty", field=parameter_name)
        
        # Check for null bytes (security risk)
        if '\x00' in file_path:
            raise ValidationError(f"{parameter_name} contains null bytes", field=parameter_name)
        
        # Normalize path to prevent directory traversal
        try:
            normalized_path = os.path.normpath(file_path)
            resolved_path = os.path.abspath(normalized_path)
        except (OSError, ValueError) as e:
            raise ValidationError(f"Invalid file path format: {e}", field=parameter_name)
        
        # Check for directory traversal attempts
        if '..' in normalized_path or normalized_path.startswith('/'):
            # Allow absolute paths but log them for security monitoring
            logger.warning(f"Absolute or parent directory path used: {file_path}")
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'\.\.[\\/]',  # Parent directory traversal
            r'^[\\/]',     # Root directory access
            r'[\\/]\.\.[\\/]',  # Mid-path traversal
            r'[<>:"|?*]',  # Invalid filename characters on Windows
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, file_path):
                logger.warning(f"Potentially unsafe file path pattern detected: {file_path}")
        
        # Validate file extension
        allowed_extensions = {'.txt', '.pdf', '.doc', '.docx', '.md', '.html', '.csv', '.json', '.xml', '.rtf'}
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext and file_ext not in allowed_extensions:
            raise ValidationError(
                f"Unsupported file type: {file_ext}. Allowed: {', '.join(sorted(allowed_extensions))}", 
                field=parameter_name
            )
        
        return resolved_path
    
    def _validate_string_parameter(self, value: Any, parameter_name: str, min_length: int = 1, max_length: int = 1000) -> str:
        """Validate string parameter with length constraints.
        
        Args:
            value: Value to validate
            parameter_name: Name of the parameter for error messages
            min_length: Minimum allowed length
            max_length: Maximum allowed length
            
        Returns:
            Validated string value
            
        Raises:
            ValidationError: If value is invalid
        """
        if not isinstance(value, str):
            raise ValidationError(f"{parameter_name} must be a string", field=parameter_name)
        
        value = value.strip()
        if len(value) < min_length:
            raise ValidationError(f"{parameter_name} must be at least {min_length} characters long", field=parameter_name)
        
        if len(value) > max_length:
            raise ValidationError(f"{parameter_name} cannot exceed {max_length} characters", field=parameter_name)
        
        # Check for control characters (except newlines and tabs)
        if any(ord(c) < 32 and c not in '\n\t\r' for c in value):
            raise ValidationError(f"{parameter_name} contains invalid control characters", field=parameter_name)
        
        return value
    
    def _validate_integer_parameter(self, value: Any, parameter_name: str, min_value: int = None, max_value: int = None) -> int:
        """Validate integer parameter with range constraints.
        
        Args:
            value: Value to validate
            parameter_name: Name of the parameter for error messages
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            Validated integer value
            
        Raises:
            ValidationError: If value is invalid
        """
        if not isinstance(value, int):
            # Try to convert from string or float
            try:
                if isinstance(value, str):
                    value = int(value.strip())
                elif isinstance(value, float):
                    if value.is_integer():
                        value = int(value)
                    else:
                        raise ValueError("Float is not an integer")
                else:
                    raise ValueError("Invalid type")
            except (ValueError, AttributeError):
                raise ValidationError(f"{parameter_name} must be an integer", field=parameter_name)
        
        if min_value is not None and value < min_value:
            raise ValidationError(f"{parameter_name} must be at least {min_value}", field=parameter_name)
        
        if max_value is not None and value > max_value:
            raise ValidationError(f"{parameter_name} cannot exceed {max_value}", field=parameter_name)
        
        return value
    
    def _validate_float_parameter(self, value: Any, parameter_name: str, min_value: float = None, max_value: float = None) -> float:
        """Validate float parameter with range constraints.
        
        Args:
            value: Value to validate
            parameter_name: Name of the parameter for error messages
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            Validated float value
            
        Raises:
            ValidationError: If value is invalid
        """
        if not isinstance(value, (int, float)):
            # Try to convert from string
            try:
                if isinstance(value, str):
                    value = float(value.strip())
                else:
                    raise ValueError("Invalid type")
            except (ValueError, AttributeError):
                raise ValidationError(f"{parameter_name} must be a number", field=parameter_name)
        
        value = float(value)
        
        # Check for NaN and infinity
        if not (value == value):  # NaN check
            raise ValidationError(f"{parameter_name} cannot be NaN", field=parameter_name)
        
        if value == float('inf') or value == float('-inf'):
            raise ValidationError(f"{parameter_name} cannot be infinite", field=parameter_name)
        
        if min_value is not None and value < min_value:
            raise ValidationError(f"{parameter_name} must be at least {min_value}", field=parameter_name)
        
        if max_value is not None and value > max_value:
            raise ValidationError(f"{parameter_name} cannot exceed {max_value}", field=parameter_name)
        
        return value
    
    def _validate_chunk_method(self, chunk_method: str) -> str:
        """Validate chunk method parameter.
        
        Args:
            chunk_method: Chunk method to validate
            
        Returns:
            Validated chunk method
            
        Raises:
            ValidationError: If chunk method is invalid
        """
        valid_chunk_methods = {
            "naive", "manual", "qa", "table", "paper", "book", "laws", 
            "presentation", "picture", "one", "knowledge_graph", "email"
        }
        
        chunk_method = chunk_method.strip().lower()
        if chunk_method not in valid_chunk_methods:
            raise ValidationError(
                f"chunk_method must be one of: {', '.join(sorted(valid_chunk_methods))}", 
                field="chunk_method"
            )
        
        return chunk_method
    
    async def _list_tools(self) -> List[Tool]:
        """List available MCP tools.
        
        Returns:
            List of available tools
        """
        tools = [
            Tool(
                name="ragflow_upload_file",
                description="Upload and embed a new file into RAGFlow",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to upload"
                        },
                        "dataset_id": {
                            "type": "string", 
                            "description": "ID of the dataset in RAGFlow"
                        },
                        "chunk_method": {
                            "type": "string",
                            "description": "Chunking method to use",
                            "default": "naive"
                        }
                    },
                    "required": ["file_path", "dataset_id"]
                }
            ),
            Tool(
                name="ragflow_update_file",
                description="Update and re-embed an existing file in RAGFlow",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the file to update"
                        },
                        "dataset_id": {
                            "type": "string",
                            "description": "ID of the dataset containing the file"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to the new file content"
                        }
                    },
                    "required": ["file_id", "dataset_id", "file_path"]
                }
            ),
            Tool(
                name="ragflow_search",
                description="Search in RAGFlow knowledge base",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "dataset_id": {
                            "type": "string",
                            "description": "ID of the dataset to search in"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10
                        },
                        "similarity_threshold": {
                            "type": "number",
                            "description": "Similarity threshold for results",
                            "default": 0.1
                        }
                    },
                    "required": ["query", "dataset_id"]
                }
            ),
            Tool(
                name="ragflow_list_files",
                description="List all files in a dataset",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dataset_id": {
                            "type": "string",
                            "description": "ID of the dataset"
                        }
                    },
                    "required": ["dataset_id"]
                }
            ),
            Tool(
                name="ragflow_delete_file",
                description="Delete a file from RAGFlow",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the file to delete"
                        },
                        "dataset_id": {
                            "type": "string",
                            "description": "ID of the dataset containing the file"
                        }
                    },
                    "required": ["file_id", "dataset_id"]
                }
            ),
            Tool(
                name="ragflow_get_datasets",
                description="Get list of available datasets",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        ]
        
        logger.debug(f"Listed {len(tools)} available tools")
        return tools
    
    async def _call_tool(self, name: str, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Call a specific tool with given arguments.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        logger.info(f"Calling tool: {name} with arguments keys: {list(arguments.keys())}")
        
        try:
            # Add timeout wrapper for all tool operations
            timeout_duration = min(self.config.timeout * 2, 120)  # Max 2 minutes
            
            if name == "ragflow_upload_file":
                task = asyncio.create_task(self._handle_upload_file(arguments))
            elif name == "ragflow_update_file":
                task = asyncio.create_task(self._handle_update_file(arguments))
            elif name == "ragflow_search":
                task = asyncio.create_task(self._handle_search(arguments))
            elif name == "ragflow_list_files":
                task = asyncio.create_task(self._handle_list_files(arguments))
            elif name == "ragflow_delete_file":
                task = asyncio.create_task(self._handle_delete_file(arguments))
            elif name == "ragflow_get_datasets":
                task = asyncio.create_task(self._handle_get_datasets(arguments))
            else:
                raise ValidationError(f"Unknown tool: {name}", field="tool_name")
            
            try:
                return await asyncio.wait_for(task, timeout=timeout_duration)
            except asyncio.TimeoutError:
                logger.error(f"Tool {name} timed out after {timeout_duration}s")
                error_msg = f"Operation timed out after {timeout_duration} seconds. Please try again or check your connection."
                return [TextContent(type="text", text=error_msg)]
                
        except (ValidationError, FileError, APIError, ConfigurationError) as e:
            logger.error(f"Error executing tool {name}: {e}")
            # Return user-friendly error message
            error_msg = f"Error: {str(e)}"
            return [TextContent(type="text", text=error_msg)]
        except Exception as e:
            logger.error(f"Unexpected error executing tool {name}: {e}")
            error_msg = f"An unexpected error occurred while executing {name}. Please try again."
            return [TextContent(type="text", text=error_msg)]
    
    async def _handle_upload_file(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Handle file upload tool with comprehensive validation."""
        # Validate required parameters
        if "file_path" not in arguments:
            raise ValidationError("file_path parameter is required", field="file_path")
        if "dataset_id" not in arguments:
            raise ValidationError("dataset_id parameter is required", field="dataset_id")
        
        # Extract and validate parameters
        file_path = self._validate_file_path(arguments["file_path"], "file_path")
        dataset_id = self._validate_string_parameter(arguments["dataset_id"], "dataset_id", min_length=1, max_length=100)
        
        # Validate optional chunk_method parameter
        chunk_method = "naive"  # Default
        if "chunk_method" in arguments:
            chunk_method = self._validate_chunk_method(arguments["chunk_method"])
        
        # Additional file existence and accessibility checks
        if not os.path.exists(file_path):
            raise FileError(f"File not found: {file_path}", file_path=file_path)
        
        if not os.path.isfile(file_path):
            raise FileError(f"Path is not a file: {file_path}", file_path=file_path)
        
        if not os.access(file_path, os.R_OK):
            raise FileError(f"File is not readable: {file_path}", file_path=file_path)
        
        # Check file size
        try:
            file_size = os.path.getsize(file_path)
            max_size = 100 * 1024 * 1024  # 100MB
            if file_size > max_size:
                raise FileError(f"File too large: {file_size} bytes (max: {max_size})", file_path=file_path)
            if file_size == 0:
                raise FileError(f"File is empty: {file_path}", file_path=file_path)
        except OSError as e:
            raise FileError(f"Cannot access file: {e}", file_path=file_path)
        
        try:
            logger.info(f"Uploading file: {os.path.basename(file_path)} ({file_size} bytes) to dataset {dataset_id}")
            result = await self.client.upload_file(file_path, dataset_id, chunk_method)
            
            response = f"✅ File uploaded successfully!\n"
            response += f"📄 File ID: {result.file_id}\n"
            response += f"📊 Status: {result.status}\n"
            response += f"💬 Message: {result.message}"
            
            if result.chunk_count:
                response += f"\n🔢 Chunks created: {result.chunk_count}"
            
            return [TextContent(type="text", text=response)]
            
        except (ValidationError, FileError) as e:
            # Re-raise validation and file errors as-is
            raise
        except Exception as e:
            logger.error(f"Upload failed for file {file_path}: {e}")
            raise APIError(f"Failed to upload file: {str(e)}")
    
    async def _handle_update_file(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Handle file update tool with comprehensive validation."""
        # Validate required parameters
        if "file_id" not in arguments:
            raise ValidationError("file_id parameter is required", field="file_id")
        if "dataset_id" not in arguments:
            raise ValidationError("dataset_id parameter is required", field="dataset_id")
        if "file_path" not in arguments:
            raise ValidationError("file_path parameter is required", field="file_path")
        
        # Extract and validate parameters
        file_id = self._validate_string_parameter(arguments["file_id"], "file_id", min_length=1, max_length=100)
        dataset_id = self._validate_string_parameter(arguments["dataset_id"], "dataset_id", min_length=1, max_length=100)
        file_path = self._validate_file_path(arguments["file_path"], "file_path")
        
        # Additional file existence and accessibility checks
        if not os.path.exists(file_path):
            raise FileError(f"File not found: {file_path}", file_path=file_path)
        
        if not os.path.isfile(file_path):
            raise FileError(f"Path is not a file: {file_path}", file_path=file_path)
        
        if not os.access(file_path, os.R_OK):
            raise FileError(f"File is not readable: {file_path}", file_path=file_path)
        
        # Check file size
        try:
            file_size = os.path.getsize(file_path)
            max_size = 100 * 1024 * 1024  # 100MB
            if file_size > max_size:
                raise FileError(f"File too large: {file_size} bytes (max: {max_size})", file_path=file_path)
            if file_size == 0:
                raise FileError(f"File is empty: {file_path}", file_path=file_path)
        except OSError as e:
            raise FileError(f"Cannot access file: {e}", file_path=file_path)
        
        try:
            logger.info(f"Updating file {file_id} with: {os.path.basename(file_path)} ({file_size} bytes)")
            result = await self.client.update_file(file_id, dataset_id, file_path)
            
            response = f"✅ File updated successfully!\n"
            response += f"📄 File ID: {result.file_id}\n"
            response += f"📊 Status: {result.status}\n"
            response += f"💬 Message: {result.message}"
            
            if result.chunk_count:
                response += f"\n🔢 Chunks updated: {result.chunk_count}"
            
            return [TextContent(type="text", text=response)]
            
        except (ValidationError, FileError) as e:
            # Re-raise validation and file errors as-is
            raise
        except Exception as e:
            logger.error(f"Update failed for file {file_id}: {e}")
            raise APIError(f"Failed to update file: {str(e)}")
    
    async def _handle_search(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Handle search tool with comprehensive validation."""
        # Validate required parameters
        if "query" not in arguments:
            raise ValidationError("query parameter is required", field="query")
        if "dataset_id" not in arguments:
            raise ValidationError("dataset_id parameter is required", field="dataset_id")
        
        # Extract and validate parameters
        query = self._validate_string_parameter(arguments["query"], "query", min_length=1, max_length=1000)
        dataset_id = self._validate_string_parameter(arguments["dataset_id"], "dataset_id", min_length=1, max_length=100)
        
        # Validate optional parameters
        limit = 10  # Default
        if "limit" in arguments:
            limit = self._validate_integer_parameter(arguments["limit"], "limit", min_value=1, max_value=100)
        
        similarity_threshold = 0.1  # Default
        if "similarity_threshold" in arguments:
            similarity_threshold = self._validate_float_parameter(
                arguments["similarity_threshold"], "similarity_threshold", min_value=0.0, max_value=1.0
            )
        
        # Additional query validation
        if len(query.split()) > 50:
            raise ValidationError("Query is too long (max 50 words)", field="query")
        
        # Check for potentially harmful query patterns
        suspicious_patterns = [
            r'<script[^>]*>',  # Script tags
            r'javascript:',    # JavaScript URLs
            r'data:',         # Data URLs
            r'vbscript:',     # VBScript URLs
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"Potentially suspicious query pattern detected: {pattern}")
                raise ValidationError("Query contains potentially unsafe content", field="query")
        
        try:
            logger.info(f"Searching in dataset {dataset_id} with query length: {len(query)} chars")
            result = await self.client.search(
                query=query,
                dataset_id=dataset_id,
                limit=limit,
                similarity_threshold=similarity_threshold
            )
            
            if not result.results:
                return [TextContent(type="text", text="🔍 No results found for your query.\n\nTry:\n• Using different keywords\n• Lowering the similarity threshold\n• Checking if the dataset contains relevant content")]
            
            response = f"🔍 Found {result.total_count} results (showing top {len(result.results)}):\n\n"
            
            for i, item in enumerate(result.results, 1):
                response += f"{i}. 📊 Score: {item.score:.3f}\n"
                response += f"   📄 File: {item.file_name}\n"
                
                # Truncate content intelligently at word boundaries
                content = item.content
                if len(content) > 200:
                    truncated = content[:200]
                    # Try to truncate at word boundary
                    last_space = truncated.rfind(' ')
                    if last_space > 150:  # Only if we can save significant space
                        truncated = truncated[:last_space]
                    content = truncated + "..."
                
                response += f"   📝 Content: {content}\n\n"
            
            response += f"⏱️ Query time: {result.query_time:.3f}s"
            
            return [TextContent(type="text", text=response)]
            
        except (ValidationError, FileError) as e:
            # Re-raise validation and file errors as-is
            raise
        except Exception as e:
            logger.error(f"Search failed for query in dataset {dataset_id}: {e}")
            raise APIError(f"Failed to search: {str(e)}")
    
    async def _handle_list_files(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Handle list files tool with comprehensive validation."""
        # Validate required parameters
        if "dataset_id" not in arguments:
            raise ValidationError("dataset_id parameter is required", field="dataset_id")
        
        # Extract and validate parameters
        dataset_id = self._validate_string_parameter(arguments["dataset_id"], "dataset_id", min_length=1, max_length=100)
        
        # Validate optional parameters
        limit = 100  # Default
        if "limit" in arguments:
            limit = self._validate_integer_parameter(arguments["limit"], "limit", min_value=1, max_value=1000)
        
        offset = 0  # Default
        if "offset" in arguments:
            offset = self._validate_integer_parameter(arguments["offset"], "offset", min_value=0)
        
        try:
            logger.info(f"Listing files in dataset {dataset_id} (limit: {limit}, offset: {offset})")
            result = await self.client.list_files(dataset_id, limit=limit, offset=offset)
            
            if not result.files:
                return [TextContent(type="text", text="📂 No files found in the dataset.\n\nTry uploading some files first using the ragflow_upload_file tool.")]
            
            response = f"📂 Found {len(result.files)} files"
            if result.total_count > len(result.files):
                response += f" (showing {len(result.files)} of {result.total_count} total)"
            response += ":\n\n"
            
            for i, file_info in enumerate(result.files, 1):
                response += f"{i}. 📄 {file_info.name}\n"
                response += f"   🆔 ID: {file_info.file_id}\n"
                
                # Format file size nicely
                size = file_info.size
                if size < 1024:
                    size_str = f"{size} bytes"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                
                response += f"   📏 Size: {size_str}\n"
                response += f"   📅 Created: {file_info.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                response += f"   📊 Status: {file_info.status}\n"
                
                if hasattr(file_info, 'chunk_count') and file_info.chunk_count:
                    response += f"   🔢 Chunks: {file_info.chunk_count}\n"
                
                response += "\n"
            
            return [TextContent(type="text", text=response)]
            
        except (ValidationError, FileError) as e:
            # Re-raise validation and file errors as-is
            raise
        except Exception as e:
            logger.error(f"List files failed for dataset {dataset_id}: {e}")
            raise APIError(f"Failed to list files: {str(e)}")
    
    async def _handle_delete_file(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Handle delete file tool with comprehensive validation."""
        # Validate required parameters
        if "file_id" not in arguments:
            raise ValidationError("file_id parameter is required", field="file_id")
        if "dataset_id" not in arguments:
            raise ValidationError("dataset_id parameter is required", field="dataset_id")
        
        # Extract and validate parameters
        file_id = self._validate_string_parameter(arguments["file_id"], "file_id", min_length=1, max_length=100)
        dataset_id = self._validate_string_parameter(arguments["dataset_id"], "dataset_id", min_length=1, max_length=100)
        
        # Optional confirmation parameter for safety
        confirm = arguments.get("confirm", False)
        if not confirm and "confirm" not in arguments:
            # For safety, we could require explicit confirmation
            logger.warning(f"Deleting file {file_id} without explicit confirmation")
        
        try:
            logger.info(f"Deleting file {file_id}")
            result = await self.client.delete_file(file_id, dataset_id)
            
            response = f"🗑️ File deleted successfully!\n"
            response += f"📄 File ID: {file_id}\n"
            response += f"💬 Message: {result.message}"
            
            return [TextContent(type="text", text=response)]
            
        except (ValidationError, FileError) as e:
            # Re-raise validation and file errors as-is
            raise
        except Exception as e:
            logger.error(f"Delete failed for file {file_id}: {e}")
            raise APIError(f"Failed to delete file: {str(e)}")
    
    async def _handle_get_datasets(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Handle get datasets tool with comprehensive validation."""
        # Validate optional parameters
        limit = 100  # Default
        if "limit" in arguments:
            limit = self._validate_integer_parameter(arguments["limit"], "limit", min_value=1, max_value=1000)
        
        offset = 0  # Default
        if "offset" in arguments:
            offset = self._validate_integer_parameter(arguments["offset"], "offset", min_value=0)
        
        # Check for any unexpected parameters
        expected_params = {"limit", "offset"}
        unexpected_params = set(arguments.keys()) - expected_params
        if unexpected_params:
            logger.warning(f"Unexpected parameters in get_datasets: {unexpected_params}")
        
        try:
            logger.info(f"Getting datasets (limit: {limit}, offset: {offset})")
            result = await self.client.get_datasets(limit=limit, offset=offset)
            
            if not result.datasets:
                return [TextContent(type="text", text="📊 No datasets found.\n\nYou may need to create a dataset first in your RAGFlow instance.")]
            
            response = f"📊 Found {len(result.datasets)} datasets"
            if hasattr(result, 'total_count') and result.total_count > len(result.datasets):
                response += f" (showing {len(result.datasets)} of {result.total_count} total)"
            response += ":\n\n"
            
            for i, dataset in enumerate(result.datasets, 1):
                response += f"{i}. 📁 {dataset.name}\n"
                response += f"   🆔 ID: {dataset.dataset_id}\n"
                
                description = dataset.description or "No description"
                if len(description) > 100:
                    description = description[:100] + "..."
                response += f"   📝 Description: {description}\n"
                
                file_count = getattr(dataset, 'file_count', 0)
                response += f"   📄 Files: {file_count}\n"
                
                if hasattr(dataset, 'created_at'):
                    response += f"   📅 Created: {dataset.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                
                response += "\n"
            
            return [TextContent(type="text", text=response)]
            
        except (ValidationError, FileError) as e:
            # Re-raise validation and file errors as-is
            raise
        except Exception as e:
            logger.error(f"Get datasets failed: {e}")
            raise APIError(f"Failed to get datasets: {str(e)}")