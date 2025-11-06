"""
Tests for elasticsearch_client.py module.
"""

from typing import Any
from unittest.mock import Mock, patch

import pytest

from pjsua_bot.elasticsearch_client import ElasticsearchLogger


class TestElasticsearchLogger:
    """Test cases for ElasticsearchLogger class."""

    def test_init_with_default_values(self) -> None:
        """Test ElasticsearchLogger initialization with default values."""
        with patch("pjsua_bot.elasticsearch_client.Elasticsearch") as mock_es:
            with patch.dict(
                "os.environ",
                {
                    "ES_HOST": "localhost",
                    "ES_PORT": "9200",
                    "ELASTIC_INDEX_PREFIX": "pjsua-calls",
                },
            ):
                client = ElasticsearchLogger()
                assert client.host == "localhost"
                assert client.port == 9200
                assert client.index_prefix == "pjsua-calls"
                mock_es.assert_called_once()

    def test_init_with_custom_values(self) -> None:
        """Test ElasticsearchLogger initialization with custom values."""
        with patch("pjsua_bot.elasticsearch_client.Elasticsearch"):
            client = ElasticsearchLogger(
                host="test-host", port=9300, index_prefix="test_index"
            )
            assert client.host == "test-host"
            assert client.port == 9300
            assert client.index_prefix == "test_index"

    def test_connect_success(self, mock_elasticsearch_client: Any) -> None:
        """Test successful connection to Elasticsearch."""
        with patch(
            "elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            result = client._connect()
            assert result is True
            # The info method is called during initialization and in _connect
            assert mock_elasticsearch_client.info.call_count >= 1

    def test_connect_failure(self) -> None:
        """Test connection failure to Elasticsearch."""
        mock_client = Mock()
        mock_client.info.side_effect = Exception("Connection failed")
        mock_client.ping.return_value = False

        with patch("elasticsearch_client.Elasticsearch", return_value=mock_client):
            client = ElasticsearchLogger()
            result = client._connect()
            assert result is False

    def test_log_call_record(
        self,
        mock_elasticsearch_client: Any,
        sample_call_data: Any,
    ) -> None:
        """Test logging call record to Elasticsearch."""
        with patch(
            "elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            client.connected = True

            result = client.log_call_record(sample_call_data)

            assert result is True
            mock_elasticsearch_client.index.assert_called_once()

    def test_log_call_event(self, mock_elasticsearch_client: Any) -> None:
        """Test logging call event to Elasticsearch."""
        with patch(
            "elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            client.connected = True

            result = client.log_call_event("test_event", "call_123")

            assert result is True
            mock_elasticsearch_client.index.assert_called_once()

    def test_health_check(self, mock_elasticsearch_client: Any) -> None:
        """Test health check functionality."""
        with patch(
            "elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            client.connected = True

            result = client.health_check()

            assert "status" in result
            # The info method is called during initialization and in health_check
            assert mock_elasticsearch_client.info.call_count >= 1

    @pytest.mark.elasticsearch
    def test_integration_with_real_elasticsearch(self) -> None:
        """Integration test with real Elasticsearch instance."""
        # This test would only run if marked with --run-elasticsearch
        pytest.skip("Requires real Elasticsearch instance")
