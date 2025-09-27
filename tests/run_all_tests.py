#!/usr/bin/env python3
"""Test runner for all RAGFlow MCP tests."""

import asyncio
import sys
import importlib.util
from pathlib import Path


async def run_test_module(module_path: Path):
    """Run a test module."""
    print(f"\n{'='*60}")
    print(f"Running: {module_path.name}")
    print(f"{'='*60}")
    
    try:
        # Import and run the module
        spec = importlib.util.spec_from_file_location("test_module", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Run main function if it exists
        if hasattr(module, 'main'):
            await module.main()
        else:
            print("⚠️ No main() function found in test module")
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 RAGFlow MCP Test Suite")
    print("=" * 60)
    
    # Get test directory
    test_dir = Path(__file__).parent
    
    # Define test order (basic tests first)
    test_files = [
        "test_basic_functionality.py",
        "test_search_functionality.py", 
        "test_file_operations.py",
        "test_comprehensive.py"
    ]
    
    results = {}
    
    for test_file in test_files:
        test_path = test_dir / test_file
        
        if test_path.exists():
            success = await run_test_module(test_path)
            results[test_file] = success
        else:
            print(f"⚠️ Test file not found: {test_file}")
            results[test_file] = False
    
    # Summary
    print(f"\n{'='*60}")
    print("🎯 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = 0
    total = len(results)
    
    for test_file, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_file:<30} {status}")
        if success:
            passed += 1
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())