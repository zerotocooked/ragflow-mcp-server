"""Unit tests for configuration management."""

import os
import pytest
from unittest.mock import patch, mock_open
from pydantic import ValidationError as PydanticValidationError

from ragflow_mcp_server.config import RAGFlowConfig
from ragflow_mcp_server.errors import ConfigurationError


class TestRAGFlowConfig:
    """Test cases for RAGFlowConfig class."""
    
    def test_valid_config_creation(self):
        """Test creating a valid configuration."""
        config = RAGFlowConfig(
            base_url="https://api.ragflow.com",
            api_key="test-api-key",
            default_dataset_id="dataset-123",
            timeout=60,
            max_retries=5
        )
        
        assert config.base_url == "https://api.ragflow.com"
        assert config.api_key == "test-api-key"
        assert config.default_dataset_id == "dataset-123"
        assert config.timeout == 60
        assert config.max_retries == 5
    
    def test_config_with_defaults(self):
        """Test creating configuration with default values."""
        config = RAGFlowConfig(
            base_url="https://api.ragflow.com",
            api_key="test-api-key"
        )
        
        assert config.base_url == "https://api.ragflow.com"
        assert config.api_key == "test-api-key"
        assert config.default_dataset_id is None
        assert config.timeout == 30
        assert config.max_retries == 3
    
    def test_base_url_validation_removes_trailing_slash(self):
        """Test that trailing slash is removed from base URL."""
        config = RAGFlowConfig(
            base_url="https://api.ragflow.com/",
            api_key="test-api-key"
        )
        
        assert config.base_url == "https://api.ragflow.com"
    
    def test_base_url_validation_requires_protocol(self):
        """Test that base URL must have http/https protocol."""
        with pytest.raises(PydanticValidationError) as exc_info:
            RAGFlowConfig(
                base_url="api.ragflow.com",
                api_key="test-api-key"
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("base_url",)
        assert "must start with http://" in errors[0]["msg"]
    
    def test_empty_base_url_validation(self):
        """Test that empty base URL is rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            RAGFlowConfig(
                base_url="",
                api_key="test-api-key"
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("base_url",)
        assert "cannot be empty" in errors[0]["msg"]
    
    def test_empty_api_key_validation(self):
        """Test that empty API key is rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            RAGFlowConfig(
                base_url="https://api.ragflow.com",
                api_key=""
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("api_key",)
        assert "cannot be empty" in errors[0]["msg"]
    
    def test_whitespace_api_key_validation(self):
        """Test that whitespace-only API key is rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            RAGFlowConfig(
                base_url="https://api.ragflow.com",
                api_key="   "
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("api_key",)
        assert "cannot be empty" in errors[0]["msg"]
    
    def test_api_key_strips_whitespace(self):
        """Test that API key whitespace is stripped."""
        config = RAGFlowConfig(
            base_url="https://api.ragflow.com",
            api_key="  test-api-key  "
        )
        
        assert config.api_key == "test-api-key"
    
    def test_negative_timeout_validation(self):
        """Test that negative timeout is rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            RAGFlowConfig(
                base_url="https://api.ragflow.com",
                api_key="test-api-key",
                timeout=-1
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("timeout",)
        assert "greater than 0" in errors[0]["msg"]
    
    def test_zero_timeout_validation(self):
        """Test that zero timeout is rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            RAGFlowConfig(
                base_url="https://api.ragflow.com",
                api_key="test-api-key",
                timeout=0
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("timeout",)
        assert "greater than 0" in errors[0]["msg"]
    
    def test_negative_max_retries_validation(self):
        """Test that negative max_retries is rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            RAGFlowConfig(
                base_url="https://api.ragflow.com",
                api_key="test-api-key",
                max_retries=-1
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("max_retries",)
        assert "greater than or equal to 0" in errors[0]["msg"]
    
    def test_zero_max_retries_allowed(self):
        """Test that zero max_retries is allowed."""
        config = RAGFlowConfig(
            base_url="https://api.ragflow.com",
            api_key="test-api-key",
            max_retries=0
        )
        
        assert config.max_retries == 0
    
    def test_default_dataset_id_strips_whitespace(self):
        """Test that default_dataset_id whitespace is stripped."""
        config = RAGFlowConfig(
            base_url="https://api.ragflow.com",
            api_key="test-api-key",
            default_dataset_id="  dataset-123  "
        )
        
        assert config.default_dataset_id == "dataset-123"
    
    def test_empty_default_dataset_id_becomes_none(self):
        """Test that empty default_dataset_id becomes None."""
        config = RAGFlowConfig(
            base_url="https://api.ragflow.com",
            api_key="test-api-key",
            default_dataset_id="   "
        )
        
        assert config.default_dataset_id is None
    
    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(PydanticValidationError) as exc_info:
            RAGFlowConfig(
                base_url="https://api.ragflow.com",
                api_key="test-api-key",
                extra_field="not-allowed"
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "extra_forbidden"


class TestRAGFlowConfigFromEnv:
    """Test cases for loading configuration from environment variables."""
    
    @patch.dict(os.environ, {
        "RAGFLOW_BASE_URL": "https://api.ragflow.com",
        "RAGFLOW_API_KEY": "test-api-key",
        "RAGFLOW_DEFAULT_DATASET_ID": "dataset-123",
        "RAGFLOW_TIMEOUT": "60",
        "RAGFLOW_MAX_RETRIES": "5"
    })
    @patch("ragflow_mcp_server.config.load_dotenv")
    def test_from_env_all_values(self, mock_load_dotenv):
        """Test loading all configuration values from environment."""
        config = RAGFlowConfig.from_env()
        
        assert config.base_url == "https://api.ragflow.com"
        assert config.api_key == "test-api-key"
        assert config.default_dataset_id == "dataset-123"
        assert config.timeout == 60
        assert config.max_retries == 5
        mock_load_dotenv.assert_called_once()
    
    @patch.dict(os.environ, {
        "RAGFLOW_BASE_URL": "https://api.ragflow.com/",
        "RAGFLOW_API_KEY": "test-api-key"
    })
    @patch("ragflow_mcp_server.config.load_dotenv")
    def test_from_env_required_only(self, mock_load_dotenv):
        """Test loading only required configuration from environment."""
        config = RAGFlowConfig.from_env()
        
        assert config.base_url == "https://api.ragflow.com"
        assert config.api_key == "test-api-key"
        assert config.default_dataset_id is None
        assert config.timeout == 30
        assert config.max_retries == 3
        mock_load_dotenv.assert_called_once()
    
    @patch.dict(os.environ, {
        "RAGFLOW_API_KEY": "test-api-key"
    }, clear=True)
    @patch("ragflow_mcp_server.config.load_dotenv")
    def test_from_env_missing_base_url(self, mock_load_dotenv):
        """Test error when RAGFLOW_BASE_URL is missing."""
        with pytest.raises(ConfigurationError) as exc_info:
            RAGFlowConfig.from_env()
        
        assert "RAGFLOW_BASE_URL environment variable is required" in str(exc_info.value)
        mock_load_dotenv.assert_called_once()
    
    @patch.dict(os.environ, {
        "RAGFLOW_BASE_URL": "https://api.ragflow.com"
    }, clear=True)
    @patch("ragflow_mcp_server.config.load_dotenv")
    def test_from_env_missing_api_key(self, mock_load_dotenv):
        """Test error when RAGFLOW_API_KEY is missing."""
        with pytest.raises(ConfigurationError) as exc_info:
            RAGFlowConfig.from_env()
        
        assert "RAGFLOW_API_KEY environment variable is required" in str(exc_info.value)
        mock_load_dotenv.assert_called_once()
    
    @patch.dict(os.environ, {
        "RAGFLOW_BASE_URL": "https://api.ragflow.com",
        "RAGFLOW_API_KEY": "test-api-key",
        "RAGFLOW_TIMEOUT": "invalid"
    })
    @patch("ragflow_mcp_server.config.load_dotenv")
    def test_from_env_invalid_timeout(self, mock_load_dotenv):
        """Test error when RAGFLOW_TIMEOUT is not a valid integer."""
        with pytest.raises(ConfigurationError) as exc_info:
            RAGFlowConfig.from_env()
        
        assert "Invalid RAGFLOW_TIMEOUT value" in str(exc_info.value)
        mock_load_dotenv.assert_called_once()
    
    @patch.dict(os.environ, {
        "RAGFLOW_BASE_URL": "https://api.ragflow.com",
        "RAGFLOW_API_KEY": "test-api-key",
        "RAGFLOW_MAX_RETRIES": "invalid"
    })
    @patch("ragflow_mcp_server.config.load_dotenv")
    def test_from_env_invalid_max_retries(self, mock_load_dotenv):
        """Test error when RAGFLOW_MAX_RETRIES is not a valid integer."""
        with pytest.raises(ConfigurationError) as exc_info:
            RAGFlowConfig.from_env()
        
        assert "Invalid RAGFLOW_MAX_RETRIES value" in str(exc_info.value)
        mock_load_dotenv.assert_called_once()
    
    @patch.dict(os.environ, {
        "RAGFLOW_BASE_URL": "invalid-url",
        "RAGFLOW_API_KEY": "test-api-key"
    })
    @patch("ragflow_mcp_server.config.load_dotenv")
    def test_from_env_invalid_base_url(self, mock_load_dotenv):
        """Test error when base URL format is invalid."""
        with pytest.raises(ConfigurationError) as exc_info:
            RAGFlowConfig.from_env()
        
        assert "Configuration validation failed" in str(exc_info.value)
        assert "must start with http://" in str(exc_info.value)
        mock_load_dotenv.assert_called_once()
    
    @patch.dict(os.environ, {
        "RAGFLOW_BASE_URL": "https://api.ragflow.com",
        "RAGFLOW_API_KEY": "test-api-key",
        "RAGFLOW_TIMEOUT": "-1"
    })
    @patch("ragflow_mcp_server.config.load_dotenv")
    def test_from_env_negative_timeout(self, mock_load_dotenv):
        """Test error when timeout is negative."""
        with pytest.raises(ConfigurationError) as exc_info:
            RAGFlowConfig.from_env()
        
        assert "Configuration validation failed" in str(exc_info.value)
        assert "greater than 0" in str(exc_info.value)
        mock_load_dotenv.assert_called_once()


class TestRAGFlowConfigValidation:
    """Test cases for configuration validation method."""
    
    def test_validate_config_success(self):
        """Test successful configuration validation."""
        config = RAGFlowConfig(
            base_url="https://api.ragflow.com",
            api_key="test-api-key"
        )
        
        # Should not raise any exception
        config.validate_config()
    
    def test_validate_config_with_modified_invalid_data(self):
        """Test validation fails when config is manually modified to invalid state."""
        config = RAGFlowConfig(
            base_url="https://api.ragflow.com",
            api_key="test-api-key"
        )
        
        # Manually modify the config to invalid state (bypassing Pydantic validation)
        config.__dict__["timeout"] = -1
        
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate_config()
        
        assert "Configuration validation failed" in str(exc_info.value)