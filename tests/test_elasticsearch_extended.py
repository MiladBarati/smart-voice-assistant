"""Extended tests for ElasticsearchLogger to increase coverage."""

from unittest.mock import Mock, patch

from pjsua_bot.elasticsearch_client import ElasticsearchLogger


class TestElasticsearchLoggerExtended:
    """Extended test cases for ElasticsearchLogger class."""

    def test_log_call_record_with_connection_retry(
        self, mock_elasticsearch_client: Mock
    ) -> None:
        """Test logging call record when connection needs to be re-established."""
        with patch(
            "pjsua_bot.elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            client.connected = False  # Simulate disconnected state

            call_data = {
                "call_id": "test-call-123",
                "timestamp": "2024-01-01T00:00:00Z",
            }

            result = client.log_call_record(call_data)
            assert result is True
            mock_elasticsearch_client.index.assert_called()

    def test_log_call_event_with_all_params(
        self, mock_elasticsearch_client: Mock
    ) -> None:
        """Test logging call event with all parameters."""
        with patch(
            "pjsua_bot.elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            client.connected = True

            result = client.log_call_event(
                event_type="call_connected",
                call_id="test-call-123",
                call_state="CONNECTED",
                call_code=200,
                remote_uri="sip:1001@host",
                local_uri="sip:1002@host",
                duration=30.5,
                additional_data={"custom": "data"},
            )

            assert result is True
            mock_elasticsearch_client.index.assert_called_once()

    def test_log_call_event_connection_error(
        self, mock_elasticsearch_client: Mock
    ) -> None:
        """Test logging call event when connection error occurs."""
        from elasticsearch.exceptions import ConnectionError

        # ConnectionError expects (message, errors, info) tuple
        mock_elasticsearch_client.index.side_effect = ConnectionError(
            "Connection failed", {}, {}
        )

        with patch(
            "pjsua_bot.elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            client.connected = True

            result = client.log_call_event("test_event", call_id="test-123")
            assert result is False
            assert client.connected is False

    def test_log_call_event_request_error(
        self, mock_elasticsearch_client: Mock
    ) -> None:
        """Test logging call event when request error occurs."""
        from elasticsearch.exceptions import RequestError

        mock_elasticsearch_client.index.side_effect = RequestError(
            "Request failed", {}, {}
        )

        with patch(
            "pjsua_bot.elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            client.connected = True

            result = client.log_call_event("test_event", call_id="test-123")
            assert result is False

    def test_log_registration_event(self, mock_elasticsearch_client: Mock) -> None:
        """Test logging registration event."""
        with patch(
            "pjsua_bot.elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            client.connected = True

            result = client.log_registration_event(
                event_type="registration_success",
                user="test_user",
                domain="test_domain",
                status="OK",
                code=200,
                additional_data={"extra": "data"},
            )

            assert result is True
            mock_elasticsearch_client.index.assert_called_once()

    def test_log_registration_event_error(
        self, mock_elasticsearch_client: Mock
    ) -> None:
        """Test logging registration event when error occurs."""
        mock_elasticsearch_client.index.side_effect = Exception("Index error")

        with patch(
            "pjsua_bot.elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            client.connected = True

            result = client.log_registration_event(
                event_type="registration_failed",
                user="test_user",
                domain="test_domain",
                status="Failed",
            )

            assert result is False

    def test_log_media_event(self, mock_elasticsearch_client: Mock) -> None:
        """Test logging media event."""
        with patch(
            "pjsua_bot.elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            client.connected = True

            result = client.log_media_event(
                event_type="playback_started",
                call_id="test-call-123",
                media_type="audio",
                media_status="active",
                file_played="/path/to/audio.wav",
                additional_data={"custom": "data"},
            )

            assert result is True
            mock_elasticsearch_client.index.assert_called_once()

    def test_log_media_event_error(self, mock_elasticsearch_client: Mock) -> None:
        """Test logging media event when error occurs."""
        mock_elasticsearch_client.index.side_effect = Exception("Index error")

        with patch(
            "pjsua_bot.elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            client.connected = True

            result = client.log_media_event(
                event_type="playback_error",
                call_id="test-call-123",
            )

            assert result is False

    def test_log_voice_capture_event(self, mock_elasticsearch_client: Mock) -> None:
        """Test logging voice capture event."""
        with patch(
            "pjsua_bot.elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            client.connected = True

            result = client.log_voice_capture_event(
                event_type="voice_capture_finished",
                call_id="test-call-123",
                voice_captured=True,
                audio_file_path="/path/to/audio.wav",
                capture_duration=10.5,
                additional_data={"custom": "data"},
            )

            assert result is True
            mock_elasticsearch_client.index.assert_called_once()

    def test_log_voice_capture_event_error(
        self, mock_elasticsearch_client: Mock
    ) -> None:
        """Test logging voice capture event when error occurs."""
        mock_elasticsearch_client.index.side_effect = Exception("Index error")

        with patch(
            "pjsua_bot.elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            client.connected = True

            result = client.log_voice_capture_event(
                event_type="voice_capture_error",
                call_id="test-call-123",
            )

            assert result is False

    def test_log_batch_events_with_errors(
        self, mock_elasticsearch_client: Mock
    ) -> None:
        """Test batch logging when some events have errors."""
        # Simulate bulk response with errors
        mock_elasticsearch_client.bulk.return_value = {
            "errors": True,
            "items": [
                {"index": {"_id": "1", "status": 200}},
                {"index": {"_id": "2", "status": 400, "error": {"type": "error"}}},
            ],
        }

        with patch(
            "pjsua_bot.elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            client.connected = True

            events = [
                {"event_type": "test1", "doc_type": "call"},
                {"event_type": "test2", "doc_type": "call"},
            ]

            result = client.log_batch_events(events)
            assert result is False

    def test_log_batch_events_empty_list(self, mock_elasticsearch_client: Mock) -> None:
        """Test batch logging with empty event list."""
        with patch(
            "pjsua_bot.elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            client.connected = True

            result = client.log_batch_events([])
            assert result is True
            mock_elasticsearch_client.bulk.assert_not_called()

    def test_log_batch_events_exception(self, mock_elasticsearch_client: Mock) -> None:
        """Test batch logging when exception occurs."""
        mock_elasticsearch_client.bulk.side_effect = Exception("Bulk error")

        with patch(
            "pjsua_bot.elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            client.connected = True

            events = [{"event_type": "test", "doc_type": "call"}]
            result = client.log_batch_events(events)
            assert result is False

    def test_log_batch_events_no_client(self, mock_elasticsearch_client: Mock) -> None:
        """Test batch logging when client is None."""
        with patch(
            "pjsua_bot.elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            client.connected = True
            client.client = None  # Simulate no client

            events = [{"event_type": "test", "doc_type": "call"}]
            result = client.log_batch_events(events)
            assert result is False

    def test_get_index_name(self) -> None:
        """Test getting index name."""
        with patch("pjsua_bot.elasticsearch_client.Elasticsearch"):
            client = ElasticsearchLogger(index_prefix="test-prefix")
            index_name = client._get_index_name()
            # _get_index_name just returns the prefix, not including doc_type
            assert index_name == "test-prefix"

    def test_get_index_name_different_doc_type(self) -> None:
        """Test getting index name with different doc type."""
        with patch("pjsua_bot.elasticsearch_client.Elasticsearch"):
            client = ElasticsearchLogger(index_prefix="test-prefix")
            index_name = client._get_index_name()
            assert "test-prefix" in index_name

    def test_health_check_not_connected(self, mock_elasticsearch_client: Mock) -> None:
        """Test health check when not connected."""
        mock_elasticsearch_client.info.side_effect = Exception("Not connected")
        mock_elasticsearch_client.ping.return_value = False

        with patch(
            "pjsua_bot.elasticsearch_client.Elasticsearch",
            return_value=mock_elasticsearch_client,
        ):
            client = ElasticsearchLogger()
            client.connected = False

            result = client.health_check()
            assert "status" in result
            assert result["status"] == "disconnected"
