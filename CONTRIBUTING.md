# Contributing to AIFS

Thank you for your interest in contributing to AIFS! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites
- Python 3.9+
- Git
- Make (optional, for using Makefile)

### Setup
```bash
# Clone the repository
git clone https://github.com/UriBer/AIFS.git
cd AIFS/local_implementation

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov black flake8 mypy

# Run tests to verify setup
python run_tests.py
```

## Code Style

### Python
- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Maximum line length: 88 characters (Black default)
- Use meaningful variable and function names

### Code Formatting
```bash
# Format code with Black
black aifs/ tests/

# Check formatting
black --check aifs/ tests/
```

### Linting
```bash
# Run flake8
flake8 aifs/ tests/

# Run mypy for type checking
mypy aifs/
```

## Testing

### Running Tests
```bash
# Run all tests
python run_tests.py

# Run specific test file
pytest tests/test_asset_manager.py -v

# Run with coverage
pytest --cov=aifs tests/
```

### Writing Tests
- Write tests for all new functionality
- Use descriptive test names
- Follow the existing test patterns
- Aim for high test coverage

## Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/your-feature-name`
3. **Make** your changes
4. **Add** tests for new functionality
5. **Run** the test suite: `python run_tests.py`
6. **Format** your code: `black aifs/ tests/`
7. **Commit** your changes: `git commit -m "Add your feature"`
8. **Push** to your fork: `git push origin feature/your-feature-name`
9. **Create** a Pull Request

### Pull Request Guidelines
- Provide a clear description of changes
- Reference any related issues
- Ensure all tests pass
- Update documentation if needed
- Keep PRs focused and atomic

## Development Workflow

### Branch Naming
- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `test/description` - Test improvements

### Commit Messages
Use clear, descriptive commit messages:
```
Add BLAKE3 hashing support for content addressing

- BLAKE3 is now implemented in storage backend
- Update tests to verify BLAKE3 hash generation
- Add BLAKE3 dependency to requirements.txt
```

## Architecture Guidelines

### Core Principles
- **Content Addressing**: All data identified by content hash
- **Vector-First**: Metadata designed for ML workloads
- **Versioned Snapshots**: Immutable versioning with Merkle trees
- **Security**: Encryption and authentication throughout

### Component Guidelines
- **Storage Backend**: Content-addressed, chunked storage
- **Vector Database**: FAISS integration for similarity search
- **Metadata Store**: SQLite for metadata and lineage
- **gRPC API**: High-performance RPC interface
- **Crypto Manager**: Ed25519 signatures and AES-256-GCM encryption

## Documentation

### Code Documentation
- Use docstrings for all public functions and classes
- Follow Google docstring format
- Include type hints in function signatures

### API Documentation
- Update `API.md` for any API changes
- Include usage examples
- Document error conditions

### README Updates
- Update relevant README files
- Include new features in changelog
- Update installation instructions if needed

## Issue Reporting

### Bug Reports
When reporting bugs, please include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or error messages

### Feature Requests
For feature requests, please include:
- Clear description of the feature
- Use case and motivation
- Proposed implementation approach (if any)
- Any relevant examples

## Release Process

### Version Numbering
We use [Semantic Versioning](https://semver.org/):
- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Version numbers updated
- [ ] Release notes prepared

## Community Guidelines

### Code of Conduct
- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow the golden rule

### Getting Help
- Check existing issues and discussions
- Ask questions in GitHub Discussions
- Join our community chat (if available)
- Read the documentation thoroughly

## License

By contributing to AIFS, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

## Thank You

Thank you for contributing to AIFS! Your contributions help make AI-native storage accessible to everyone.
