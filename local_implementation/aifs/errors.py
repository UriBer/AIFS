"""AIFS Error Handling

Implements proper google.rpc.Status error handling as specified in the AIFS architecture.
"""

from typing import Optional, Dict, Any
import grpc
from google.rpc import status_pb2, code_pb2
from google.rpc import error_details_pb2


class AIFSError(Exception):
    """Base exception for AIFS errors."""
    
    def __init__(self, message: str, code: int = code_pb2.UNKNOWN, 
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class NotFoundError(AIFSError):
    """Asset or resource not found."""
    
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            f"{resource_type} '{resource_id}' not found",
            code=code_pb2.NOT_FOUND,
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


class InvalidArgumentError(AIFSError):
    """Invalid argument provided."""
    
    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            f"Invalid argument for field '{field}': {reason}",
            code=code_pb2.INVALID_ARGUMENT,
            details={"field": field, "value": str(value), "reason": reason}
        )


class PermissionDeniedError(AIFSError):
    """Permission denied for operation."""
    
    def __init__(self, operation: str, resource: str):
        super().__init__(
            f"Permission denied for operation '{operation}' on resource '{resource}'",
            code=code_pb2.PERMISSION_DENIED,
            details={"operation": operation, "resource": resource}
        )


class AlreadyExistsError(AIFSError):
    """Resource already exists."""
    
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            f"{resource_type} '{resource_id}' already exists",
            code=code_pb2.ALREADY_EXISTS,
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


class ResourceExhaustedError(AIFSError):
    """Resource exhausted (quota exceeded)."""
    
    def __init__(self, resource: str, limit: int):
        super().__init__(
            f"Resource '{resource}' exhausted (limit: {limit})",
            code=code_pb2.RESOURCE_EXHAUSTED,
            details={"resource": resource, "limit": limit}
        )


class FailedPreconditionError(AIFSError):
    """Operation failed due to precondition not met."""
    
    def __init__(self, condition: str, reason: str):
        super().__init__(
            f"Precondition failed: {condition} - {reason}",
            code=code_pb2.FAILED_PRECONDITION,
            details={"condition": condition, "reason": reason}
        )


class InternalError(AIFSError):
    """Internal server error."""
    
    def __init__(self, operation: str, reason: str):
        super().__init__(
            f"Internal error during {operation}: {reason}",
            code=code_pb2.INTERNAL,
            details={"operation": operation, "reason": reason}
        )


def create_status_proto(error: AIFSError) -> status_pb2.Status:
    """Create a google.rpc.Status proto from an AIFSError.
    
    Args:
        error: AIFSError instance
        
    Returns:
        google.rpc.Status proto
    """
    from google.protobuf import any_pb2
    
    status = status_pb2.Status()
    status.code = error.code
    status.message = error.message
    
    # Add error details if available
    if error.details:
        # Add BadRequest details for validation errors
        if error.code == code_pb2.INVALID_ARGUMENT:
            bad_request = error_details_pb2.BadRequest()
            for field, value in error.details.items():
                field_violation = bad_request.field_violations.add()
                field_violation.field = field
                field_violation.description = str(value)
            
            # Wrap in Any
            any_detail = any_pb2.Any()
            any_detail.Pack(bad_request)
            status.details.append(any_detail)
        
        # Add ResourceInfo details for resource errors
        elif error.code in [code_pb2.NOT_FOUND, code_pb2.ALREADY_EXISTS, code_pb2.PERMISSION_DENIED]:
            resource_info = error_details_pb2.ResourceInfo()
            if "resource_type" in error.details:
                resource_info.resource_type = error.details["resource_type"]
            if "resource_id" in error.details:
                resource_info.resource_name = error.details["resource_id"]
            
            # Wrap in Any
            any_detail = any_pb2.Any()
            any_detail.Pack(resource_info)
            status.details.append(any_detail)
        
        # Add QuotaFailure details for resource exhaustion
        elif error.code == code_pb2.RESOURCE_EXHAUSTED:
            quota_failure = error_details_pb2.QuotaFailure()
            violation = quota_failure.violations.add()
            if "resource" in error.details:
                violation.subject = error.details["resource"]
            if "limit" in error.details:
                violation.description = f"Limit: {error.details['limit']}"
            
            # Wrap in Any
            any_detail = any_pb2.Any()
            any_detail.Pack(quota_failure)
            status.details.append(any_detail)
    
    return status


def abort_with_status(context, error: AIFSError):
    """Abort gRPC context with proper status.
    
    Args:
        context: gRPC context
        error: AIFSError instance
    """
    # Map gRPC status codes
    grpc_code_map = {
        code_pb2.OK: grpc.StatusCode.OK,
        code_pb2.CANCELLED: grpc.StatusCode.CANCELLED,
        code_pb2.UNKNOWN: grpc.StatusCode.UNKNOWN,
        code_pb2.INVALID_ARGUMENT: grpc.StatusCode.INVALID_ARGUMENT,
        code_pb2.DEADLINE_EXCEEDED: grpc.StatusCode.DEADLINE_EXCEEDED,
        code_pb2.NOT_FOUND: grpc.StatusCode.NOT_FOUND,
        code_pb2.ALREADY_EXISTS: grpc.StatusCode.ALREADY_EXISTS,
        code_pb2.PERMISSION_DENIED: grpc.StatusCode.PERMISSION_DENIED,
        code_pb2.RESOURCE_EXHAUSTED: grpc.StatusCode.RESOURCE_EXHAUSTED,
        code_pb2.FAILED_PRECONDITION: grpc.StatusCode.FAILED_PRECONDITION,
        code_pb2.ABORTED: grpc.StatusCode.ABORTED,
        code_pb2.OUT_OF_RANGE: grpc.StatusCode.OUT_OF_RANGE,
        code_pb2.UNIMPLEMENTED: grpc.StatusCode.UNIMPLEMENTED,
        code_pb2.INTERNAL: grpc.StatusCode.INTERNAL,
        code_pb2.UNAVAILABLE: grpc.StatusCode.UNAVAILABLE,
        code_pb2.DATA_LOSS: grpc.StatusCode.DATA_LOSS,
        code_pb2.UNAUTHENTICATED: grpc.StatusCode.UNAUTHENTICATED,
    }
    
    grpc_code = grpc_code_map.get(error.code, grpc.StatusCode.UNKNOWN)
    
    # Create status proto
    status_proto = create_status_proto(error)
    
    # Abort with status - gRPC context.abort only takes 2 arguments
    context.abort(grpc_code, error.message)


def handle_exception(context, operation: str, exception: Exception):
    """Handle an exception and abort with proper status.
    
    Args:
        context: gRPC context
        operation: Name of the operation that failed
        exception: Exception that occurred
    """
    if isinstance(exception, AIFSError):
        abort_with_status(context, exception)
    else:
        # Convert generic exception to internal error
        error = InternalError(operation, str(exception))
        abort_with_status(context, error)
