# Testing Framework

This guide consolidates the testing information for the PJSUA2 call monitoring system. It covers dependencies, configuration, fixtures, and workflows for running, extending, and troubleshooting the test suite.

## Overview

The project relies on **pytest** to provide:
- **Unit tests** with robust mocking for external dependencies such as Elasticsearch and PJSUA2
- **Integration tests** that exercise end-to-end flows when external services are available
- **Coverage reporting** in terminal, HTML, and XML formats
- **Custom markers and runner scripts** to target specific subsets of the suite
- **Reusable fixtures** that prepare call data, environment variables, and temporary recording directories

## Dependencies

Install the core testing dependencies:
- `pytest>=7.0.0`
- `pytest-cov>=4.0.0`
- `pytest-mock` (included transitively with pytest, listed here for clarity)

```bash
# Install directly
pip install pytest pytest-cov

# Or install the project's full dependency set
pip install -r requirements.txt
```

## Project Structure

```
tests/
├── __init__.py
├── conftest.py                 # Shared fixtures and configuration
├── test_setup.py               # Basic setup verification
├── test_elasticsearch_client.py
└── test_main.py

pytest.ini                      # Pytest configuration
run_tests.py                    # Custom test runner script
docs/TESTING.md                 # This guide
```

## Test Configuration

Key configuration lives in `pytest.ini`:
- **Discovery**: Targets the `tests/` directory with standard `test_*.py` naming patterns
- **Markers**: `unit`, `integration`, `slow`, `elasticsearch`, `pjsua`
- **Coverage**: Focuses on `elasticsearch_client` and `main`, with branch coverage enabled
- **Output**: Verbose output, short tracebacks, and CLI logging
- **Thresholds**: Coverage fails below 30% (`--cov-fail-under=30`)

Refer to `pytest.ini` for the complete list of options.

## Running Tests

**Custom runner (`run_tests.py`)**
```bash
python run_tests.py                 # Run all tests with coverage
python run_tests.py --type unit     # Only unit tests
python run_tests.py --type integration
python run_tests.py --type fast     # Exclude slow tests
python run_tests.py --verbose
python run_tests.py --no-coverage
```

**pytest directly**
```bash
pytest                              # Default run (verbose via pytest.ini)
pytest tests/test_setup.py          # Specific file
pytest -m unit                      # Marker selection
pytest --no-cov                     # Skip coverage
pytest --cov=elasticsearch_client --cov=main --cov-report=html  # HTML report
```

## Available Fixtures

Defined in `tests/conftest.py`:
- **Mock fixtures**: `mock_elasticsearch_client`, `mock_pjsua2`, `sample_call_data`
- **Environment fixtures**: `setup_test_environment`, `temp_recording_dir`

Reuse these fixtures in new tests to avoid duplicating setup logic.

## Writing Tests

```python
import pytest

class TestMyFeature:
    """Example test class."""

    def test_basic_functionality(self):
        assert True

    def test_with_mock(self, mock_elasticsearch_client):
        assert mock_elasticsearch_client is not None

    @pytest.mark.unit
    def test_unit_case(self):
        assert True

    @pytest.mark.integration
    def test_integration_case(self):
        pytest.skip("Requires external service")
```

### Test Categories
- **Unit**: Fast, isolated, no external dependencies
- **Integration**: Cross-component flows; may require Elasticsearch or PJSUA2
- **Slow**: Long-running scenarios; exclude with `--type fast`
- **Elasticsearch / PJSUA**: Explicitly flag tests that interact with those services

## Coverage Reporting

Generated automatically when coverage is enabled:
- **Terminal** summary during the run
- **HTML** report at `htmlcov/index.html`
- **XML** report (`coverage.xml`) for CI/CD

Tune thresholds or targets in `pytest.ini` if coverage requirements change.

## Continuous Integration

Use these commands in pipelines or pre-commit hooks:
```bash
pytest --cov=elasticsearch_client --cov=main --cov-report=xml --junitxml=test-results.xml
```
Adjust reporting flags as needed for your CI provider.

## Troubleshooting

- **Import errors**: Ensure the repository root is on `PYTHONPATH`
- **Elasticsearch / PJSUA2 failures**: Confirm services or mocks are available
- **Coverage below threshold**: Review ignored files and add targeted tests
- **Debugging**: Run `pytest -v -s --tb=long` for verbose logs and tracebacks

## Example Scenarios

```python
from pjsua_bot.elasticsearch_client import ElasticsearchLogger

def test_log_call_record(mock_elasticsearch_client, sample_call_data):
    """Validate Elasticsearch logging behaviour."""
    logger = ElasticsearchLogger()
    logger.connected = True
    assert logger.log_call_record(sample_call_data)
    mock_elasticsearch_client.index.assert_called_once()
```

```python
import os

def test_environment_setup(setup_test_environment):
    """Ensure environment variables required for tests are available."""
    assert os.environ["ELASTICSEARCH_HOST"]
    assert os.environ["ELASTICSEARCH_PORT"]
```

## Best Practices
- Name tests descriptively and document non-obvious scenarios
- Group related tests in classes or modules
- Mock external dependencies by default; reserve integration tests for full flows
- Use fixtures for shared setup/teardown logic
- Keep documentation current when adding or reorganizing tests

## Resources
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)


