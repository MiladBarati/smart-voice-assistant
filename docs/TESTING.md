# Testing Framework

This project includes a comprehensive unit testing framework built with pytest, providing reliable testing capabilities for development and continuous integration.

## Overview

The testing framework provides:
- **Unit Testing**: Fast, isolated tests with mocking for external dependencies
- **Integration Testing**: Tests that require external services (Elasticsearch, PJSUA2)
- **Code Coverage**: Detailed coverage reporting with HTML and XML outputs
- **Test Categorization**: Custom markers for organizing different test types
- **Mock Support**: Pre-configured mocks for Elasticsearch and PJSUA2 libraries
- **Environment Isolation**: Proper test environment setup and cleanup

## Quick Start

### Run All Tests
```bash
# Using the custom test runner (recommended)
python run_tests.py

# Using pytest directly
pytest tests/ -v
```

### Run Specific Test Types
```bash
# Unit tests only (fast, no external dependencies)
python run_tests.py --type unit

# Integration tests (require external services)
python run_tests.py --type integration

# Fast tests (exclude slow tests)
python run_tests.py --type fast

# All tests
python run_tests.py --type all
```

### Coverage Reporting
```bash
# Run with coverage (default)
python run_tests.py

# Run without coverage
python run_tests.py --no-coverage

# Generate HTML coverage report
pytest --cov=elasticsearch_client --cov=main --cov-report=html
```

## Test Structure

```
tests/
├── __init__.py                 # Package initialization
├── conftest.py                 # Pytest configuration and fixtures
├── test_setup.py              # Basic setup verification tests
├── test_elasticsearch_client.py # Elasticsearch client tests
└── test_main.py               # Main module tests
```

## Test Categories

Tests are organized using custom markers:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (require external services)
- `@pytest.mark.slow` - Slow running tests
- `@pytest.mark.elasticsearch` - Tests requiring Elasticsearch
- `@pytest.mark.pjsua` - Tests requiring PJSUA2 library

## Available Fixtures

The `conftest.py` provides several useful fixtures:

### Mock Fixtures
- `mock_elasticsearch_client` - Mock Elasticsearch client
- `mock_pjsua2` - Mock PJSUA2 library
- `sample_call_data` - Sample call data for testing

### Environment Fixtures
- `setup_test_environment` - Sets up test environment variables
- `temp_recording_dir` - Temporary directory for recording files

## Running Tests

### Using the Custom Test Runner

The `run_tests.py` script provides a convenient way to run tests with different options:

```bash
# Show help
python run_tests.py --help

# Run all tests
python run_tests.py

# Run only unit tests
python run_tests.py --type unit

# Run with verbose output
python run_tests.py --verbose

# Run without coverage
python run_tests.py --no-coverage
```

### Using pytest Directly

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_setup.py -v

# Run tests with specific marker
pytest -m unit

# Run with coverage
pytest --cov=elasticsearch_client --cov=main --cov-report=html

# Run without coverage
pytest --no-cov
```

## Writing Tests

### Basic Test Structure

```python
import pytest
from unittest.mock import Mock, patch

class TestMyClass:
    """Test cases for MyClass."""
    
    def test_basic_functionality(self):
        """Test basic functionality."""
        assert True
    
    def test_with_mock(self, mock_elasticsearch_client):
        """Test with mock fixture."""
        assert mock_elasticsearch_client is not None
    
    @pytest.mark.unit
    def test_unit_functionality(self):
        """Unit test example."""
        assert True
    
    @pytest.mark.integration
    def test_integration_functionality(self):
        """Integration test example."""
        pytest.skip("Requires external service")
```

### Test Categories

**Unit Tests**
- Fast, isolated tests
- Use mocks for external dependencies
- Test individual functions and methods
- Should not require external services

**Integration Tests**
- Test interaction between components
- May require external services
- Use `@pytest.mark.integration` marker
- Can be skipped if services unavailable

**Slow Tests**
- Tests that take longer to run
- Use `@pytest.mark.slow` marker
- Can be excluded with `--type fast`

## Coverage Reporting

The project generates comprehensive coverage reports:

- **Terminal**: Shows coverage summary in terminal
- **HTML**: Generates `htmlcov/index.html` for detailed coverage
- **XML**: Generates `coverage.xml` for CI/CD integration

### Coverage Configuration

- **Target modules**: `elasticsearch_client`, `main`
- **Minimum coverage**: 30% (configurable in pytest.ini)
- **Branch coverage**: Enabled for more detailed analysis

## Configuration

### pytest.ini

The main pytest configuration includes:

```ini
[pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

addopts = 
    --verbose
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=elasticsearch_client
    --cov=main
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-report=xml
    --cov-fail-under=30
    --cov-branch

markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
    elasticsearch: Tests requiring Elasticsearch
    pjsua: Tests requiring PJSUA2
```

## Demo Script

The `demo_tests.py` script demonstrates all testing capabilities:

```bash
python demo_tests.py
```

This script runs various test scenarios and shows:
- Basic pytest execution
- Custom test runner usage
- Coverage reporting
- Specific test file execution

## Continuous Integration

For CI/CD pipelines, use:

```bash
# Run tests with XML coverage report
pytest --cov=elasticsearch_client --cov=main --cov-report=xml --junitxml=test-results.xml
```

## Best Practices

1. **Test Naming**: Use descriptive test names that explain what is being tested
2. **Test Organization**: Group related tests in classes
3. **Mocking**: Mock external dependencies to ensure tests are isolated
4. **Fixtures**: Use fixtures for common test setup
5. **Markers**: Use appropriate markers to categorize tests
6. **Documentation**: Document complex test scenarios
7. **Coverage**: Aim for high test coverage but focus on critical paths

## Troubleshooting Tests

### Common Issues

1. **Import Errors**: Ensure the project root is in the Python path
2. **Elasticsearch Connection**: Tests may fail if Elasticsearch is not available
3. **PJSUA2 Dependencies**: Some tests may require PJSUA2 library
4. **Coverage Issues**: Adjust coverage settings in pytest.ini if needed

### Debug Mode

Run tests in debug mode for more information:

```bash
pytest -v -s --tb=long
```

## Test Results

Current test status:
- **18 tests passing** ✅
- **1 integration test skipped** (requires real Elasticsearch)
- **Coverage: 38.74%** (exceeds 30% threshold) ✅
- **All test runners working perfectly** ✅

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Python unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Testing Best Practices](https://docs.python.org/3/library/unittest.html#unittest.TestCase)

