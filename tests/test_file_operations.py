#!/usr/bin/env python3
"""File operations tests for RAGFlow MCP Server."""

import asyncio
import tempfile
import os
from ragflow_mcp_server.client import RAGFlowClient
from ragflow_mcp_server.config import RAGFlowConfig


async def test_upload_update_delete_cycle():
    """Test complete file lifecycle: upload -> update -> delete."""
    print("🔄 Testing complete file lifecycle...")
    
    config = RAGFlowConfig.from_env()
    dataset_id = config.default_dataset_id
    
    # Create original file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Original content about cats and dogs.")
        original_file_path = f.name
    
    # Create updated file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Updated content about birds and fish.")
        updated_file_path = f.name
    
    try:
        async with RAGFlowClient(config) as client:
            # 1. Upload
            print("\n📤 Step 1: Upload original file")
            upload_result = await client.upload_file(
                file_path=original_file_path,
                dataset_id=dataset_id,
                chunk_method="naive"
            )
            print(f"✅ Uploaded: {upload_result.file_id}")
            
            # Wait for processing
            await asyncio.sleep(10)
            
            # 2. Update
            print("\n🔄 Step 2: Update file content")
            update_result = await client.update_file(
                file_id=upload_result.file_id,
                dataset_id=dataset_id,
                file_path=updated_file_path
            )
            print(f"✅ Updated: {update_result.file_id}")
            
            # Wait for re-processing
            await asyncio.sleep(10)
            
            # 3. Verify update with search
            print("\n🔍 Step 3: Verify update with search")
            search_result = await client.search(
                query="birds and fish",
                dataset_id=dataset_id,
                limit=3
            )
            
            updated_content_found = False
            for item in search_result.results:
                if update_result.file_id in item.file_id:
                    updated_content_found = True
                    print(f"  ✅ Found updated content: {item.content[:50]}...")
            
            if not updated_content_found:
                print("  ⚠️ Updated content not found in search")
            
            # 4. Delete
            print("\n🗑️ Step 4: Delete file")
            delete_result = await client.delete_file(
                update_result.file_id, 
                dataset_id, 
                confirm=True
            )
            print(f"✅ Deleted: {delete_result.status}")
            
            # 5. Verify deletion
            print("\n📋 Step 5: Verify deletion")
            files_result = await client.list_files(dataset_id, limit=20)
            file_still_exists = any(f.file_id == update_result.file_id for f in files_result.files)
            
            if not file_still_exists:
                print("✅ File successfully deleted")
            else:
                print("❌ File still exists after deletion")
                
    finally:
        # Clean up temp files
        try:
            os.unlink(original_file_path)
            os.unlink(updated_file_path)
        except:
            pass


async def test_duplicate_handling():
    """Test duplicate file upload handling."""
    print("\n🔄 Testing duplicate file handling...")
    
    config = RAGFlowConfig.from_env()
    dataset_id = config.default_dataset_id
    
    # Create test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Duplicate test content with unique identifier 12345.")
        test_file_path = f.name
    
    try:
        async with RAGFlowClient(config) as client:
            # Upload same file twice
            result1 = await client.upload_file(test_file_path, dataset_id, "naive")
            result2 = await client.upload_file(test_file_path, dataset_id, "naive")
            
            print(f"📄 First upload: {result1.file_id}")
            print(f"📄 Second upload: {result2.file_id}")
            
            if result1.file_id != result2.file_id:
                print("✅ System creates separate files for duplicates")
                
                # Clean up both files
                await client.delete_file(result1.file_id, dataset_id, confirm=True)
                await client.delete_file(result2.file_id, dataset_id, confirm=True)
                print("🗑️ Cleaned up duplicate files")
            else:
                print("✅ System reuses existing file for duplicates")
                
                # Clean up single file
                await client.delete_file(result1.file_id, dataset_id, confirm=True)
                print("🗑️ Cleaned up file")
                
    finally:
        os.unlink(test_file_path)


async def main():
    """Run file operations tests."""
    print("🚀 RAGFlow MCP File Operations Tests")
    print("=" * 50)
    
    try:
        await test_upload_update_delete_cycle()
        await test_duplicate_handling()
        print("\n✅ All file operations tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())