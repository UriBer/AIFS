# AIFS Test Suite

This directory contains comprehensive tests for the AIFS (AI-Native File System) implementation.

## Test Categories

### Core Functionality Tests
- **`test_basic.py`** - Basic AIFS functionality tests
- **`test_asset_manager.py`** - Asset management tests
- **`test_storage.py`** - Storage backend tests
- **`test_merkle_tree.py`** - Merkle tree implementation tests
- **`test_crypto.py`** - Cryptographic operations tests
- **`test_auth.py`** - Authentication and authorization tests

### New Feature Tests
- **`test_blake3_uri.py`** - BLAKE3 hashing and URI schemes tests
- **`test_error_handling.py`** - Error handling and google.rpc.Status tests
- **`test_encryption_kms.py`** - AES-256-GCM encryption and KMS integration tests
- **`test_grpc_server.py`** - gRPC server functionality tests
- **`test_merkle_blake3.py`** - Merkle tree with BLAKE3 hashing tests

### Service Tests
- **`test_builtin_services.py`** - Built-in services (Health, Introspect, Admin, etc.) tests
- **`test_compression.py`** - Compression functionality tests

## Running Tests

### Run All Tests
```bash
cd local_implementation
python -m pytest tests/ -v
```

### Run Specific Test Categories
```bash
# Core functionality
python -m pytest tests/test_basic.py tests/test_asset_manager.py tests/test_storage.py -v

# New features
python -m pytest tests/test_blake3_uri.py tests/test_error_handling.py tests/test_encryption_kms.py -v

# gRPC server
python -m pytest tests/test_grpc_server.py -v

# Merkle tree
python -m pytest tests/test_merkle_tree.py tests/test_merkle_blake3.py -v
```

### Run Individual Tests
```bash
# BLAKE3 and URI tests
python -m pytest tests/test_blake3_uri.py::TestBLAKE3Hashing::test_blake3_hash_generation -v

# Error handling tests
python -m pytest tests/test_error_handling.py::TestAIFSErrors::test_not_found_error -v

# Encryption tests
python -m pytest tests/test_encryption_kms.py::TestAES256GCMEncryption::test_encryption_decryption -v
```

## Test Requirements

### Dependencies
All required dependencies are listed in `requirements.txt`:
- `blake3` - BLAKE3 hashing
- `cryptography` - AES-256-GCM encryption and Ed25519 signatures
- `grpcio-status` - gRPC status handling
- `grpcio-reflection` - gRPC reflection
- `numpy` - Vector operations
- `faiss-cpu` - Vector database
- `grpcio` - gRPC framework

### Test Data
Tests use temporary directories and clean up after themselves. No persistent test data is created.

## Test Coverage

### Implemented Features (✅ Tested)
- **BLAKE3 Content Addressing** - Hash generation, validation, consistency
- **URI Schemes** - `aifs://` and `aifs-snap://` URI creation and parsing
- **AES-256-GCM Encryption** - Data encryption/decryption, security properties
- **KMS Integration** - Envelope encryption metadata storage
- **Ed25519 Signatures** - Snapshot signing and verification
- **Error Handling** - Structured error types and google.rpc.Status
- **gRPC Server** - All RPC methods and error handling
- **Merkle Trees** - Tree construction, proof generation, verification

### Test Scenarios

#### BLAKE3 Hashing
- Hash generation and validation
- Deterministic hashing
- Different data produces different hashes
- Content-addressed storage consistency

#### URI Schemes
- Asset URI creation and parsing
- Snapshot URI creation and parsing
- Invalid URI handling
- URI validation

#### Encryption
- Data encryption and decryption
- Large data handling
- Binary data support
- KMS key ID storage and retrieval
- Security properties verification

#### Error Handling
- Structured error types
- google.rpc.Status proto creation
- gRPC error mapping
- Error details and context

#### gRPC Server
- Health check endpoint
- Asset operations (put, get, delete, list)
- Vector search
- Snapshot operations
- Error handling and status codes

#### Merkle Trees
- Tree construction with BLAKE3
- Proof generation and verification
- Deterministic ordering
- Large tree handling
- Tree structure validation

## Test Results

### Expected Results
All tests should pass when run against a properly implemented AIFS system. The tests verify:

1. **Correctness** - All operations produce expected results
2. **Security** - Encryption and hashing work as specified
3. **Consistency** - Content-addressing and deterministic behavior
4. **Error Handling** - Proper error types and status codes
5. **Performance** - Basic performance characteristics

### Known Issues
- Some tests may require specific system configurations
- gRPC server tests need port availability
- Vector database tests require sufficient memory

## Contributing

When adding new features to AIFS:

1. **Add corresponding tests** in the appropriate test file
2. **Update this README** with new test categories
3. **Ensure tests pass** before submitting changes
4. **Add integration tests** for complex features
5. **Test error conditions** and edge cases

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Ensure you're in the correct directory
cd local_implementation

# Install dependencies
pip install -r requirements.txt

# Run tests from the correct location
python -m pytest tests/ -v
```

#### Port Conflicts
```bash
# If gRPC server tests fail due to port conflicts
# Check if port 50052 is available
lsof -i :50052

# Kill any processes using the port
kill -9 <PID>
```

#### Memory Issues
```bash
# If vector database tests fail due to memory
# Reduce test data size or increase system memory
```

#### Permission Issues
```bash
# Ensure write permissions for test directories
chmod 755 local_implementation/tests/
```

### Debug Mode
```bash
# Run tests with debug output
python -m pytest tests/ -v -s --tb=short

# Run specific test with debug
python -m pytest tests/test_grpc_server.py::TestGRPCServer::test_health_check -v -s
```

## Test Metrics

### Coverage Goals
- **Unit Tests**: 90%+ code coverage
- **Integration Tests**: All major workflows
- **Error Tests**: All error conditions
- **Security Tests**: All cryptographic operations

### Performance Benchmarks
- **Hash Generation**: < 1ms per operation
- **Encryption**: < 10ms per MB
- **Vector Search**: < 100ms for 1000 vectors
- **gRPC Calls**: < 50ms per operation

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run AIFS Tests
  run: |
    cd local_implementation
    pip install -r requirements.txt
    python -m pytest tests/ -v --tb=short
```

The test suite provides comprehensive coverage of all AIFS functionality and ensures the system meets the specification requirements.
