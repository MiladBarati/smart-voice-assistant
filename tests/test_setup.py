"""
Basic setup tests to verify the testing framework is working correctly.
"""
import pytest
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSetup:
    """Basic tests to verify the testing setup."""

    def test_pytest_working(self):
        """Test that pytest is working correctly."""
        assert True

    def test_imports(self):
        """Test that we can import the main modules."""
        try:
            import elasticsearch_client
            assert hasattr(elasticsearch_client, 'ElasticsearchLogger')
        except ImportError:
            pytest.skip("elasticsearch_client module not available")
        
        try:
            import main
            assert hasattr(main, 'main')
        except ImportError:
            pytest.skip("main module not available")

    def test_environment_variables(self):
        """Test that environment variables are set correctly in tests."""
        # These should be set by the conftest.py fixture
        assert os.environ.get("ELASTICSEARCH_HOST") == "localhost"
        assert os.environ.get("ELASTICSEARCH_PORT") == "9200"
        assert os.environ.get("ELASTICSEARCH_INDEX") == "test_calls"

    def test_mock_fixtures(self, mock_elasticsearch_client, sample_call_data):
        """Test that mock fixtures are working correctly."""
        assert mock_elasticsearch_client is not None
        assert sample_call_data is not None
        assert "call_id" in sample_call_data
        assert "timestamp" in sample_call_data

    @pytest.mark.unit
    def test_unit_marker(self):
        """Test that unit test markers work."""
        assert True

    @pytest.mark.slow
    def test_slow_marker(self):
        """Test that slow test markers work."""
        assert True

    @pytest.mark.elasticsearch
    def test_elasticsearch_marker(self):
        """Test that elasticsearch test markers work."""
        assert True

    @pytest.mark.pjsua
    def test_pjsua_marker(self):
        """Test that pjsua test markers work."""
        assert True
