#!/usr/bin/env python3
"""
Usage examples for RAGFlow MCP Server.

This file demonstrates how to use the RAGFlow MCP Server programmatically
and provides examples of common workflows.
"""

import asyncio
import os
from pathlib import Path

from ragflow_mcp_server.config import RAGFlowConfig
from ragflow_mcp_server.client import RAGFlowClient


async def basic_workflow_example():
    """Demonstrate a basic workflow with RAGFlow."""
    
    # Load configuration from environment
    config = RAGFlowConfig.from_env()
    
    # Create client
    async with RAGFlowClient(config) as client:
        
        # 1. Get available datasets
        print("Getting available datasets...")
        datasets = await client.get_datasets()
        print(f"Available datasets: {[d.name for d in datasets.datasets]}")
        
        if not datasets.datasets:
            print("No datasets available. Please create a dataset in RAGFlow first.")
            return
        
        dataset_id = datasets.datasets[0].id
        print(f"Using dataset: {dataset_id}")
        
        # 2. Upload a file (example)
        sample_file = Path("examples/sample_document.txt")
        if sample_file.exists():
            print(f"Uploading file: {sample_file}")
            upload_result = await client.upload_file(
                file_path=str(sample_file),
                dataset_id=dataset_id,
                chunk_method="naive"
            )
            print(f"Upload result: {upload_result.status}")
            file_id = upload_result.file_id
        else:
            print("Sample file not found, skipping upload example")
            return
        
        # 3. Wait for processing (in real usage, you might poll status)
        print("Waiting for file processing...")
        await asyncio.sleep(5)
        
        # 4. Search for content
        print("Searching for content...")
        search_result = await client.search(
            query="example content",
            dataset_id=dataset_id,
            limit=5
        )
        print(f"Found {len(search_result.results)} results")
        for result in search_result.results:
            print(f"  - Score: {result.score:.3f}, Content: {result.content[:100]}...")
        
        # 5. List files
        print("Listing files in dataset...")
        files_result = await client.list_files(dataset_id)
        print(f"Files in dataset: {len(files_result.files)}")
        for file_info in files_result.files:
            print(f"  - {file_info.name} (ID: {file_info.id})")
        
        # 6. Update file (example)
        if sample_file.exists():
            print(f"Updating file: {file_id}")
            update_result = await client.update_file(
                file_id=file_id,
                file_path=str(sample_file)
            )
            print(f"Update result: {update_result.status}")
        
        # 7. Clean up - delete the uploaded file
        print(f"Cleaning up - deleting file: {file_id}")
        delete_result = await client.delete_file(file_id)
        print(f"Delete result: {delete_result.status}")


async def search_only_example():
    """Example of using RAGFlow for search only."""
    
    config = RAGFlowConfig.from_env()
    
    async with RAGFlowClient(config) as client:
        # Get datasets
        datasets = await client.get_datasets()
        if not datasets.datasets:
            print("No datasets available")
            return
        
        dataset_id = datasets.datasets[0].id
        
        # Perform multiple searches
        queries = [
            "machine learning algorithms",
            "data preprocessing techniques",
            "model evaluation metrics"
        ]
        
        for query in queries:
            print(f"\nSearching for: '{query}'")
            results = await client.search(
                query=query,
                dataset_id=dataset_id,
                limit=3,
                similarity_threshold=0.2
            )
            
            if results.results:
                for i, result in enumerate(results.results, 1):
                    print(f"  {i}. Score: {result.score:.3f}")
                    print(f"     File: {result.file_name}")
                    print(f"     Content: {result.content[:150]}...")
            else:
                print("  No results found")


async def file_management_example():
    """Example of file management operations."""
    
    config = RAGFlowConfig.from_env()
    
    async with RAGFlowClient(config) as client:
        # Get datasets
        datasets = await client.get_datasets()
        if not datasets.datasets:
            print("No datasets available")
            return
        
        dataset_id = datasets.datasets[0].id
        print(f"Working with dataset: {dataset_id}")
        
        # List current files
        print("\nCurrent files:")
        files_result = await client.list_files(dataset_id)
        for file_info in files_result.files:
            print(f"  - {file_info.name} (ID: {file_info.id}, Size: {file_info.size} bytes)")
        
        # Check file status (if files exist)
        if files_result.files:
            file_id = files_result.files[0].id
            print(f"\nChecking status of file: {file_id}")
            status = await client.get_file_status(file_id)
            print(f"  Status: {status.status}")
            print(f"  Progress: {status.progress}%")


def create_sample_document():
    """Create a sample document for testing."""
    sample_content = """
# Sample Document for RAGFlow Testing

This is a sample document that can be used to test the RAGFlow MCP Server.

## Machine Learning Concepts

Machine learning is a subset of artificial intelligence that focuses on algorithms
that can learn and make decisions from data without being explicitly programmed.

### Key Algorithms

1. **Linear Regression**: Used for predicting continuous values
2. **Decision Trees**: Good for classification and regression tasks
3. **Neural Networks**: Powerful for complex pattern recognition

## Data Preprocessing

Data preprocessing is crucial for machine learning success:

- **Data Cleaning**: Remove or handle missing values
- **Feature Scaling**: Normalize data ranges
- **Feature Selection**: Choose relevant features

## Model Evaluation

Common metrics for evaluating models:

- **Accuracy**: Percentage of correct predictions
- **Precision**: True positives / (True positives + False positives)
- **Recall**: True positives / (True positives + False negatives)
- **F1-Score**: Harmonic mean of precision and recall

This document provides basic examples that can be searched and retrieved
using the RAGFlow semantic search capabilities.
"""
    
    sample_file = Path("examples/sample_document.txt")
    sample_file.parent.mkdir(exist_ok=True)
    sample_file.write_text(sample_content.strip())
    print(f"Created sample document: {sample_file}")


if __name__ == "__main__":
    # Create sample document
    create_sample_document()
    
    # Run examples
    print("=== Basic Workflow Example ===")
    asyncio.run(basic_workflow_example())
    
    print("\n=== Search Only Example ===")
    asyncio.run(search_only_example())
    
    print("\n=== File Management Example ===")
    asyncio.run(file_management_example())