# Dockerfile for RAGFlow MCP Server
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml .
COPY README.md .
COPY LICENSE .

# Install Python dependencies
RUN pip install --no-cache-dir .

# Copy source code
COPY ragflow_mcp_server/ ./ragflow_mcp_server/

# Create non-root user
RUN useradd --create-home --shell /bin/bash ragflow
USER ragflow

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port (if needed for HTTP interface)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import ragflow_mcp_server; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "ragflow_mcp_server"]