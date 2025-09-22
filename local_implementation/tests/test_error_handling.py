#!/usr/bin/env python3
"""Tests for error handling and google.rpc.Status."""

import unittest
import tempfile
import os
from pathlib import Path

from aifs.errors import (
    AIFSError, NotFoundError, InvalidArgumentError, PermissionDeniedError,
    AlreadyExistsError, ResourceExhaustedError, FailedPreconditionError,
    InternalError, create_status_proto, abort_with_status, handle_exception
)
from aifs.storage import StorageBackend
from aifs.asset import AssetManager


class TestAIFSErrors(unittest.TestCase):
    """Test AIFS error classes."""
    
    def test_base_error(self):
        """Test base AIFSError."""
        error = AIFSError("Test error", details={"key": "value"})
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.details, {"key": "value"})
    
    def test_not_found_error(self):
        """Test NotFoundError."""
        error = NotFoundError("Asset", "test-id")
        self.assertIn("Asset", str(error))
        self.assertIn("test-id", str(error))
        self.assertEqual(error.details["resource_type"], "Asset")
        self.assertEqual(error.details["resource_id"], "test-id")
    
    def test_invalid_argument_error(self):
        """Test InvalidArgumentError."""
        error = InvalidArgumentError("field", "value", "reason")
        self.assertIn("field", str(error))
        self.assertIn("reason", str(error))
        self.assertEqual(error.details["field"], "field")
        self.assertEqual(error.details["value"], "value")
        self.assertEqual(error.details["reason"], "reason")
    
    def test_permission_denied_error(self):
        """Test PermissionDeniedError."""
        error = PermissionDeniedError("read", "asset-123")
        self.assertIn("read", str(error))
        self.assertIn("asset-123", str(error))
        self.assertEqual(error.details["operation"], "read")
        self.assertEqual(error.details["resource"], "asset-123")
    
    def test_already_exists_error(self):
        """Test AlreadyExistsError."""
        error = AlreadyExistsError("Namespace", "test-ns")
        self.assertIn("Namespace", str(error))
        self.assertIn("test-ns", str(error))
        self.assertEqual(error.details["resource_type"], "Namespace")
        self.assertEqual(error.details["resource_id"], "test-ns")
    
    def test_resource_exhausted_error(self):
        """Test ResourceExhaustedError."""
        error = ResourceExhaustedError("storage", 1000)
        self.assertIn("storage", str(error))
        self.assertIn("1000", str(error))
        self.assertEqual(error.details["resource"], "storage")
        self.assertEqual(error.details["limit"], 1000)
    
    def test_failed_precondition_error(self):
        """Test FailedPreconditionError."""
        error = FailedPreconditionError("asset exists", "Asset not found")
        self.assertIn("asset exists", str(error))
        self.assertIn("Asset not found", str(error))
        self.assertEqual(error.details["condition"], "asset exists")
        self.assertEqual(error.details["reason"], "Asset not found")
    
    def test_internal_error(self):
        """Test InternalError."""
        error = InternalError("storage", "Disk full")
        self.assertIn("storage", str(error))
        self.assertIn("Disk full", str(error))
        self.assertEqual(error.details["operation"], "storage")
        self.assertEqual(error.details["reason"], "Disk full")


class TestStatusProto(unittest.TestCase):
    """Test google.rpc.Status proto creation."""
    
    def test_create_status_proto(self):
        """Test creating status proto from error."""
        error = NotFoundError("Asset", "test-id")
        status = create_status_proto(error)
        
        self.assertEqual(status.code, 5)  # NOT_FOUND
        self.assertIn("Asset", status.message)
        self.assertIn("test-id", status.message)
        self.assertTrue(len(status.details) > 0)
    
    def test_create_status_proto_with_details(self):
        """Test creating status proto with error details."""
        error = InvalidArgumentError("field", "value", "reason")
        status = create_status_proto(error)
        
        self.assertEqual(status.code, 3)  # INVALID_ARGUMENT
        self.assertIn("field", status.message)
        self.assertTrue(len(status.details) > 0)
        
        # Check that details were added (wrapped in Any)
        self.assertIsNotNone(status.details[0])


class TestErrorHandlingIntegration(unittest.TestCase):
    """Test error handling integration with AIFS components."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.asset_manager = AssetManager(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_asset_not_found_error(self):
        """Test that asset not found raises proper error."""
        # Try to get non-existent asset
        asset = self.asset_manager.get_asset("nonexistent" * 8)  # 64 chars
        self.assertIsNone(asset)
    
    def test_invalid_asset_id_error(self):
        """Test that invalid asset ID raises proper error."""
        # Try to get asset with invalid ID (too short)
        asset = self.asset_manager.get_asset("invalid")
        # Should return None for invalid ID, not raise error
        self.assertIsNone(asset)
    
    def test_storage_error_handling(self):
        """Test storage error handling."""
        storage = StorageBackend(self.test_dir)
        
        # Test getting non-existent chunk
        chunk_info = storage.get_chunk_info("nonexistent" * 8)
        self.assertIsNone(chunk_info)
        
        # Test deleting non-existent chunk
        result = storage.delete("nonexistent" * 8)
        self.assertFalse(result)


class TestErrorHandlingMock(unittest.TestCase):
    """Test error handling with mock gRPC context."""
    
    def test_abort_with_status(self):
        """Test aborting with status."""
        class MockContext:
            def __init__(self):
                self.aborted = False
                self.code = None
                self.message = None
                self.details = None
            
            def abort(self, code, message, details=None):
                self.aborted = True
                self.code = code
                self.message = message
                self.details = details
        
        context = MockContext()
        error = NotFoundError("Asset", "test-id")
        
        abort_with_status(context, error)
        
        self.assertTrue(context.aborted)
        self.assertIsNotNone(context.code)
        self.assertIn("Asset", context.message)
        self.assertIn("test-id", context.message)
    
    def test_handle_exception(self):
        """Test handling generic exceptions."""
        class MockContext:
            def __init__(self):
                self.aborted = False
                self.code = None
                self.message = None
            
            def abort(self, code, message, details=None):
                self.aborted = True
                self.code = code
                self.message = message
        
        context = MockContext()
        exception = ValueError("Test exception")
        
        handle_exception(context, "TestOperation", exception)
        
        self.assertTrue(context.aborted)
        self.assertIsNotNone(context.code)
        self.assertIn("TestOperation", context.message)
        self.assertIn("Test exception", context.message)


if __name__ == '__main__':
    unittest.main()
