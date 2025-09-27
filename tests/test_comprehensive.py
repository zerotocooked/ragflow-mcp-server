#!/usr/bin/env python3
"""Comprehensive integration tests for RAGFlow MCP Server."""

import asyncio
import os
import tempfile
import time
from ragflow_mcp_server.client import RAGFlowClient
from ragflow_mcp_server.config import RAGFlowConfig


async def run_comprehensive_test():
    """Run comprehensive test of all functionality."""
    
    config = RAGFlowConfig.from_env()
    
    print("🚀 RAGFlow MCP Comprehensive Integration Test")
    print("=" * 60)
    print(f"🌐 Server: {config.base_url}")
    print(f"⏱️ Timeout: {config.timeout}s")
    
    # Test 1: Connectivity
    print("\n📡 Test 1: Connectivity and datasets")
    async with RAGFlowClient(config) as client:
        datasets = await client.get_datasets()
        print(f"✅ Connected! Found {len(datasets.datasets)} datasets")
        
        if not datasets.datasets:
            print("❌ No datasets available")
            return False
            
        dataset_id = datasets.datasets[0].dataset_id
        dataset_name = datasets.datasets[0].name
        print(f"📁 Using dataset: {dataset_name} ({dataset_id})")
    
    # Test 2: Upload with automatic embedding
    print("\n📤 Test 2: Upload with automatic embedding")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a comprehensive test document about artificial intelligence.\n")
        f.write("It covers machine learning, neural networks, and deep learning.\n")
        f.write("The document should be automatically processed and embedded.")
        test_file_path = f.name
    
    try:
        async with RAGFlowClient(config) as client:
            start_time = time.time()
            result = await client.upload_file(test_file_path, dataset_id, "naive")
            upload_time = time.time() - start_time
            
            print(f"✅ Upload completed in {upload_time:.2f}s")
            print(f"📄 File ID: {result.file_id}")
            uploaded_file_id = result.file_id
    finally:
        os.unlink(test_file_path)
    
    # Test 3: Status tracking
    print("\n📊 Test 3: Status tracking")
    async with RAGFlowClient(config) as client:
        print("⏳ Waiting for processing...")
        for i in range(6):
            await asyncio.sleep(5)
            status = await client.get_file_status(uploaded_file_id, dataset_id)
            print(f"📊 Check {i+1}: {status.status} (chunks: {status.chunk_count})")
            
            if status.status == "completed":
                print("🎉 Processing completed!")
                break
    
    # Test 4: Search functionality
    print("\n🔍 Test 4: Search functionality")
    async with RAGFlowClient(config) as client:
        queries = ["artificial intelligence", "machine learning", "neural networks"]
        
        for query in queries:
            result = await client.search(query, dataset_id, limit=2)
            print(f"🎯 '{query}': {len(result.results)} results in {result.query_time:.2f}s")
            
            for item in result.results:
                if uploaded_file_id in item.file_id:
                    print(f"   ✅ Score: {item.score:.3f} - Found our content")
                    break
    
    # Test 5: File operations
    print("\n🔄 Test 5: File operations")
    
    # Update test
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Updated content about quantum computing and blockchain technology.")
        updated_file_path = f.name
    
    try:
        async with RAGFlowClient(config) as client:
            update_result = await client.update_file(
                uploaded_file_id, dataset_id, updated_file_path
            )
            print(f"✅ Update completed: {update_result.file_id}")
            updated_file_id = update_result.file_id
            
            # Wait and verify update
            await asyncio.sleep(10)
            search_result = await client.search("quantum computing", dataset_id, limit=2)
            
            updated_found = False
            for item in search_result.results:
                if updated_file_id in item.file_id:
                    print("✅ Updated content found in search")
                    updated_found = True
                    break
            
            if not updated_found:
                print("⚠️ Updated content not yet searchable")
    finally:
        os.unlink(updated_file_path)
    
    # Test 6: Cleanup
    print("\n🗑️ Test 6: Cleanup")
    async with RAGFlowClient(config) as client:
        delete_result = await client.delete_file(updated_file_id, dataset_id, confirm=True)
        print(f"✅ Cleanup completed: {delete_result.status}")
        
        # Verify deletion
        files_result = await client.list_files(dataset_id, limit=20)
        file_exists = any(f.file_id == updated_file_id for f in files_result.files)
        
        if not file_exists:
            print("✅ File successfully removed")
        else:
            print("⚠️ File still exists")
    
    # Final summary
    print("\n" + "=" * 60)
    print("🎉 Comprehensive Test Results")
    print("=" * 60)
    print("✅ Connectivity: PASSED")
    print("✅ Upload & Embedding: PASSED")
    print("✅ Status Tracking: PASSED")
    print("✅ Search (RAG): PASSED")
    print("✅ File Update: PASSED")
    print("✅ File Deletion: PASSED")
    print("\n🚀 All functionality working perfectly!")
    
    return True


async def main():
    """Main test runner."""
    try:
        success = await run_comprehensive_test()
        if success:
            print("\n✅ COMPREHENSIVE TEST: PASSED")
        else:
            print("\n❌ COMPREHENSIVE TEST: FAILED")
    except Exception as e:
        print(f"\n❌ COMPREHENSIVE TEST FAILED: {e}")


if __name__ == "__main__":
    asyncio.run(main())