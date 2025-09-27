"""Configuration management for RAGFlow MCP Server."""

import os
from typing import Optional
import logging

from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationError as PydanticValidationError
from dotenv import load_dotenv
from .errors import ConfigurationError


logger = logging.getLogger(__name__)


class RAGFlowConfig(BaseModel):
    """Configuration model for RAGFlow MCP Server using Pydantic validation."""
    
    base_url: str = Field(..., description="RAGFlow API base URL")
    api_key: str = Field(..., description="RAGFlow API key")
    default_dataset_id: Optional[str] = Field(None, description="Default dataset ID")
    timeout: int = Field(120, gt=0, description="Request timeout in seconds")
    max_retries: int = Field(3, ge=0, description="Maximum number of retries")
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid"
    )
    
    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate base URL format and normalize it.
        
        Args:
            v: Base URL value
            
        Returns:
            Normalized base URL
            
        Raises:
            ValueError: If URL format is invalid
        """
        if not v:
            raise ValueError("base_url cannot be empty")
        
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("base_url must start with http:// or https://")
        
        # Remove trailing slash for consistency
        return v.rstrip("/")
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key is not empty.
        
        Args:
            v: API key value
            
        Returns:
            API key
            
        Raises:
            ValueError: If API key is empty
        """
        if not v or not v.strip():
            raise ValueError("api_key cannot be empty")
        
        return v.strip()
    
    @field_validator('default_dataset_id')
    @classmethod
    def validate_default_dataset_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate default dataset ID if provided.
        
        Args:
            v: Default dataset ID value
            
        Returns:
            Default dataset ID or None
        """
        if v is not None and not v.strip():
            return None
        
        return v.strip() if v else None
    
    @classmethod
    def from_env(cls) -> "RAGFlowConfig":
        """Load configuration from environment variables.
        
        Returns:
            RAGFlowConfig instance with values from environment
            
        Raises:
            ConfigurationError: If required configuration is missing or invalid
        """
        # Load environment variables from .env file if present
        load_dotenv()
        
        # Get configuration from environment
        config_data = {
            "base_url": os.getenv("RAGFLOW_BASE_URL"),
            "api_key": os.getenv("RAGFLOW_API_KEY"),
            "default_dataset_id": os.getenv("RAGFLOW_DEFAULT_DATASET_ID"),
        }
        
        # Handle optional integer fields with defaults
        try:
            if os.getenv("RAGFLOW_TIMEOUT"):
                config_data["timeout"] = int(os.getenv("RAGFLOW_TIMEOUT"))
        except ValueError as e:
            raise ConfigurationError(f"Invalid RAGFLOW_TIMEOUT value: {e}")
        
        try:
            if os.getenv("RAGFLOW_MAX_RETRIES"):
                config_data["max_retries"] = int(os.getenv("RAGFLOW_MAX_RETRIES"))
        except ValueError as e:
            raise ConfigurationError(f"Invalid RAGFLOW_MAX_RETRIES value: {e}")
        
        # Check required fields
        if not config_data["base_url"]:
            raise ConfigurationError("RAGFLOW_BASE_URL environment variable is required")
        
        if not config_data["api_key"]:
            raise ConfigurationError("RAGFLOW_API_KEY environment variable is required")
        
        try:
            config = cls(**config_data)
            logger.info(f"Configuration loaded: base_url={config.base_url}, timeout={config.timeout}")
            return config
        except PydanticValidationError as e:
            # Convert Pydantic validation errors to ConfigurationError
            error_messages = []
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                message = error["msg"]
                error_messages.append(f"{field}: {message}")
            
            raise ConfigurationError(f"Configuration validation failed: {'; '.join(error_messages)}")
    
    def validate_config(self) -> None:
        """Additional validation method for backward compatibility.
        
        Note: Pydantic automatically validates on instantiation,
        but this method is kept for explicit validation calls.
        
        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            # Pydantic validation happens automatically, but we can trigger it explicitly
            self.__class__(**self.model_dump())
            logger.debug("Configuration validation passed")
        except PydanticValidationError as e:
            error_messages = []
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                message = error["msg"]
                error_messages.append(f"{field}: {message}")
            
            raise ConfigurationError(f"Configuration validation failed: {'; '.join(error_messages)}")