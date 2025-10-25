# Testing Framework for PJSUA2 Call Monitoring System

This document describes the testing framework setup for the PJSUA2 call monitoring system.

## Overview

The project uses **pytest** as the primary testing framework with the following features:
- Unit testing with mocking for external dependencies
- Integration testing capabilities
- Code coverage reporting
- Test categorization with markers
- Custom test runner script

## Dependencies

The testing framework requires the following packages:
- `pytest>=7.0.0` - Core testing framework
- `pytest-cov>=4.0.0` - Coverage reporting
- `pytest-mock` - Enhanced mocking capabilities (included with pytest)

## Installation

Install the testing dependencies:

```bash
pip install pytest pytest-cov
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

## Project Structure

```
├── tests/                          # Test directory
│   ├── __init__.py                 # Package initialization
│   ├── conftest.py                 # Pytest configuration and fixtures
│   ├── test_setup.py              # Basic setup tests
│   ├── test_elasticsearch_client.py # Elasticsearch client tests
│   └── test_main.py               # Main module tests
├── pytest.ini                     # Pytest configuration
├── run_tests.py                   # Custom test runner script
└── TESTING.md                     # This file
```

## Configuration

### pytest.ini

The main pytest configuration is in `pytest.ini`:

- **Test Discovery**: Tests are discovered in the `tests/` directory
- **Coverage**: Configured to test `elasticsearch_client` and `main` modules
- **Markers**: Custom markers for test categorization
- **Output**: Verbose output with short traceback format
- **Logging**: Configured for test logging

### Test Markers

The following markers are available for categorizing tests:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (require external services)
- `@pytest.mark.slow` - Slow running tests
- `@pytest.mark.elasticsearch` - Tests requiring Elasticsearch
- `@pytest.mark.pjsua` - Tests requiring PJSUA2 library

## Running Tests

### Using pytest directly

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_setup.py

# Run tests with specific marker
pytest -m unit

# Run tests without coverage
pytest --no-cov

# Run tests with coverage report
pytest --cov=elasticsearch_client --cov=main --cov-report=html
```

### Using the custom test runner

```bash
# Run all tests
python run_tests.py

# Run only unit tests
python run_tests.py --type unit

# Run only integration tests
python run_tests.py --type integration

# Run fast tests (exclude slow tests)
python run_tests.py --type fast

# Run with verbose output
python run_tests.py --verbose

# Run without coverage
python run_tests.py --no-coverage
```

## Test Fixtures

The `conftest.py` file provides several useful fixtures:

### Mock Fixtures

- `mock_elasticsearch_client` - Mock Elasticsearch client
- `mock_pjsua2` - Mock PJSUA2 library
- `sample_call_data` - Sample call data for testing

### Environment Fixtures

- `setup_test_environment` - Sets up test environment variables
- `temp_recording_dir` - Temporary directory for recording files

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
        # Your test code here
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

#### Unit Tests
- Fast, isolated tests
- Use mocks for external dependencies
- Test individual functions and methods
- Should not require external services

#### Integration Tests
- Test interaction between components
- May require external services
- Use `@pytest.mark.integration` marker
- Can be skipped if services unavailable

#### Slow Tests
- Tests that take longer to run
- Use `@pytest.mark.slow` marker
- Can be excluded with `--type fast`

## Coverage Reporting

The project is configured to generate coverage reports:

- **Terminal**: Shows coverage summary in terminal
- **HTML**: Generates `htmlcov/index.html` for detailed coverage
- **XML**: Generates `coverage.xml` for CI/CD integration

### Coverage Configuration

- **Target modules**: `elasticsearch_client`, `main`
- **Minimum coverage**: 70% (configurable in pytest.ini)
- **Excluded files**: Test files, configuration files

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

## Troubleshooting

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

## Examples

### Testing Elasticsearch Client

```python
def test_log_call_record(self, mock_elasticsearch_client, sample_call_data):
    """Test logging call record to Elasticsearch."""
    with patch('elasticsearch_client.Elasticsearch', return_value=mock_elasticsearch_client):
        client = ElasticsearchLogger()
        client.connected = True
        
        result = client.log_call_record(sample_call_data)
        
        assert result is True
        mock_elasticsearch_client.index.assert_called_once()
```

### Testing with Environment Variables

```python
def test_environment_variables(self):
    """Test that environment variables are set correctly."""
    assert os.environ.get("ELASTICSEARCH_HOST") == "localhost"
    assert os.environ.get("ELASTICSEARCH_PORT") == "9200"
```

## Contributing

When adding new tests:

1. Follow the existing test structure
2. Use appropriate markers
3. Add docstrings to test methods
4. Ensure tests are isolated and repeatable
5. Update this documentation if needed

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Python unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
