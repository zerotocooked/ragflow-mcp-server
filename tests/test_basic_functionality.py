#!/usr/bin/env python3
"""Basic functionality tests for RAGFlow MCP Server."""

import asyncio
import tempfile
import os
from ragflow_mcp_server.client import RAGFlowClient
from ragflow_mcp_server.config import RAGFlowConfig


async def test_connectivity():
    """Test basic connectivity to RAGFlow server."""
    print("📡 Testing connectivity...")
    
    config = RAGFlowConfig.from_env()
    
    async with RAGFlowClient(config) as client:
        datasets = await client.get_datasets()
        print(f"✅ Connected! Found {len(datasets.datasets)} datasets")
        
        if datasets.datasets:
            dataset = datasets.datasets[0]
            print(f"📁 Sample dataset: {dataset.name} ({dataset.dataset_id})")
        
        return datasets.datasets[0].dataset_id if datasets.datasets else None


async def test_upload():
    """Test file upload functionality."""
    print("\n📤 Testing file upload...")
    
    config = RAGFlowConfig.from_env()
    dataset_id = config.default_dataset_id or await test_connectivity()
    
    # Create test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a basic test document for upload testing.")
        test_file_path = f.name
    
    try:
        async with RAGFlowClient(config) as client:
            result = await client.upload_file(
                file_path=test_file_path,
                dataset_id=dataset_id,
                chunk_method="naive"
            )
            
            print(f"✅ Upload successful: {result.file_id}")
            print(f"💬 Message: {result.message}")
            
            return result.file_id
            
    finally:
        os.unlink(test_file_path)


async def test_list_files():
    """Test list files functionality."""
    print("\n📋 Testing list files...")
    
    config = RAGFlowConfig.from_env()
    dataset_id = config.default_dataset_id
    
    async with RAGFlowClient(config) as client:
        files_result = await client.list_files(dataset_id, limit=5)
        print(f"📂 Found {len(files_result.files)} files")
        
        for i, file_info in enumerate(files_result.files[:3]):
            print(f"  {i+1}. {file_info.name} - {file_info.status}")


async def test_search():
    """Test search functionality."""
    print("\n🔍 Testing search...")
    
    config = RAGFlowConfig.from_env()
    dataset_id = config.default_dataset_id
    
    async with RAGFlowClient(config) as client:
        result = await client.search(
            query="test document",
            dataset_id=dataset_id,
            limit=3
        )
        
        print(f"🎯 Found {len(result.results)} results")
        for i, item in enumerate(result.results):
            print(f"  {i+1}. Score: {item.score:.3f} - {item.content[:50]}...")


async def main():
    """Run basic functionality tests."""
    print("🚀 RAGFlow MCP Basic Functionality Tests")
    print("=" * 50)
    
    try:
        dataset_id = await test_connectivity()
        if dataset_id:
            file_id = await test_upload()
            await asyncio.sleep(5)  # Wait for processing
            await test_list_files()
            await test_search()
            print("\n✅ All basic tests passed!")
        else:
            print("❌ No datasets available for testing")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())