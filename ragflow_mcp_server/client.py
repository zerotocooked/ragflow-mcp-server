"""RAGFlow API client implementation."""

from typing import Any, Dict, List, Optional
import logging
import asyncio
import aiohttp
from aiohttp import ClientTimeout, ClientConnectorError, ClientResponseError
import json

from .config import RAGFlowConfig
from .errors import APIError, AuthenticationError, FileError, ValidationError
from .models import UploadResult, UpdateResult, SearchResult, SearchItem, ListFilesResult, DeleteResult, FileStatus


logger = logging.getLogger(__name__)


class RAGFlowClient:
    """Client for interacting with RAGFlow HTTP API."""
    
    def __init__(self, config: RAGFlowConfig) -> None:
        """Initialize the RAGFlow API client.
        
        Args:
            config: RAGFlow configuration object
        """
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info(f"RAGFlow client initialized for {config.base_url}")
    
    async def __aenter__(self) -> "RAGFlowClient":
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self) -> None:
        """Ensure HTTP session is created with connection pooling."""
        if self.session is None:
            timeout = ClientTimeout(total=self.config.timeout)
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool size
                limit_per_host=30,  # Max connections per host
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
            )
            
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "User-Agent": "RAGFlow-MCP-Server/1.0"
            }
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=headers
            )
            logger.debug("HTTP session created with connection pooling")
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.debug("HTTP session closed")
    
    def _safe_get(self, data: Any, key: str, default: Any = None) -> Any:
        """Safely get value from data, handling None case."""
        if data is None:
            return default
        if isinstance(data, dict):
            return data.get(key, default)
        return default
    
    async def start_document_processing(self, dataset_id: str, document_ids: List[str]) -> bool:
        """Start processing/embedding for uploaded documents.
        
        Args:
            dataset_id: Dataset ID containing the documents
            document_ids: List of document IDs to process
            
        Returns:
            True if processing started successfully
            
        Raises:
            APIError: If request fails
        """
        logger.info(f"Starting processing for {len(document_ids)} documents in dataset {dataset_id}")
        
        response_data = await self._make_request(
            method="POST",
            endpoint=f"/api/v1/datasets/{dataset_id}/chunks",
            data={"document_ids": document_ids}
        )
        
        # Check for success (code 0)
        if isinstance(response_data, dict) and response_data.get('code') == 0:
            logger.info("Document processing started successfully")
            return True
        else:
            error_msg = self._safe_get(response_data, 'message', 'Unknown error')
            raise APIError(f"Failed to start document processing: {error_msg}")
    
    async def wait_for_processing(self, dataset_id: str, document_id: str, timeout: int = 300) -> bool:
        """Wait for document processing to complete.
        
        Args:
            dataset_id: Dataset ID
            document_id: Document ID to monitor
            timeout: Maximum wait time in seconds
            
        Returns:
            True if processing completed successfully
        """
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                status = await self.get_file_status(document_id, dataset_id)
                if status.status == "completed":
                    logger.info(f"Document {document_id} processing completed")
                    return True
                elif status.status == "failed":
                    logger.error(f"Document {document_id} processing failed")
                    return False
                
                # Wait before next check
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.warning(f"Error checking status: {e}")
                await asyncio.sleep(5)
        
        logger.warning(f"Document processing timeout after {timeout}s")
        return False
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic and error handling.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: JSON data to send
            files: Files to upload (multipart)
            params: Query parameters
            retry_count: Current retry attempt
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIError: For API-related errors
            AuthenticationError: For authentication failures
        """
        await self._ensure_session()
        
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            # Prepare request kwargs
            kwargs = {}
            if params:
                kwargs['params'] = params
            
            if files:
                # For multipart uploads, use data parameter and let aiohttp handle Content-Type
                kwargs['data'] = files
            elif data:
                # For JSON requests, set Content-Type and use json parameter
                kwargs['headers'] = {**self.session.headers, 'Content-Type': 'application/json'}
                kwargs['json'] = data
            
            logger.debug(f"Making {method} request to {url}")
            logger.debug(f"Request kwargs: {kwargs}")
            
            async with self.session.request(method, url, **kwargs) as response:
                response_text = await response.text()
                
                # Handle authentication errors
                if response.status == 401:
                    logger.error("Authentication failed")
                    raise AuthenticationError("Invalid API key or token expired")
                
                # Handle other HTTP errors
                if response.status >= 400:
                    try:
                        error_data = json.loads(response_text) if response_text else {}
                        error_message = error_data.get('message', f'HTTP {response.status}')
                    except json.JSONDecodeError:
                        error_message = f'HTTP {response.status}: {response_text[:200]}'
                    
                    logger.error(f"API error {response.status}: {error_message}")
                    raise APIError(
                        message=error_message,
                        status_code=response.status,
                        response_data=error_data if 'error_data' in locals() else None
                    )
                
                # Parse successful response
                try:
                    if response_text:
                        return json.loads(response_text)
                    else:
                        return {}
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    raise APIError(f"Invalid JSON response: {e}")
                    
        except (ClientConnectorError, asyncio.TimeoutError) as e:
            # Network errors - retry with exponential backoff
            if retry_count < self.config.max_retries:
                wait_time = min(2 ** retry_count, 30)  # Exponential backoff: 1s, 2s, 4s, max 30s
                logger.warning(f"Network error, retrying in {wait_time}s (attempt {retry_count + 1}/{self.config.max_retries}): {type(e).__name__}")
                await asyncio.sleep(wait_time)
                return await self._make_request(method, endpoint, data, files, params, retry_count + 1)
            else:
                error_type = "timeout" if isinstance(e, asyncio.TimeoutError) else "connection"
                logger.error(f"Network {error_type} error after {self.config.max_retries} retries: {e}")
                if isinstance(e, asyncio.TimeoutError):
                    raise APIError(f"Request timed out after {self.config.timeout}s. Please check your connection or try again later.")
                else:
                    raise APIError(f"Connection error: Unable to connect to RAGFlow server. Please check the server URL and network connection.")
                
        except ClientResponseError as e:
            # HTTP errors that weren't handled above
            logger.error(f"HTTP error: {e}")
            raise APIError(f"HTTP error: {e}", status_code=e.status)
            
        except (AuthenticationError, APIError):
            # Re-raise our custom exceptions without wrapping
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error in HTTP request: {e}")
            raise APIError(f"Unexpected error: {e}")
    
    async def upload_file(
        self, 
        file_path: str, 
        dataset_id: str,
        chunk_method: str = "naive",
        progress_callback: Optional[callable] = None
    ) -> UploadResult:
        """Upload and embed a file to RAGFlow.
        
        Args:
            file_path: Path to the file to upload
            dataset_id: ID of the dataset in RAGFlow
            chunk_method: Method for chunking the document (default: "naive")
            progress_callback: Optional callback for progress updates
            
        Returns:
            Upload result with file ID and status
            
        Raises:
            FileError: If file doesn't exist or is invalid
            ValidationError: If parameters are invalid
            APIError: If upload fails
        """
        # Comprehensive parameter validation
        if not file_path or not isinstance(file_path, str):
            raise ValidationError("File path must be a non-empty string", field="file_path")
        
        if not dataset_id or not isinstance(dataset_id, str):
            raise ValidationError("Dataset ID must be a non-empty string", field="dataset_id")
        
        if not isinstance(chunk_method, str):
            raise ValidationError("Chunk method must be a string", field="chunk_method")
        
        # Validate chunk method
        valid_chunk_methods = {
            "naive", "manual", "qa", "table", "paper", "book", "laws", 
            "presentation", "picture", "one", "knowledge_graph", "email"
        }
        if chunk_method not in valid_chunk_methods:
            raise ValidationError(
                f"Invalid chunk method. Must be one of: {', '.join(sorted(valid_chunk_methods))}", 
                field="chunk_method"
            )
        
        # Check if file exists and get file info
        import os
        if not os.path.exists(file_path):
            raise FileError(f"File not found: {file_path}", file_path=file_path)
        
        if not os.path.isfile(file_path):
            raise FileError(f"Path is not a file: {file_path}", file_path=file_path)
        
        # Get file size and validate
        file_size = os.path.getsize(file_path)
        max_file_size = 100 * 1024 * 1024  # 100MB limit
        if file_size > max_file_size:
            raise FileError(f"File too large: {file_size} bytes (max: {max_file_size})", file_path=file_path)
        
        if file_size == 0:
            raise FileError(f"File is empty: {file_path}", file_path=file_path)
        
        # Validate file type
        allowed_extensions = {'.txt', '.pdf', '.doc', '.docx', '.md', '.html', '.csv', '.json'}
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in allowed_extensions:
            raise FileError(f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}", file_path=file_path)
        
        # Prepare multipart form data
        filename = os.path.basename(file_path)
        
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
                
            # Create multipart form data using aiohttp FormData properly
            import aiohttp
            
            form_data = aiohttp.FormData()
            form_data.add_field('file', 
                              file_content, 
                              filename=filename, 
                              content_type=self._get_content_type(file_ext))
            form_data.add_field('chunk_method', chunk_method)
            
            logger.info(f"Uploading file {filename} ({file_size} bytes) to dataset {dataset_id}")
            
            # Call progress callback if provided
            if progress_callback:
                progress_callback(0, file_size, "Starting upload...")
            
            # Make the upload request
            response_data = await self._make_request(
                method="POST",
                endpoint=f"/api/v1/datasets/{dataset_id}/documents",
                files=form_data
            )
            
            # Call progress callback for completion
            if progress_callback:
                progress_callback(file_size, file_size, "Upload completed")
            
            # Parse response and create UploadResult
            # Debug: log the actual response structure
            logger.debug(f"Upload response data: {response_data}")
            
            # RAGFlow may return data in different formats, try multiple approaches
            data_list = self._safe_get(response_data, 'data', [])
            
            # If data is not a list, it might be a single object
            if not isinstance(data_list, list):
                if isinstance(data_list, dict):
                    data_list = [data_list]
                else:
                    data_list = []
            
            # If still no data, check if the response itself contains the document info
            if not data_list:
                # Sometimes the response is the document data directly
                if 'id' in response_data:
                    data_list = [response_data]
                else:
                    logger.error(f"No document data found in response: {response_data}")
                    raise APIError("No document data returned from upload response")
            
            # Get first document from the list
            doc_data = data_list[0] if data_list else {}
            file_id = self._safe_get(doc_data, 'id')
            if not file_id:
                # Try alternative field names
                file_id = self._safe_get(doc_data, 'document_id') or self._safe_get(doc_data, 'file_id')
                if not file_id:
                    logger.error(f"No file ID found in document data: {doc_data}")
                    raise APIError("No file ID returned from upload response")
            
            status = self._safe_get(response_data, 'status', 'success')
            message = self._safe_get(response_data, 'message', f'File {filename} uploaded successfully')
            
            # Try to get chunk_count from document data
            chunk_count = None
            if isinstance(data_list, list) and data_list:
                chunk_count = self._safe_get(data_list[0], 'chunk_count')
            
            logger.info(f"File uploaded successfully: {file_id}")
            
            # Automatically trigger document processing/embedding after upload
            try:
                logger.info(f"Starting automatic document processing for file {file_id}")
                await self.start_document_processing(dataset_id, [file_id])
                message += " and processing started"
                
                # Don't wait for processing to complete to avoid timeout
                # Processing will happen in background
                logger.info(f"Document processing started for file {file_id}")
                    
            except Exception as e:
                # Don't fail the upload if processing fails, just log warning
                logger.warning(f"Failed to start automatic processing for file {file_id}: {e}")
                message += " (manual processing may be required)"
            
            return UploadResult(
                file_id=file_id,
                status=status,
                message=message,
                chunk_count=chunk_count
            )
            
        except (OSError, IOError) as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise FileError(f"Failed to read file: {e}", file_path=file_path)
        except Exception as e:
            if isinstance(e, (ValidationError, FileError, APIError, AuthenticationError)):
                raise
            logger.error(f"Unexpected error during file upload: {e}")
            raise APIError(f"Upload failed: {e}")
    
    def _get_content_type(self, file_ext: str) -> str:
        """Get MIME content type for file extension.
        
        Args:
            file_ext: File extension (with dot)
            
        Returns:
            MIME content type string
        """
        content_types = {
            '.txt': 'text/plain',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.md': 'text/markdown',
            '.html': 'text/html',
            '.csv': 'text/csv',
            '.json': 'application/json'
        }
        return content_types.get(file_ext.lower(), 'application/octet-stream')
    
    async def update_file(
        self, 
        file_id: str, 
        dataset_id: str,
        file_path: str,
        progress_callback: Optional[callable] = None
    ) -> UpdateResult:
        """Update and re-embed an existing file in RAGFlow.
        
        Args:
            file_id: ID of the file to update
            file_path: Path to the new file content
            progress_callback: Optional callback for progress updates
            
        Returns:
            Update result with status
            
        Raises:
            FileError: If file doesn't exist or is invalid
            ValidationError: If parameters are invalid
            APIError: If update fails
        """
        # Validate parameters
        if not file_id or not isinstance(file_id, str):
            raise ValidationError("File ID must be a non-empty string", field="file_id")
        
        if not file_path or not isinstance(file_path, str):
            raise ValidationError("File path must be a non-empty string", field="file_path")
        
        # Check if file exists first
        try:
            await self.get_file_status(file_id, dataset_id)
        except APIError as e:
            if e.status_code == 404:
                raise FileError(f"File with ID {file_id} not found", file_path=file_id)
            raise
        
        # Validate new file
        import os
        if not os.path.exists(file_path):
            raise FileError(f"File not found: {file_path}", file_path=file_path)
        
        if not os.path.isfile(file_path):
            raise FileError(f"Path is not a file: {file_path}", file_path=file_path)
        
        # Get file size and validate
        file_size = os.path.getsize(file_path)
        max_file_size = 100 * 1024 * 1024  # 100MB limit
        if file_size > max_file_size:
            raise FileError(f"File too large: {file_size} bytes (max: {max_file_size})", file_path=file_path)
        
        if file_size == 0:
            raise FileError(f"File is empty: {file_path}", file_path=file_path)
        
        # Validate file type
        allowed_extensions = {'.txt', '.pdf', '.doc', '.docx', '.md', '.html', '.csv', '.json'}
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in allowed_extensions:
            raise FileError(f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}", file_path=file_path)
        
        # Prepare multipart form data
        filename = os.path.basename(file_path)
        
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
                
            # Create multipart form data
            files = {
                'file': (filename, file_content, self._get_content_type(file_ext)),
                'file_id': (None, file_id)
            }
            
            logger.info(f"Updating file {file_id} with {filename} ({file_size} bytes)")
            
            # Call progress callback if provided
            if progress_callback:
                progress_callback(0, file_size, "Starting update...")
            
            # RAGFlow doesn't support direct file update, so we delete and re-upload
            logger.info(f"RAGFlow doesn't support direct update, deleting and re-uploading file {file_id}")
            
            # First, get the original file name for re-upload
            original_name = filename
            try:
                files_result = await self.list_files(dataset_id, limit=1000)
                for file_info in files_result.files:
                    if file_info.file_id == file_id:
                        original_name = file_info.name
                        break
            except Exception:
                pass  # Use filename if we can't get original name
            
            # Delete the old file
            await self.delete_file(file_id, dataset_id, confirm=True)
            
            # Upload the new file with the same name
            upload_result = await self.upload_file(
                file_path=file_path,
                dataset_id=dataset_id,
                chunk_method="naive"
            )
            
            # Create a fake response for consistency
            response_data = {
                'code': 0,
                'message': f'File updated successfully (deleted and re-uploaded)',
                'data': [{'id': upload_result.file_id, 'chunk_count': upload_result.chunk_count}]
            }
            
            # Call progress callback for completion
            if progress_callback:
                progress_callback(file_size, file_size, "Update completed")
            
            # Parse response and create UpdateResult
            if not response_data:
                response_data = {}
                
            status = self._safe_get(response_data, 'status', 'success')
            message = self._safe_get(response_data, 'message', f'File {file_id} updated successfully')
            
            # Try to get chunk_count from response data
            chunk_count = None
            data = self._safe_get(response_data, 'data')
            if isinstance(data, dict):
                chunk_count = self._safe_get(data, 'chunk_count')
            elif isinstance(data, list) and data:
                chunk_count = self._safe_get(data[0], 'chunk_count')
            
            logger.info(f"File updated successfully: {file_id}")
            
            # Trigger re-embedding automatically
            try:
                await self._trigger_reembedding(dataset_id, file_id)
                
                # Optionally wait for processing to complete
                processing_success = await self.wait_for_processing(dataset_id, file_id, timeout=60)
                if processing_success:
                    logger.info(f"Document re-processing completed successfully for file {file_id}")
                    message += " and re-processed for embedding"
                else:
                    logger.warning(f"Document re-processing may still be in progress for file {file_id}")
                    message += " (re-processing in background)"
                    
            except Exception as e:
                # Don't fail the update if processing fails, just log warning
                logger.warning(f"Failed to start automatic re-processing for file {file_id}: {e}")
                message += " (manual re-processing may be required)"
            
            return UpdateResult(
                file_id=upload_result.file_id,  # Return new file_id after re-upload
                status=status,
                message=message,
                chunk_count=chunk_count
            )
            
        except (OSError, IOError) as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise FileError(f"Failed to read file: {e}", file_path=file_path)
        except Exception as e:
            if isinstance(e, (ValidationError, FileError, APIError, AuthenticationError)):
                raise
            logger.error(f"Unexpected error during file update: {e}")
            raise APIError(f"Update failed: {e}")
    
    async def _trigger_reembedding(self, dataset_id: str, file_id: str) -> None:
        """Trigger re-embedding for an updated file.
        
        Args:
            dataset_id: ID of the dataset containing the file
            file_id: ID of the file to re-embed
            
        Raises:
            APIError: If re-embedding trigger fails
        """
        try:
            logger.info(f"Triggering re-embedding for file {file_id}")
            
            # Use the same document processing method as upload
            await self.start_document_processing(dataset_id, [file_id])
            
            logger.info(f"Re-embedding triggered successfully for file {file_id}")
            
        except APIError as e:
            # Log warning but don't fail the update operation
            logger.warning(f"Failed to trigger re-embedding for file {file_id}: {e}")
            # Only re-raise for authentication errors (401, 403)
            if e.status_code in [401, 403]:
                raise
    
    async def search(
        self, 
        query: str, 
        dataset_id: str, 
        limit: int = 10,
        similarity_threshold: float = 0.1,
        offset: int = 0,
        **kwargs: Any
    ) -> SearchResult:
        """Search in RAGFlow knowledge base.
        
        Args:
            query: Search query string
            dataset_id: ID of the dataset to search
            limit: Maximum number of results to return (default: 10)
            similarity_threshold: Minimum similarity score (default: 0.1)
            offset: Number of results to skip for pagination (default: 0)
            **kwargs: Additional search parameters
            
        Returns:
            Search results with relevance scores
            
        Raises:
            ValidationError: If parameters are invalid
            APIError: If search fails
        """
        # Validate parameters
        if not query or not isinstance(query, str):
            raise ValidationError("Query must be a non-empty string", field="query")
        
        if not dataset_id or not isinstance(dataset_id, str):
            raise ValidationError("Dataset ID must be a non-empty string", field="dataset_id")
        
        if not isinstance(limit, int) or limit <= 0 or limit > 100:
            raise ValidationError("Limit must be an integer between 1 and 100", field="limit")
        
        if not isinstance(similarity_threshold, (int, float)) or similarity_threshold < 0 or similarity_threshold > 1:
            raise ValidationError("Similarity threshold must be a number between 0 and 1", field="similarity_threshold")
        
        if not isinstance(offset, int) or offset < 0:
            raise ValidationError("Offset must be a non-negative integer", field="offset")
        
        # Prepare search parameters according to RAGFlow API
        search_params = {
            "question": query.strip(),
            "dataset_ids": [dataset_id],
            "limit": limit,
            "similarity_threshold": similarity_threshold,
            "offset": offset
        }
        
        # Add any additional parameters
        for key, value in kwargs.items():
            if key not in search_params:  # Don't override main parameters
                search_params[key] = value
        
        logger.info(f"Searching in dataset {dataset_id} with query: '{query[:50]}{'...' if len(query) > 50 else ''}'")
        
        import time
        start_time = time.time()
        
        try:
            response_data = await self._make_request(
                method="POST",
                endpoint="/api/v1/retrieval",
                data=search_params
            )
            
            query_time = time.time() - start_time
            
            # Parse response according to RAGFlow API format
            if not response_data:
                response_data = {}
                
            data = self._safe_get(response_data, 'data', {})
            if not data:
                data = {}
                
            # RAGFlow returns chunks in data.chunks
            results_data = self._safe_get(data, 'chunks', [])
            if not results_data:
                results_data = []
                
            total_count = len(results_data)
            
            # Convert results to SearchItem objects
            search_items = []
            for item in results_data:
                if not item:
                    continue
                    
                # Handle RAGFlow response format
                content = self._safe_get(item, 'content', '')
                score = float(self._safe_get(item, 'similarity', 0.0))
                file_name = self._safe_get(item, 'document_name', 'unknown')
                file_id = self._safe_get(item, 'document_id', '')
                chunk_id = self._safe_get(item, 'id', '')
                
                # Filter by similarity threshold
                if score >= similarity_threshold:
                    search_items.append(SearchItem(
                        content=content,
                        score=score,
                        file_name=file_name,
                        file_id=file_id,
                        chunk_id=chunk_id
                    ))
            
            # Sort by score (highest first)
            search_items.sort(key=lambda x: x.score, reverse=True)
            
            # Apply limit after filtering and sorting
            search_items = search_items[:limit]
            
            logger.info(f"Search completed in {query_time:.2f}s, found {len(search_items)} results")
            
            return SearchResult(
                results=search_items,
                total_count=len(search_items),  # Count after filtering
                query_time=query_time
            )
            
        except Exception as e:
            if isinstance(e, (ValidationError, APIError, AuthenticationError)):
                raise
            logger.error(f"Unexpected error during search: {e}")
            raise APIError(f"Search failed: {e}")
    
    async def list_files(self, dataset_id: str, limit: int = 100, offset: int = 0) -> ListFilesResult:
        """List all files in a dataset.
        
        Args:
            dataset_id: ID of the dataset
            limit: Maximum number of files to return (default: 100)
            offset: Number of files to skip for pagination (default: 0)
            
        Returns:
            List of files with metadata
            
        Raises:
            ValidationError: If parameters are invalid
            APIError: If request fails
        """
        # Validate parameters
        if not dataset_id or not isinstance(dataset_id, str):
            raise ValidationError("Dataset ID must be a non-empty string", field="dataset_id")
        
        if not isinstance(limit, int) or limit <= 0 or limit > 1000:
            raise ValidationError("Limit must be an integer between 1 and 1000", field="limit")
        
        if not isinstance(offset, int) or offset < 0:
            raise ValidationError("Offset must be a non-negative integer", field="offset")
        
        logger.info(f"Listing files in dataset {dataset_id}")
        
        # Prepare query parameters
        params = {
            "dataset_id": dataset_id,
            "limit": limit,
            "offset": offset
        }
        
        response_data = await self._make_request(
            method="GET",
            endpoint=f"/api/v1/datasets/{dataset_id}/documents",
            params=params
        )
        
        # Parse response
        data = self._safe_get(response_data, 'data', response_data)
        
        # RAGFlow returns data as {"docs": [...], "total": N}
        if isinstance(data, dict) and 'docs' in data:
            files_data = data['docs']
            total_count = data.get('total', len(files_data))
        elif isinstance(data, list):
            files_data = data
            total_count = len(files_data)
        else:
            files_data = self._safe_get(data, 'files', self._safe_get(data, 'documents', []))
            total_count = len(files_data)
        
        # Convert to FileInfo objects
        from .models import FileInfo
        from datetime import datetime
        
        files = []
        for file_data in files_data:
            # Handle different response formats
            file_id = file_data.get('id', file_data.get('file_id', ''))
            name = file_data.get('name', file_data.get('filename', 'unknown'))
            size = file_data.get('size', file_data.get('file_size', 0))
            
            # Map RAGFlow status to our status format
            raw_status = file_data.get('status', 'unknown')
            run_status = file_data.get('run', 'UNSTART')
            
            # Determine status based on run field primarily
            if run_status == 'DONE':
                status = 'completed'
            elif run_status == 'RUNNING':
                status = 'processing'
            elif run_status == 'FAIL':
                status = 'failed'
            elif run_status == 'UNSTART':
                status = 'uploaded'
            else:
                status = 'uploaded'  # Default fallback
                
            chunk_count = file_data.get('chunk_count', file_data.get('chunks', 0))
            
            # Parse creation date
            created_at_str = file_data.get('created_at', file_data.get('upload_time'))
            if created_at_str:
                try:
                    # Try different date formats
                    if isinstance(created_at_str, str):
                        # ISO format
                        if 'T' in created_at_str:
                            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        else:
                            # Assume timestamp
                            created_at = datetime.fromtimestamp(float(created_at_str))
                    else:
                        # Assume timestamp
                        created_at = datetime.fromtimestamp(float(created_at_str))
                except (ValueError, TypeError):
                    created_at = datetime.now()
            else:
                created_at = datetime.now()
            
            files.append(FileInfo(
                file_id=file_id,
                name=name,
                size=size,
                created_at=created_at,
                status=status,
                chunk_count=chunk_count
            ))
        
        logger.info(f"Found {len(files)} files in dataset {dataset_id}")
        
        return ListFilesResult(
            files=files,
            total_count=total_count
        )
    
    async def get_datasets(self, limit: int = 100, offset: int = 0) -> 'ListDatasetsResult':
        """Get list of available datasets.
        
        Args:
            limit: Maximum number of datasets to return (ignored by API)
            offset: Number of datasets to skip for pagination (ignored by API)
            
        Returns:
            List of available datasets
            
        Raises:
            APIError: If request fails
        """
        logger.info("Getting list of datasets")
        
        # RAGFlow API doesn't support pagination parameters for datasets endpoint
        response_data = await self._make_request(
            method="GET",
            endpoint="/api/v1/datasets"
        )
        
        # Check for API error response
        if isinstance(response_data, dict) and 'code' in response_data:
            code = response_data.get('code')
            message = response_data.get('message', 'Unknown error')
            
            # Handle authentication errors
            if code == 109:  # Authentication error code
                raise AuthenticationError(f"Authentication failed: {message}")
            elif code != 0 and code is not None:  # Other error codes (0 typically means success)
                raise APIError(f"API error (code {code}): {message}")
        
        # Parse response - handle case where response might be None or not a dict
        if response_data is None:
            logger.warning("Received None response from API")
            datasets_data = []
            total_count = 0
        elif not isinstance(response_data, dict):
            logger.warning(f"Expected dict response, got {type(response_data)}: {response_data}")
            # If response is not a dict, assume empty dataset list
            datasets_data = []
            total_count = 0
        else:
            data = response_data.get('data', response_data)
            if isinstance(data, list):
                # RAGFlow returns data as a list directly
                datasets_data = data
                total_count = len(datasets_data)
            elif isinstance(data, dict):
                # Some APIs return data wrapped in an object
                datasets_data = data.get('datasets', data.get('items', []))
                total_count = data.get('total', len(datasets_data))
            else:
                # If data is not a dict or list (e.g., False for auth errors), return empty list
                logger.info("No datasets data available (possibly due to authentication or other issues)")
                datasets_data = []
                total_count = 0
        
        # Convert to Dataset objects
        from .models import Dataset
        from datetime import datetime
        
        datasets = []
        for dataset_data in datasets_data:
            # Handle different response formats
            dataset_id = dataset_data.get('id', dataset_data.get('dataset_id', ''))
            name = dataset_data.get('name', dataset_data.get('title', 'unknown'))
            description = dataset_data.get('description', dataset_data.get('desc'))
            file_count = dataset_data.get('file_count', dataset_data.get('document_count', 0))
            
            # Parse creation date
            created_at_str = dataset_data.get('created_at', dataset_data.get('create_time'))
            if created_at_str:
                try:
                    if isinstance(created_at_str, str):
                        if 'T' in created_at_str:
                            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        else:
                            # Convert string to number first
                            timestamp = float(created_at_str)
                            # If timestamp is in milliseconds, convert to seconds
                            if timestamp > 1e10:
                                timestamp = timestamp / 1000
                            created_at = datetime.fromtimestamp(timestamp)
                    else:
                        # Handle numeric timestamps
                        timestamp = float(created_at_str)
                        # If timestamp is in milliseconds, convert to seconds
                        if timestamp > 1e10:
                            timestamp = timestamp / 1000
                        created_at = datetime.fromtimestamp(timestamp)
                except (ValueError, TypeError, OSError):
                    created_at = None
            else:
                created_at = None
            
            datasets.append(Dataset(
                dataset_id=dataset_id,
                name=name,
                description=description,
                file_count=file_count,
                created_at=created_at
            ))
        
        logger.info(f"Found {len(datasets)} datasets")
        
        from .models import ListDatasetsResult
        return ListDatasetsResult(
            datasets=datasets,
            total_count=total_count
        )
    
    async def delete_file(self, file_id: str, dataset_id: str, confirm: bool = False) -> DeleteResult:
        """Delete a file from RAGFlow.
        
        Args:
            file_id: ID of the file to delete
            dataset_id: ID of the dataset containing the file
            confirm: Confirmation flag to prevent accidental deletion
            
        Returns:
            Delete result with confirmation
            
        Raises:
            ValidationError: If parameters are invalid
            APIError: If deletion fails
        """
        # Validate parameters
        if not file_id or not isinstance(file_id, str):
            raise ValidationError("File ID must be a non-empty string", field="file_id")
        
        if not confirm:
            raise ValidationError("Deletion must be confirmed by setting confirm=True", field="confirm")
        
        logger.info(f"Deleting file {file_id} from dataset {dataset_id}")
        
        try:
            # Use correct RAGFlow delete endpoint with proper parameter name
            response_data = await self._make_request(
                method="DELETE",
                endpoint=f"/api/v1/datasets/{dataset_id}/documents",
                data={"ids": [file_id]}  # Correct parameter name is "ids", not "document_ids"
            )
            
            # Parse response
            if not response_data:
                response_data = {}
                
            code = self._safe_get(response_data, 'code', 0)
            message = self._safe_get(response_data, 'message', f'File {file_id} deleted successfully')
            
            if code == 0:
                status = 'success'
            else:
                status = 'failed'
            
            logger.info(f"File {file_id} deleted successfully")
            
            return DeleteResult(
                file_id=file_id,
                status=status,
                message=message
            )
            
        except APIError as e:
            if e.status_code == 404:
                logger.warning(f"File {file_id} not found for deletion")
                return DeleteResult(
                    file_id=file_id,
                    status="not_found",
                    message=f"File {file_id} not found"
                )
            else:
                logger.error(f"Failed to delete file {file_id}: {e}")
                raise
    
    async def get_file_status(self, file_id: str, dataset_id: str = None) -> FileStatus:
        """Get the status of a file.
        
        Args:
            file_id: ID of the file
            dataset_id: ID of the dataset (optional, will try to find if not provided)
            
        Returns:
            File status information
            
        Raises:
            ValidationError: If file_id is invalid
            APIError: If request fails
        """
        if not file_id or not isinstance(file_id, str):
            raise ValidationError("File ID must be a non-empty string", field="file_id")
        
        logger.debug(f"Getting status for file {file_id}")
        
        # Get file info by listing files and finding the specific one
        try:
            if dataset_id:
                # List all files in dataset and find the specific file
                files_result = await self.list_files(dataset_id, limit=1000)
                file_data = None
                for file_info in files_result.files:
                    if file_info.file_id == file_id:
                        # Convert FileInfo back to dict for processing
                        file_data = {
                            'id': file_info.file_id,
                            'name': file_info.name,
                            'size': file_info.size,
                            'run': 'DONE' if file_info.chunk_count and file_info.chunk_count > 0 else 'UNSTART',
                            'chunk_count': file_info.chunk_count,
                            'progress': 1.0 if file_info.chunk_count and file_info.chunk_count > 0 else 0.0
                        }
                        break
                
                if not file_data:
                    raise APIError(f"File {file_id} not found in dataset {dataset_id}")
                    
            else:
                # If no dataset_id provided, try to find the file by listing all datasets
                datasets = await self.get_datasets()
                file_data = None
                for dataset in datasets.datasets:
                    try:
                        files_result = await self.list_files(dataset.dataset_id, limit=1000)
                        for file_info in files_result.files:
                            if file_info.file_id == file_id:
                                file_data = {
                                    'id': file_info.file_id,
                                    'name': file_info.name,
                                    'size': file_info.size,
                                    'run': 'DONE' if file_info.chunk_count and file_info.chunk_count > 0 else 'UNSTART',
                                    'chunk_count': file_info.chunk_count,
                                    'progress': 1.0 if file_info.chunk_count and file_info.chunk_count > 0 else 0.0
                                }
                                break
                    except APIError:
                        continue
                
                if not file_data:
                    raise APIError(f"File {file_id} not found in any dataset")
            
            # Map RAGFlow status to our status
            ragflow_status = self._safe_get(file_data, 'run', 'unknown')
            status_mapping = {
                'UNSTART': 'uploaded',
                'RUNNING': 'processing', 
                'CANCEL': 'failed',
                'DONE': 'completed',
                'FAIL': 'failed'
            }
            status = status_mapping.get(ragflow_status, 'unknown')
            
            return FileStatus(
                file_id=file_id,
                status=status,
                progress=self._safe_get(file_data, 'progress'),
                error_message=self._safe_get(file_data, 'error_message'),
                chunk_count=self._safe_get(file_data, 'chunk_count')
            )
            
        except APIError:
            # If specific endpoint fails, return basic status
            return FileStatus(
                file_id=file_id,
                status='UNKNOWN',
                progress=None,
                error_message=None,
                chunk_count=None
            )