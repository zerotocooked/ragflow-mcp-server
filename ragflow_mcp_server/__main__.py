"""Main entry point for RAGFlow MCP Server."""

import argparse
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from .server import RAGFlowMCPServer
from .config import RAGFlowConfig
from .errors import ConfigurationError


logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Set up logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path. If None, logs to stderr only.
    """
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Add stderr handler
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    root_logger.addHandler(stderr_handler)
    
    # Add file handler if specified
    if log_file:
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            logger.info(f"Logging to file: {log_file}")
        except Exception as e:
            logger.warning(f"Failed to set up file logging: {e}")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="RAGFlow MCP Server - Model Context Protocol server for RAGFlow integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  RAGFLOW_BASE_URL        RAGFlow API base URL (default: http://localhost:9380)
  RAGFLOW_API_KEY         RAGFlow API key (required)
  RAGFLOW_DEFAULT_DATASET_ID  Default dataset ID (optional)
  RAGFLOW_TIMEOUT         Request timeout in seconds (default: 30)
  RAGFLOW_MAX_RETRIES     Maximum retry attempts (default: 3)

Examples:
  python -m ragflow_mcp_server
  python -m ragflow_mcp_server --log-level DEBUG
  python -m ragflow_mcp_server --log-file /var/log/ragflow-mcp.log
  python -m ragflow_mcp_server --base-url http://ragflow.example.com:9380
        """
    )
    
    # Configuration options
    parser.add_argument(
        "--base-url",
        type=str,
        help="RAGFlow API base URL (overrides RAGFLOW_BASE_URL)"
    )
    
    parser.add_argument(
        "--api-key",
        type=str,
        help="RAGFlow API key (overrides RAGFLOW_API_KEY)"
    )
    
    parser.add_argument(
        "--default-dataset-id",
        type=str,
        help="Default dataset ID (overrides RAGFLOW_DEFAULT_DATASET_ID)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        help="Request timeout in seconds (overrides RAGFLOW_TIMEOUT)"
    )
    
    parser.add_argument(
        "--max-retries",
        type=int,
        help="Maximum retry attempts (overrides RAGFLOW_MAX_RETRIES)"
    )
    
    # Logging options
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--log-file",
        type=str,
        help="Log file path (logs to stderr if not specified)"
    )
    
    # Server options
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration and exit"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="RAGFlow MCP Server 0.1.0"
    )
    
    return parser.parse_args()


def create_config_from_args(args: argparse.Namespace) -> RAGFlowConfig:
    """Create configuration from command line arguments and environment.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        RAGFlow configuration object
        
    Raises:
        ConfigurationError: If configuration is invalid
    """
    try:
        # Try to load from environment first, but allow fallback to command line args
        config_data = {}
        
        # Load from environment if available
        from dotenv import load_dotenv
        load_dotenv()
        
        # Get base configuration from environment or command line
        config_data["base_url"] = args.base_url or os.getenv("RAGFLOW_BASE_URL")
        config_data["api_key"] = args.api_key or os.getenv("RAGFLOW_API_KEY")
        config_data["default_dataset_id"] = args.default_dataset_id or os.getenv("RAGFLOW_DEFAULT_DATASET_ID")
        
        # Handle timeout
        if args.timeout:
            config_data["timeout"] = args.timeout
        elif os.getenv("RAGFLOW_TIMEOUT"):
            try:
                config_data["timeout"] = int(os.getenv("RAGFLOW_TIMEOUT"))
            except ValueError as e:
                raise ConfigurationError(f"Invalid RAGFLOW_TIMEOUT value: {e}")
        else:
            config_data["timeout"] = 30  # Default value
        
        # Handle max_retries
        if args.max_retries:
            config_data["max_retries"] = args.max_retries
        elif os.getenv("RAGFLOW_MAX_RETRIES"):
            try:
                config_data["max_retries"] = int(os.getenv("RAGFLOW_MAX_RETRIES"))
            except ValueError as e:
                raise ConfigurationError(f"Invalid RAGFLOW_MAX_RETRIES value: {e}")
        else:
            config_data["max_retries"] = 3  # Default value
        
        # Check required fields
        if not config_data["base_url"]:
            raise ConfigurationError("RAGFlow base URL is required (set RAGFLOW_BASE_URL or use --base-url)")
        
        if not config_data["api_key"]:
            raise ConfigurationError("RAGFlow API key is required (set RAGFLOW_API_KEY or use --api-key)")
        
        # Create config object
        config = RAGFlowConfig(**config_data)
        logger.info(f"Configuration loaded: base_url={config.base_url}, timeout={config.timeout}")
        return config
        
    except Exception as e:
        if isinstance(e, ConfigurationError):
            raise
        raise ConfigurationError(f"Failed to create configuration: {e}")


async def validate_config(config: RAGFlowConfig) -> None:
    """Validate configuration by testing connection to RAGFlow.
    
    Args:
        config: RAGFlow configuration to validate
        
    Raises:
        ConfigurationError: If configuration is invalid
    """
    from .client import RAGFlowClient
    
    logger.info("Validating configuration...")
    
    client = None
    try:
        client = RAGFlowClient(config)
        await client.get_datasets()
        logger.info("✓ Configuration is valid - successfully connected to RAGFlow")
        
    except Exception as e:
        logger.error(f"✗ Configuration validation failed: {e}")
        raise ConfigurationError(f"Cannot connect to RAGFlow API: {e}")
    finally:
        if client:
            await client.close()


class ServerManager:
    """Manages server lifecycle and graceful shutdown."""
    
    def __init__(self, server: RAGFlowMCPServer):
        self.server = server
        self.shutdown_event = asyncio.Event()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        if sys.platform != "win32":
            # Unix-like systems
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, self._signal_handler)
        else:
            # Windows
            signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_event.set()
    
    async def run(self) -> None:
        """Run the server with graceful shutdown handling."""
        logger.info("Starting RAGFlow MCP Server...")
        
        try:
            # Just run the server directly without complex task management
            await self.server.run()
            logger.info("RAGFlow MCP Server stopped")
            
        except asyncio.CancelledError:
            logger.info("Server shutdown cancelled")
            raise
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise


async def main() -> None:
    """Main entry point for the MCP server."""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Set up logging
        setup_logging(args.log_level, args.log_file)
        
        logger.info("RAGFlow MCP Server starting up...")
        logger.debug(f"Arguments: {vars(args)}")
        
        # Create configuration
        config = create_config_from_args(args)
        logger.info(f"Configuration loaded - Base URL: {config.base_url}")
        
        # Validate configuration if requested
        if args.validate_config:
            await validate_config(config)
            logger.info("Configuration validation completed successfully")
            return
        
        # Create and start server
        async with RAGFlowMCPServer(config) as server:
            server_manager = ServerManager(server)
            await server_manager.run()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start RAGFlow MCP Server: {e}")
        logger.debug("Exception details:", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())