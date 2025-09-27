"""Data models for RAGFlow MCP Server."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class UploadResult(BaseModel):
    """Result of file upload operation."""
    
    file_id: str = Field(..., description="Unique identifier for the uploaded file")
    status: str = Field(..., description="Upload status (success, failed, processing)")
    message: str = Field(..., description="Human-readable status message")
    chunk_count: Optional[int] = Field(None, description="Number of chunks created from the file")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        allowed_statuses = ['success', 'failed', 'processing', 'pending']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of {allowed_statuses}')
        return v


class UpdateResult(BaseModel):
    """Result of file update operation."""
    
    file_id: str = Field(..., description="Unique identifier for the updated file")
    status: str = Field(..., description="Update status (success, failed, processing)")
    message: str = Field(..., description="Human-readable status message")
    chunk_count: Optional[int] = Field(None, description="Number of chunks after update")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        allowed_statuses = ['success', 'failed', 'processing', 'pending']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of {allowed_statuses}')
        return v


class SearchItem(BaseModel):
    """Individual search result item."""
    
    content: str = Field(..., description="Text content of the search result")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score between 0 and 1")
    file_name: str = Field(..., description="Name of the source file")
    file_id: str = Field(..., description="Unique identifier of the source file")
    chunk_id: str = Field(..., description="Unique identifier of the text chunk")


class SearchResult(BaseModel):
    """Result of search operation."""
    
    results: List[SearchItem] = Field(..., description="List of search results")
    total_count: int = Field(..., ge=0, description="Total number of results found")
    query_time: float = Field(..., ge=0.0, description="Time taken to execute the query in seconds")


class FileInfo(BaseModel):
    """Information about a file in RAGFlow."""
    
    file_id: str = Field(..., description="Unique identifier for the file")
    name: str = Field(..., description="Original filename")
    size: int = Field(..., ge=0, description="File size in bytes")
    created_at: datetime = Field(..., description="File creation timestamp")
    status: str = Field(..., description="Current file processing status")
    chunk_count: Optional[int] = Field(None, ge=0, description="Number of chunks created from the file")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        allowed_statuses = ['uploaded', 'processing', 'completed', 'failed', 'deleted']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of {allowed_statuses}')
        return v


class ListFilesResult(BaseModel):
    """Result of list files operation."""
    
    files: List[FileInfo] = Field(..., description="List of files in the dataset")
    total_count: int = Field(..., ge=0, description="Total number of files")


class DeleteResult(BaseModel):
    """Result of delete file operation."""
    
    file_id: str = Field(..., description="Unique identifier of the deleted file")
    status: str = Field(..., description="Deletion status")
    message: str = Field(..., description="Human-readable status message")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        allowed_statuses = ['success', 'failed', 'not_found']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of {allowed_statuses}')
        return v


class FileStatus(BaseModel):
    """Status information for a file."""
    
    file_id: str = Field(..., description="Unique identifier for the file")
    status: str = Field(..., description="Current processing status")
    progress: Optional[float] = Field(None, ge=0.0, le=1.0, description="Processing progress (0.0 to 1.0)")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    chunk_count: Optional[int] = Field(None, ge=0, description="Number of chunks created")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        allowed_statuses = ['uploaded', 'processing', 'completed', 'failed', 'PENDING', 'PROCESSING', 'DONE', 'FAILED', 'UNKNOWN', 'unknown']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of {allowed_statuses}')
        return v


class Dataset(BaseModel):
    """Information about a RAGFlow dataset."""
    
    dataset_id: str = Field(..., description="Unique identifier for the dataset")
    name: str = Field(..., description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")
    file_count: int = Field(0, ge=0, description="Number of files in the dataset")
    created_at: Optional[datetime] = Field(None, description="Dataset creation timestamp")


class DatasetInfo(BaseModel):
    """Information about a dataset."""
    
    dataset_id: str = Field(..., description="Unique identifier for the dataset")
    name: str = Field(..., description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")
    file_count: int = Field(0, ge=0, description="Number of files in the dataset")
    created_at: Optional[datetime] = Field(None, description="Dataset creation timestamp")


class DatasetsResult(BaseModel):
    """Result of get datasets operation."""
    
    datasets: List[DatasetInfo] = Field(..., description="List of available datasets")
    total_count: int = Field(..., ge=0, description="Total number of datasets")


class ListDatasetsResult(BaseModel):
    """Result of list datasets operation."""
    
    datasets: List[Dataset] = Field(..., description="List of available datasets")
    total_count: int = Field(..., ge=0, description="Total number of datasets")