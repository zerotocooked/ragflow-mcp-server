"""Unit tests for RAGFlow MCP Server data models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from ragflow_mcp_server.models import (
    UploadResult,
    UpdateResult,
    SearchItem,
    SearchResult,
    FileInfo,
    ListFilesResult,
    DeleteResult,
    FileStatus,
    Dataset,
    ListDatasetsResult,
)


class TestUploadResult:
    """Test cases for UploadResult model."""
    
    def test_valid_upload_result(self):
        """Test creating a valid UploadResult."""
        result = UploadResult(
            file_id="file123",
            status="success",
            message="File uploaded successfully",
            chunk_count=5
        )
        
        assert result.file_id == "file123"
        assert result.status == "success"
        assert result.message == "File uploaded successfully"
        assert result.chunk_count == 5
    
    def test_upload_result_without_chunk_count(self):
        """Test UploadResult without optional chunk_count."""
        result = UploadResult(
            file_id="file123",
            status="processing",
            message="File is being processed"
        )
        
        assert result.chunk_count is None
    
    def test_invalid_status(self):
        """Test UploadResult with invalid status."""
        with pytest.raises(ValidationError) as exc_info:
            UploadResult(
                file_id="file123",
                status="invalid_status",
                message="Test message"
            )
        
        assert "Status must be one of" in str(exc_info.value)
    
    def test_missing_required_fields(self):
        """Test UploadResult with missing required fields."""
        with pytest.raises(ValidationError):
            UploadResult(file_id="file123")  # Missing status and message


class TestUpdateResult:
    """Test cases for UpdateResult model."""
    
    def test_valid_update_result(self):
        """Test creating a valid UpdateResult."""
        result = UpdateResult(
            file_id="file123",
            status="success",
            message="File updated successfully",
            chunk_count=7
        )
        
        assert result.file_id == "file123"
        assert result.status == "success"
        assert result.chunk_count == 7
    
    def test_invalid_status(self):
        """Test UpdateResult with invalid status."""
        with pytest.raises(ValidationError):
            UpdateResult(
                file_id="file123",
                status="unknown",
                message="Test message"
            )


class TestSearchItem:
    """Test cases for SearchItem model."""
    
    def test_valid_search_item(self):
        """Test creating a valid SearchItem."""
        item = SearchItem(
            content="This is a test content",
            score=0.85,
            file_name="test.txt",
            file_id="file123",
            chunk_id="chunk456"
        )
        
        assert item.content == "This is a test content"
        assert item.score == 0.85
        assert item.file_name == "test.txt"
        assert item.file_id == "file123"
        assert item.chunk_id == "chunk456"
    
    def test_score_validation(self):
        """Test SearchItem score validation."""
        # Test valid scores
        SearchItem(
            content="test",
            score=0.0,
            file_name="test.txt",
            file_id="file123",
            chunk_id="chunk456"
        )
        
        SearchItem(
            content="test",
            score=1.0,
            file_name="test.txt",
            file_id="file123",
            chunk_id="chunk456"
        )
        
        # Test invalid scores
        with pytest.raises(ValidationError):
            SearchItem(
                content="test",
                score=-0.1,  # Below 0
                file_name="test.txt",
                file_id="file123",
                chunk_id="chunk456"
            )
        
        with pytest.raises(ValidationError):
            SearchItem(
                content="test",
                score=1.1,  # Above 1
                file_name="test.txt",
                file_id="file123",
                chunk_id="chunk456"
            )


class TestSearchResult:
    """Test cases for SearchResult model."""
    
    def test_valid_search_result(self):
        """Test creating a valid SearchResult."""
        items = [
            SearchItem(
                content="Content 1",
                score=0.9,
                file_name="file1.txt",
                file_id="file1",
                chunk_id="chunk1"
            ),
            SearchItem(
                content="Content 2",
                score=0.7,
                file_name="file2.txt",
                file_id="file2",
                chunk_id="chunk2"
            )
        ]
        
        result = SearchResult(
            results=items,
            total_count=2,
            query_time=0.15
        )
        
        assert len(result.results) == 2
        assert result.total_count == 2
        assert result.query_time == 0.15
    
    def test_empty_search_result(self):
        """Test SearchResult with no results."""
        result = SearchResult(
            results=[],
            total_count=0,
            query_time=0.05
        )
        
        assert len(result.results) == 0
        assert result.total_count == 0
    
    def test_negative_total_count(self):
        """Test SearchResult with negative total_count."""
        with pytest.raises(ValidationError):
            SearchResult(
                results=[],
                total_count=-1,
                query_time=0.05
            )
    
    def test_negative_query_time(self):
        """Test SearchResult with negative query_time."""
        with pytest.raises(ValidationError):
            SearchResult(
                results=[],
                total_count=0,
                query_time=-0.1
            )


class TestFileInfo:
    """Test cases for FileInfo model."""
    
    def test_valid_file_info(self):
        """Test creating a valid FileInfo."""
        created_at = datetime.now()
        file_info = FileInfo(
            file_id="file123",
            name="document.pdf",
            size=1024000,
            created_at=created_at,
            status="completed",
            chunk_count=10
        )
        
        assert file_info.file_id == "file123"
        assert file_info.name == "document.pdf"
        assert file_info.size == 1024000
        assert file_info.created_at == created_at
        assert file_info.status == "completed"
        assert file_info.chunk_count == 10
    
    def test_file_info_without_chunk_count(self):
        """Test FileInfo without optional chunk_count."""
        file_info = FileInfo(
            file_id="file123",
            name="document.pdf",
            size=1024000,
            created_at=datetime.now(),
            status="processing"
        )
        
        assert file_info.chunk_count is None
    
    def test_invalid_status(self):
        """Test FileInfo with invalid status."""
        with pytest.raises(ValidationError):
            FileInfo(
                file_id="file123",
                name="document.pdf",
                size=1024000,
                created_at=datetime.now(),
                status="invalid_status"
            )
    
    def test_negative_size(self):
        """Test FileInfo with negative size."""
        with pytest.raises(ValidationError):
            FileInfo(
                file_id="file123",
                name="document.pdf",
                size=-100,
                created_at=datetime.now(),
                status="completed"
            )
    
    def test_negative_chunk_count(self):
        """Test FileInfo with negative chunk_count."""
        with pytest.raises(ValidationError):
            FileInfo(
                file_id="file123",
                name="document.pdf",
                size=1024000,
                created_at=datetime.now(),
                status="completed",
                chunk_count=-1
            )


class TestListFilesResult:
    """Test cases for ListFilesResult model."""
    
    def test_valid_list_files_result(self):
        """Test creating a valid ListFilesResult."""
        files = [
            FileInfo(
                file_id="file1",
                name="doc1.pdf",
                size=1000,
                created_at=datetime.now(),
                status="completed"
            ),
            FileInfo(
                file_id="file2",
                name="doc2.txt",
                size=2000,
                created_at=datetime.now(),
                status="processing"
            )
        ]
        
        result = ListFilesResult(
            files=files,
            total_count=2
        )
        
        assert len(result.files) == 2
        assert result.total_count == 2
    
    def test_empty_list_files_result(self):
        """Test ListFilesResult with no files."""
        result = ListFilesResult(
            files=[],
            total_count=0
        )
        
        assert len(result.files) == 0
        assert result.total_count == 0


class TestDeleteResult:
    """Test cases for DeleteResult model."""
    
    def test_valid_delete_result(self):
        """Test creating a valid DeleteResult."""
        result = DeleteResult(
            file_id="file123",
            status="success",
            message="File deleted successfully"
        )
        
        assert result.file_id == "file123"
        assert result.status == "success"
        assert result.message == "File deleted successfully"
    
    def test_invalid_status(self):
        """Test DeleteResult with invalid status."""
        with pytest.raises(ValidationError):
            DeleteResult(
                file_id="file123",
                status="unknown",
                message="Test message"
            )


class TestFileStatus:
    """Test cases for FileStatus model."""
    
    def test_valid_file_status(self):
        """Test creating a valid FileStatus."""
        status = FileStatus(
            file_id="file123",
            status="processing",
            progress=0.75,
            error_message=None,
            chunk_count=5
        )
        
        assert status.file_id == "file123"
        assert status.status == "processing"
        assert status.progress == 0.75
        assert status.error_message is None
        assert status.chunk_count == 5
    
    def test_file_status_with_error(self):
        """Test FileStatus with error message."""
        status = FileStatus(
            file_id="file123",
            status="failed",
            error_message="Processing failed due to invalid format"
        )
        
        assert status.status == "failed"
        assert status.error_message == "Processing failed due to invalid format"
        assert status.progress is None
    
    def test_invalid_progress(self):
        """Test FileStatus with invalid progress values."""
        with pytest.raises(ValidationError):
            FileStatus(
                file_id="file123",
                status="processing",
                progress=-0.1  # Below 0
            )
        
        with pytest.raises(ValidationError):
            FileStatus(
                file_id="file123",
                status="processing",
                progress=1.1  # Above 1
            )
    
    def test_invalid_status(self):
        """Test FileStatus with invalid status."""
        with pytest.raises(ValidationError):
            FileStatus(
                file_id="file123",
                status="unknown_status"
            )


class TestDataset:
    """Test cases for Dataset model."""
    
    def test_valid_dataset(self):
        """Test creating a valid Dataset."""
        created_at = datetime.now()
        dataset = Dataset(
            dataset_id="dataset123",
            name="My Dataset",
            description="A test dataset",
            file_count=10,
            created_at=created_at
        )
        
        assert dataset.dataset_id == "dataset123"
        assert dataset.name == "My Dataset"
        assert dataset.description == "A test dataset"
        assert dataset.file_count == 10
        assert dataset.created_at == created_at
    
    def test_dataset_with_defaults(self):
        """Test Dataset with default values."""
        dataset = Dataset(
            dataset_id="dataset123",
            name="My Dataset"
        )
        
        assert dataset.description is None
        assert dataset.file_count == 0
        assert dataset.created_at is None
    
    def test_negative_file_count(self):
        """Test Dataset with negative file_count."""
        with pytest.raises(ValidationError):
            Dataset(
                dataset_id="dataset123",
                name="My Dataset",
                file_count=-1
            )


class TestListDatasetsResult:
    """Test cases for ListDatasetsResult model."""
    
    def test_valid_list_datasets_result(self):
        """Test creating a valid ListDatasetsResult."""
        datasets = [
            Dataset(
                dataset_id="dataset1",
                name="Dataset 1",
                file_count=5
            ),
            Dataset(
                dataset_id="dataset2",
                name="Dataset 2",
                file_count=3
            )
        ]
        
        result = ListDatasetsResult(
            datasets=datasets,
            total_count=2
        )
        
        assert len(result.datasets) == 2
        assert result.total_count == 2
    
    def test_empty_list_datasets_result(self):
        """Test ListDatasetsResult with no datasets."""
        result = ListDatasetsResult(
            datasets=[],
            total_count=0
        )
        
        assert len(result.datasets) == 0
        assert result.total_count == 0


class TestModelSerialization:
    """Test cases for model serialization and deserialization."""
    
    def test_upload_result_serialization(self):
        """Test UploadResult JSON serialization."""
        result = UploadResult(
            file_id="file123",
            status="success",
            message="Upload completed",
            chunk_count=5
        )
        
        # Test to dict
        data = result.model_dump()
        assert data["file_id"] == "file123"
        assert data["status"] == "success"
        assert data["chunk_count"] == 5
        
        # Test from dict
        new_result = UploadResult(**data)
        assert new_result.file_id == result.file_id
        assert new_result.status == result.status
        assert new_result.chunk_count == result.chunk_count
    
    def test_search_result_serialization(self):
        """Test SearchResult JSON serialization with nested objects."""
        items = [
            SearchItem(
                content="Test content",
                score=0.9,
                file_name="test.txt",
                file_id="file1",
                chunk_id="chunk1"
            )
        ]
        
        result = SearchResult(
            results=items,
            total_count=1,
            query_time=0.1
        )
        
        # Test to dict
        data = result.model_dump()
        assert len(data["results"]) == 1
        assert data["results"][0]["content"] == "Test content"
        assert data["results"][0]["score"] == 0.9
        
        # Test from dict
        new_result = SearchResult(**data)
        assert len(new_result.results) == 1
        assert new_result.results[0].content == "Test content"
        assert new_result.results[0].score == 0.9
    
    def test_file_info_datetime_serialization(self):
        """Test FileInfo datetime serialization."""
        created_at = datetime.now()
        file_info = FileInfo(
            file_id="file123",
            name="test.pdf",
            size=1000,
            created_at=created_at,
            status="completed"
        )
        
        # Test to dict
        data = file_info.model_dump()
        assert "created_at" in data
        
        # Test from dict
        new_file_info = FileInfo(**data)
        assert new_file_info.created_at == created_at