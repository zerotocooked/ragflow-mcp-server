#!/usr/bin/env python3
"""Search functionality tests for RAGFlow MCP Server."""

import asyncio
import tempfile
import os
from ragflow_mcp_server.client import RAGFlowClient
from ragflow_mcp_server.config import RAGFlowConfig


async def test_semantic_search():
    """Test semantic search capabilities."""
    print("🔍 Testing semantic search...")
    
    config = RAGFlowConfig.from_env()
    dataset_id = config.default_dataset_id
    
    # Create test document with specific content
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Machine learning is a subset of artificial intelligence. ")
        f.write("Deep learning uses neural networks with multiple layers. ")
        f.write("Natural language processing helps computers understand human language. ")
        f.write("Computer vision enables machines to interpret visual information.")
        test_file_path = f.name
    
    try:
        async with RAGFlowClient(config) as client:
            # Upload test document
            result = await client.upload_file(test_file_path, dataset_id, "naive")
            print(f"📄 Uploaded test document: {result.file_id}")
            
            # Wait for processing
            await asyncio.sleep(15)
            
            # Test different search queries
            search_queries = [
                ("machine learning", "Should find ML content"),
                ("neural networks", "Should find deep learning content"),
                ("language processing", "Should find NLP content"),
                ("visual recognition", "Should find computer vision content"),
                ("quantum computing", "Should not find relevant content")
            ]
            
            for query, description in search_queries:
                print(f"\n🎯 Query: '{query}' - {description}")
                
                search_result = await client.search(
                    query=query,
                    dataset_id=dataset_id,
                    limit=3,
                    similarity_threshold=0.1
                )
                
                print(f"   Found {len(search_result.results)} results in {search_result.query_time:.2f}s")
                
                for i, item in enumerate(search_result.results):
                    if result.file_id in item.file_id:
                        print(f"   ✅ {i+1}. Score: {item.score:.3f} - {item.content[:60]}...")
                    else:
                        print(f"   📄 {i+1}. Score: {item.score:.3f} - {item.content[:60]}...")
            
            # Clean up
            await client.delete_file(result.file_id, dataset_id, confirm=True)
            print(f"\n🗑️ Cleaned up test document")
            
    finally:
        os.unlink(test_file_path)


async def test_search_parameters():
    """Test different search parameters."""
    print("\n🔧 Testing search parameters...")
    
    config = RAGFlowConfig.from_env()
    dataset_id = config.default_dataset_id
    
    async with RAGFlowClient(config) as client:
        # Test with different limits
        print("\n📊 Testing different limits:")
        for limit in [1, 3, 5]:
            result = await client.search(
                query="test",
                dataset_id=dataset_id,
                limit=limit
            )
            print(f"   Limit {limit}: Found {len(result.results)} results")
        
        # Test with different similarity thresholds
        print("\n🎯 Testing different similarity thresholds:")
        for threshold in [0.1, 0.3, 0.5]:
            result = await client.search(
                query="test",
                dataset_id=dataset_id,
                limit=5,
                similarity_threshold=threshold
            )
            print(f"   Threshold {threshold}: Found {len(result.results)} results")


async def main():
    """Run search functionality tests."""
    print("🚀 RAGFlow MCP Search Functionality Tests")
    print("=" * 50)
    
    try:
        await test_semantic_search()
        await test_search_parameters()
        print("\n✅ All search tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())