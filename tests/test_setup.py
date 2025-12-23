"""
Basic setup tests to verify the testing framework is working correctly.
"""

import os
import sys
from typing import Any

import pytest

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSetup:
    """Basic tests to verify the testing setup."""

    def test_pytest_working(self) -> None:
        """Test that pytest is working correctly."""
        assert True

    def test_imports(self) -> None:
        """Test that we can import the main modules."""
        try:
            from pjsua_bot import elasticsearch_client

            assert hasattr(elasticsearch_client, "ElasticsearchLogger")
        except ImportError:
            pytest.skip("elasticsearch_client module not available")

        try:
            import main

            assert hasattr(main, "main")
        except ImportError:
            pytest.skip("main module not available")

    def test_environment_variables(self) -> None:
        """Test that environment variables are set correctly in tests."""
        # Check that environment variables exist (values may differ in the
        # actual environment). Check both old and new names for compatibility.
        es_host = os.environ.get("ES_HOST") or os.environ.get("ELASTICSEARCH_HOST")
        es_port = os.environ.get("ES_PORT") or os.environ.get("ELASTICSEARCH_PORT")
        es_index = os.environ.get("ELASTIC_INDEX_PREFIX") or os.environ.get(
            "ELASTICSEARCH_INDEX"
        )

        # Just verify that at least one of the variable name variants is set
        assert es_host is not None, "ES_HOST or ELASTICSEARCH_HOST should be set"
        assert es_port is not None, "ES_PORT or ELASTICSEARCH_PORT should be set"
        assert (
            es_index is not None
        ), "ELASTIC_INDEX_PREFIX or ELASTICSEARCH_INDEX should be set"

    def test_mock_fixtures(
        self,
        mock_elasticsearch_client: Any,
        sample_call_data: Any,
    ) -> None:
        """Test that mock fixtures are working correctly."""
        assert mock_elasticsearch_client is not None
        assert sample_call_data is not None
        assert "call_id" in sample_call_data
        assert "timestamp" in sample_call_data

    @pytest.mark.unit
    def test_unit_marker(self) -> None:
        """Test that unit test markers work."""
        assert True

    @pytest.mark.slow
    def test_slow_marker(self) -> None:
        """Test that slow test markers work."""
        assert True

    @pytest.mark.elasticsearch
    def test_elasticsearch_marker(self) -> None:
        """Test that elasticsearch test markers work."""
        assert True

    @pytest.mark.pjsua
    def test_pjsua_marker(self) -> None:
        """Test that pjsua test markers work."""
        assert True
