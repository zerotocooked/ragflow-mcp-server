# Contributing to RAGFlow MCP Server

Thank you for your interest in contributing to the RAGFlow MCP Server! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a code of conduct that we expect all contributors to follow. Please be respectful and constructive in all interactions.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- A RAGFlow instance for testing (local or remote)

### Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/your-username/ragflow-mcp-server.git
   cd ragflow-mcp-server
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

5. **Set up environment variables**:
   ```bash
   cp examples/.env.example .env
   # Edit .env with your RAGFlow configuration
   ```

6. **Verify the setup**:
   ```bash
   make test
   ```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-new-tool` - for new features
- `fix/authentication-error` - for bug fixes
- `docs/update-readme` - for documentation updates
- `refactor/client-structure` - for refactoring

### Commit Messages

Follow conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: new feature
- `fix`: bug fix
- `docs`: documentation changes
- `style`: formatting changes
- `refactor`: code refactoring
- `test`: adding or updating tests
- `chore`: maintenance tasks

Examples:
```
feat(client): add support for batch file upload
fix(server): handle connection timeout errors properly
docs(readme): update installation instructions
```

### Code Organization

```
ragflow_mcp_server/
├── __init__.py          # Package exports and metadata
├── __main__.py          # CLI entry point
├── server.py            # MCP server implementation
├── client.py            # RAGFlow API client
├── config.py            # Configuration management
├── errors.py            # Custom exceptions
└── models.py            # Pydantic data models
```

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run specific test categories
make test-unit
make test-integration

# Run with coverage
make test-cov
```

### Writing Tests

#### Unit Tests
- Test individual functions and methods
- Mock external dependencies
- Focus on edge cases and error conditions

```python
# tests/unit/test_client.py
import pytest
from unittest.mock import AsyncMock, patch
from ragflow_mcp_server.client import RAGFlowClient

@pytest.mark.asyncio
async def test_upload_file_success(mock_config):
    client = RAGFlowClient(mock_config)
    with patch.object(client, '_make_request') as mock_request:
        mock_request.return_value = {"file_id": "123", "status": "success"}
        result = await client.upload_file("test.txt", "dataset_id")
        assert result.file_id == "123"
```

#### Integration Tests
- Test complete workflows
- Use real or mock RAGFlow API
- Test MCP protocol compliance

```python
# tests/integration/test_workflows.py
@pytest.mark.asyncio
async def test_upload_search_workflow(ragflow_client, test_dataset_id):
    # Upload a file
    upload_result = await ragflow_client.upload_file("test.txt", test_dataset_id)
    assert upload_result.status == "success"
    
    # Search for content
    search_result = await ragflow_client.search("test content", test_dataset_id)
    assert len(search_result.results) > 0
```

### Test Configuration

Set up test environment variables:
```bash
# For integration tests
export RAGFLOW_TEST_BASE_URL=http://localhost:9380
export RAGFLOW_TEST_API_KEY=test_api_key
export RAGFLOW_TEST_DATASET_ID=test_dataset
```

## Code Style

### Formatting

We use several tools to maintain code quality:

```bash
# Format code
make format

# Check linting
make lint

# Type checking
make type-check

# Run all quality checks
make check
```

### Style Guidelines

#### Python Code Style
- Follow PEP 8
- Use type hints for all function parameters and return values
- Write docstrings for all public functions and classes
- Keep line length under 88 characters (Black default)

#### Documentation Style
- Use Google-style docstrings
- Include parameter types and descriptions
- Document exceptions that may be raised

```python
async def upload_file(
    self, 
    file_path: str, 
    dataset_id: str,
    chunk_method: str = "naive"
) -> UploadResult:
    """Upload a file to RAGFlow and trigger embedding.
    
    Args:
        file_path: Path to the file to upload
        dataset_id: Target dataset identifier
        chunk_method: Method for chunking the document
        
    Returns:
        UploadResult containing file ID and status
        
    Raises:
        FileError: If file cannot be read or is invalid
        APIError: If RAGFlow API request fails
        ValidationError: If parameters are invalid
    """
```

#### Error Handling
- Use specific exception types
- Provide helpful error messages
- Sanitize sensitive information in error messages

```python
try:
    result = await self._make_request("POST", "/upload", data=form_data)
except aiohttp.ClientError as e:
    raise APIError(f"Failed to upload file: {e}")
```

## Submitting Changes

### Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Write code following the style guidelines
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**:
   ```bash
   make check
   make test
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a pull request**:
   - Use a descriptive title
   - Explain what changes you made and why
   - Reference any related issues
   - Include screenshots if applicable

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

## Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- Major: Breaking changes
- Minor: New features (backward compatible)
- Patch: Bug fixes (backward compatible)

### Release Steps

1. **Update version numbers**:
   - `ragflow_mcp_server/__init__.py`
   - `pyproject.toml`

2. **Update CHANGELOG.md**:
   - Add new version section
   - List all changes since last release

3. **Create release commit**:
   ```bash
   git commit -m "chore: release v0.2.0"
   ```

4. **Create and push tag**:
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

5. **Build and upload to PyPI**:
   ```bash
   make build
   make upload
   ```

## Development Tips

### Debugging

Enable debug logging:
```bash
export RAGFLOW_LOG_LEVEL=DEBUG
python -m ragflow_mcp_server
```

### Testing with Cursor

1. Install your development version:
   ```bash
   pip install -e .
   ```

2. Update Cursor MCP configuration to use local installation

3. Restart Cursor and test your changes

### Common Issues

#### Import Errors
Make sure you're in the virtual environment and have installed the package in development mode.

#### Test Failures
Check that RAGFlow is running and accessible for integration tests.

#### Type Checking Errors
Run `mypy ragflow_mcp_server/` to check for type issues.

## Getting Help

- **Questions**: Open a discussion on GitHub
- **Bugs**: Create an issue with reproduction steps
- **Features**: Open an issue to discuss before implementing
- **Documentation**: Check existing docs or ask for clarification

## Recognition

Contributors will be recognized in:
- CHANGELOG.md for their contributions
- GitHub contributors list
- Release notes for significant contributions

Thank you for contributing to RAGFlow MCP Server!