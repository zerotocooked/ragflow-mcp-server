# Installation Guide

This guide provides detailed installation instructions for the RAGFlow MCP Server.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- A running RAGFlow instance (local or remote)
- Cursor IDE with MCP support

## Installation Methods

### Method 1: Install from PyPI (Recommended)

```bash
pip install ragflow-mcp-server
```

### Method 2: Install from Source

```bash
# Clone the repository
git clone https://github.com/your-username/ragflow-mcp-server.git
cd ragflow-mcp-server

# Install the package
pip install .
```

### Method 3: Development Installation

For development or contributing to the project:

```bash
# Clone the repository
git clone https://github.com/your-username/ragflow-mcp-server.git
cd ragflow-mcp-server

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

## RAGFlow Setup

### Option 1: Local RAGFlow Installation

1. **Install Docker and Docker Compose**
   ```bash
   # On Ubuntu/Debian
   sudo apt update
   sudo apt install docker.io docker-compose
   
   # On macOS (with Homebrew)
   brew install docker docker-compose
   
   # On Windows, install Docker Desktop
   ```

2. **Clone and Start RAGFlow**
   ```bash
   git clone https://github.com/infiniflow/ragflow.git
   cd ragflow
   docker-compose up -d
   ```

3. **Access RAGFlow Web Interface**
   - Open http://localhost:9380 in your browser
   - Create an account and log in
   - Generate an API key in Settings → API Keys

### Option 2: Remote RAGFlow Instance

If you have access to a remote RAGFlow instance:

1. Get the base URL (e.g., `https://your-ragflow-instance.com`)
2. Obtain an API key from the RAGFlow administrator
3. Ensure the instance is accessible from your development machine

## Configuration

### Environment Variables

Create a `.env` file in your project directory or set environment variables:

```bash
# Required
RAGFLOW_BASE_URL=http://localhost:9380
RAGFLOW_API_KEY=your_api_key_here

# Optional
RAGFLOW_DEFAULT_DATASET_ID=your_default_dataset_id
RAGFLOW_TIMEOUT=30
RAGFLOW_MAX_RETRIES=3
RAGFLOW_LOG_LEVEL=INFO
```

### Cursor IDE Configuration

1. **Locate your Cursor MCP settings file**:
   - **macOS**: `~/Library/Application Support/Cursor/User/globalStorage/mcp.json`
   - **Windows**: `%APPDATA%\Cursor\User\globalStorage\mcp.json`
   - **Linux**: `~/.config/Cursor/User/globalStorage/mcp.json`

2. **Add the RAGFlow MCP server configuration**:
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

3. **Restart Cursor IDE** to load the new configuration

## Verification

### Test the Installation

1. **Check if the package is installed**:
   ```bash
   python -c "import ragflow_mcp_server; print('Installation successful')"
   ```

2. **Test the command-line interface**:
   ```bash
   ragflow-mcp-server --help
   ```

3. **Run the server manually**:
   ```bash
   python -m ragflow_mcp_server
   ```

### Test with Example Usage

1. **Copy the example configuration**:
   ```bash
   cp examples/.env.example .env
   # Edit .env with your actual values
   ```

2. **Run the usage examples**:
   ```bash
   python examples/usage_examples.py
   ```

### Test MCP Integration

1. **Open Cursor IDE**
2. **Check if the RAGFlow tools are available** in the MCP tools panel
3. **Try a simple operation** like listing datasets:
   ```
   Use the ragflow_get_datasets tool to see available datasets
   ```

## Troubleshooting

### Common Installation Issues

#### Python Version Compatibility
```bash
# Check Python version
python --version

# If using Python 3.8+, you should be fine
# For older versions, consider upgrading
```

#### Permission Issues
```bash
# On Unix systems, you might need to use --user
pip install --user ragflow-mcp-server

# Or use a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install ragflow-mcp-server
```

#### Dependency Conflicts
```bash
# Create a clean virtual environment
python -m venv ragflow-env
source ragflow-env/bin/activate  # On Windows: ragflow-env\Scripts\activate
pip install ragflow-mcp-server
```

### RAGFlow Connection Issues

#### Cannot Connect to RAGFlow
1. **Check if RAGFlow is running**:
   ```bash
   curl http://localhost:9380/health
   ```

2. **Check Docker containers** (if using Docker):
   ```bash
   docker ps
   docker logs ragflow
   ```

3. **Verify network connectivity**:
   ```bash
   ping localhost
   telnet localhost 9380
   ```

#### Authentication Errors
1. **Verify API key** in RAGFlow web interface
2. **Check environment variables**:
   ```bash
   echo $RAGFLOW_API_KEY
   ```
3. **Test API key manually**:
   ```bash
   curl -H "Authorization: Bearer your_api_key" http://localhost:9380/api/datasets
   ```

### Cursor IDE Integration Issues

#### MCP Server Not Loading
1. **Check Cursor logs** for error messages
2. **Verify MCP configuration syntax** (valid JSON)
3. **Test server manually**:
   ```bash
   python -m ragflow_mcp_server
   ```

#### Tools Not Appearing
1. **Restart Cursor IDE** after configuration changes
2. **Check environment variables** in MCP configuration
3. **Verify server is responding**:
   ```bash
   # Test with debug logging
   RAGFLOW_LOG_LEVEL=DEBUG python -m ragflow_mcp_server
   ```

## Development Setup

For contributors and developers:

### 1. Clone and Setup
```bash
git clone https://github.com/your-username/ragflow-mcp-server.git
cd ragflow-mcp-server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### 2. Install Pre-commit Hooks
```bash
pre-commit install
```

### 3. Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ragflow_mcp_server

# Run specific test types
pytest tests/unit/
pytest tests/integration/
```

### 4. Code Quality Checks
```bash
# Format code
black ragflow_mcp_server/
isort ragflow_mcp_server/

# Type checking
mypy ragflow_mcp_server/

# Linting
flake8 ragflow_mcp_server/
```

## Uninstallation

To remove the RAGFlow MCP Server:

```bash
pip uninstall ragflow-mcp-server
```

Don't forget to remove the MCP configuration from Cursor IDE if you no longer need it.

## Getting Help

- **Documentation**: Check the [README.md](README.md) for usage instructions
- **Examples**: Look at the [examples/](examples/) directory for configuration examples
- **Issues**: Report bugs or request features on [GitHub Issues](https://github.com/your-username/ragflow-mcp-server/issues)
- **RAGFlow Documentation**: Visit [RAGFlow Docs](https://ragflow.io/docs) for RAGFlow-specific questions