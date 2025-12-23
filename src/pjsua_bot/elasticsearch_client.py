"""
Elasticsearch client configuration and logging utilities for PJSUA2 call monitoring.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional, cast

from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, RequestError

# Load environment variables from .env file
load_dotenv()


class ElasticsearchLogger:
    """Elasticsearch logging client for call events and monitoring."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_ssl: Optional[bool] = None,
        verify_certs: Optional[bool] = None,
        index_prefix: Optional[str] = None,
        *,
        connect_on_init: bool = True,
    ):
        """
        Initialize Elasticsearch client.

        All configuration is loaded from environment variables by default.
        Parameters can be explicitly provided to override environment variables.

        Environment variables:
            ES_HOST: Elasticsearch host
            ES_PORT: Elasticsearch port
            ES_USERNAME: Username for authentication
            ES_PASSWORD: Password for authentication
            ES_USE_SSL: Whether to use SSL/TLS (true/false)
            ES_VERIFY_CERTS: Whether to verify SSL certificates (true/false)
            ELASTIC_INDEX_PREFIX: Prefix for index names

        Args:
            host: Elasticsearch host (overrides ES_HOST)
            port: Elasticsearch port (overrides ES_PORT)
            username: Username for authentication (overrides ES_USERNAME)
            password: Password for authentication (overrides ES_PASSWORD)
            use_ssl: Whether to use SSL/TLS (overrides ES_USE_SSL)
            verify_certs: Whether to verify SSL certificates (overrides ES_VERIFY_CERTS)
            index_prefix: Prefix for index names (overrides ELASTIC_INDEX_PREFIX)
        """
        # Load configuration from environment variables with fallbacks
        self.host: str = (
            host if host is not None else (os.getenv("ES_HOST") or "localhost")
        )
        self.port: int = (
            port if port is not None else int(os.getenv("ES_PORT") or "9200")
        )
        env_username = os.getenv("ES_USERNAME") or "elastic"
        self.username: str = username if username is not None else env_username
        env_password = os.getenv("ES_PASSWORD") or ""
        self.password: str = password if password is not None else env_password
        env_use_ssl = os.getenv("ES_USE_SSL", "false").lower() == "true"
        self.use_ssl: bool = use_ssl if use_ssl is not None else env_use_ssl
        env_verify = os.getenv("ES_VERIFY_CERTS", "false").lower() == "true"
        self.verify_certs: bool = (
            verify_certs if verify_certs is not None else env_verify
        )
        env_index_prefix = os.getenv("ELASTIC_INDEX_PREFIX") or "pjsua-calls"
        self.index_prefix: str = (
            index_prefix if index_prefix is not None else env_index_prefix
        )
        self.client: Optional[Elasticsearch] = None
        self.connected: bool = False

        # Configure logging
        self.logger = logging.getLogger(__name__)

        # Initialize connection (optional; avoid network I/O at import time in tests)
        if connect_on_init:
            self._connect()

    def _connect(self) -> bool:
        """Establish connection to Elasticsearch."""
        try:
            # Try different connection methods
            connection_url = (
                f"{'https' if self.use_ssl else 'http'}://{self.host}:{self.port}"
            )

            # Configure client for Elasticsearch 7.x/8.x servers
            # Using elasticsearch-py 7.17.x which defaults to API version 7/8
            auth = (
                (self.username, self.password)
                if self.username and self.password
                else None
            )

            # Simple configuration - elasticsearch-py 7.17.x should work with
            # ES 7.x/8.x servers
            self.client = Elasticsearch(
                [connection_url],
                http_auth=auth,
                verify_certs=self.verify_certs,
                request_timeout=10,
                retry_on_timeout=True,
                max_retries=1,
            )

            # Test connection with cluster info instead of ping
            try:
                # Try to get cluster info instead of ping (more reliable)
                if self.client is None:
                    raise RuntimeError("Elasticsearch client not initialized")
                cluster_info = self.client.info()
                if cluster_info:
                    self.connected = True
                    cluster_name = cluster_info.get("cluster_name", "unknown")
                    version = cluster_info.get("version", {}).get("number", "unknown")
                    self.logger.info(
                        (
                            "Connected to Elasticsearch cluster "
                            f"'{cluster_name}' (v{version}) at {self.host}:{self.port}"
                        )
                    )
                    return True
                else:
                    self.logger.error("Failed to get cluster info from Elasticsearch")
                    return False
            except Exception as info_error:
                self.logger.error(f"Cluster info failed with error: {info_error}")
                # Fallback to ping if info() fails
                try:
                    if self.client is None:
                        return False
                    ping_result = self.client.ping()
                    if ping_result:
                        self.connected = True
                        self.logger.info(
                            "Connected to Elasticsearch at %s:%s (via ping)",
                            self.host,
                            self.port,
                        )
                        return True
                    else:
                        self.logger.error("Both cluster info and ping failed")
                        return False
                except Exception as ping_error:
                    self.logger.error(
                        f"Both cluster info and ping failed: {info_error}, {ping_error}"
                    )
                    return False

        except Exception as e:
            self.logger.error(f"Failed to create Elasticsearch client: {e}")
            self.connected = False
            return False

    def _get_index_name(self, doc_type: str = "call") -> str:
        """Generate unified index name for all logs."""
        return self.index_prefix

    def log_call_record(self, call_record: Dict[str, Any]) -> bool:
        """Index a structured call record document matching the requested schema.

        Required keys (when available):
        - call_id, caller_number, callee_ext, start_time, end_time,
          duration_sec, status, direction, media, bot, host, ingest_ts
        """
        if not self.connected:
            if not self._connect():
                return False

        try:
            # Ensure timestamps and ingest_ts are ISO8601 and present
            doc = dict(call_record) if call_record else {}
            if "ingest_ts" not in doc:
                doc["ingest_ts"] = datetime.utcnow().isoformat() + "Z"
            # Provide host if missing
            doc.setdefault("host", self.host)

            # Use unified index for all logs
            index_name = self._get_index_name()
            client = self.client
            if client is None:
                return False
            client.index(index=index_name, document=doc, refresh=False)
            return True
        except Exception as e:
            self.logger.error(f"Error logging call record: {e}")
            return False

    def log_batch_events(self, events: list) -> bool:
        """Log multiple events in a single batch operation for better performance."""
        if not self.connected:
            if not self._connect():
                return False

        if not events:
            return True

        try:
            # Prepare bulk operations
            bulk_operations = []
            for event in events:
                doc_type = event.get("doc_type", "call")

                # Ensure timestamp is present
                if "@timestamp" not in event:
                    event["@timestamp"] = datetime.utcnow().isoformat() + "Z"

                # Add host if missing
                event.setdefault("host", self.host)

                # Create bulk operation
                bulk_operations.append(
                    {"index": {"_index": self._get_index_name(doc_type)}}
                )
                bulk_operations.append(event)

            # Execute bulk operation
            if bulk_operations:
                client = self.client
                if client is None:
                    return False
                response = client.bulk(body=bulk_operations, refresh=False)

                # Check for errors
                if response.get("errors"):
                    error_items = [
                        item
                        for item in response["items"]
                        if "error" in item.get("index", {})
                    ]
                    if error_items:
                        self.logger.error(
                            f"Bulk operation had {len(error_items)} errors"
                        )
                        return False

                self.logger.debug(f"Successfully logged {len(events)} events in batch")
                return True

            return True

        except Exception as e:
            self.logger.error(f"Error logging batch events: {e}")
            return False

    def log_call_event(
        self,
        event_type: str,
        call_id: Optional[str] = None,
        call_state: Optional[str] = None,
        call_code: Optional[int] = None,
        remote_uri: Optional[str] = None,
        local_uri: Optional[str] = None,
        duration: Optional[float] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log a call event to Elasticsearch.

        Args:
            event_type: Type of event (e.g., 'incoming_call', 'call_connected',
                'call_ended')
            call_id: Unique call identifier
            call_state: Current call state
            call_code: SIP response code
            remote_uri: Remote party URI
            local_uri: Local party URI
            duration: Call duration in seconds
            additional_data: Additional data to include

        Returns:
            True if successfully logged, False otherwise
        """
        if not self.connected:
            if not self._connect():
                return False

        try:
            # Prepare document
            doc = {
                "@timestamp": datetime.utcnow().isoformat() + "Z",
                "event_type": event_type,
                "call_id": call_id,
                "call_state": call_state,
                "call_code": call_code,
                "remote_uri": remote_uri,
                "local_uri": local_uri,
                "duration": duration,
                "host": self.host,
                "service": "pjsua2",
            }

            # Add additional data if provided
            if additional_data:
                doc.update(additional_data)

            # Remove None values
            doc = {k: v for k, v in doc.items() if v is not None}

            # Index the document in unified index
            index_name = self._get_index_name()
            client = self.client
            if client is None:
                return False
            response = client.index(
                index=index_name,
                document=doc,
                refresh=False,  # Don't wait for refresh for better performance
            )

            self.logger.debug(f"Logged {event_type} event: {response['_id']}")
            return True

        except ConnectionError as e:
            self.logger.error(f"Elasticsearch connection error: {e}")
            self.connected = False
            return False
        except RequestError as e:
            self.logger.error(f"Elasticsearch request error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error logging to Elasticsearch: {e}")
            return False

    def log_registration_event(
        self,
        event_type: str,
        user: str,
        domain: str,
        status: str,
        code: Optional[int] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log a registration event to Elasticsearch.

        Args:
            event_type: Type of event (e.g., 'registration_attempt',
                'registration_success', 'registration_failed')
            user: SIP username
            domain: SIP domain
            status: Registration status
            code: SIP response code
            additional_data: Additional data to include

        Returns:
            True if successfully logged, False otherwise
        """
        if not self.connected:
            if not self._connect():
                return False

        try:
            # Prepare document
            doc = {
                "@timestamp": datetime.utcnow().isoformat() + "Z",
                "event_type": event_type,
                "user": user,
                "domain": domain,
                "status": status,
                "code": code,
                "host": self.host,
                "service": "pjsua2",
            }

            # Add additional data if provided
            if additional_data:
                doc.update(additional_data)

            # Remove None values
            doc = {k: v for k, v in doc.items() if v is not None}

            # Index the document in unified index
            index_name = self._get_index_name()
            client = self.client
            if client is None:
                return False
            response = client.index(index=index_name, document=doc, refresh=False)

            self.logger.debug(f"Logged {event_type} event: {response['_id']}")
            return True

        except Exception as e:
            self.logger.error(f"Error logging registration event: {e}")
            return False

    def log_media_event(
        self,
        event_type: str,
        call_id: Optional[str] = None,
        media_type: Optional[str] = None,
        media_status: Optional[str] = None,
        file_played: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log a media event to Elasticsearch.

        Args:
            event_type: Type of event (e.g., 'media_active', 'playback_started',
                'playback_finished')
            call_id: Call identifier
            media_type: Type of media (audio, video)
            media_status: Media status
            file_played: File being played
            additional_data: Additional data to include

        Returns:
            True if successfully logged, False otherwise
        """
        if not self.connected:
            if not self._connect():
                return False

        try:
            # Prepare document
            doc = {
                "@timestamp": datetime.utcnow().isoformat() + "Z",
                "event_type": event_type,
                "call_id": call_id,
                "media_type": media_type,
                "media_status": media_status,
                "file_played": file_played,
                "host": self.host,
                "service": "pjsua2",
            }

            # Add additional data if provided
            if additional_data:
                doc.update(additional_data)

            # Remove None values
            doc = {k: v for k, v in doc.items() if v is not None}

            # Index the document in unified index
            index_name = self._get_index_name()
            client = self.client
            if client is None:
                return False
            response = client.index(index=index_name, document=doc, refresh=False)

            self.logger.debug(f"Logged {event_type} event: {response['_id']}")
            return True

        except Exception as e:
            self.logger.error(f"Error logging media event: {e}")
            return False

    def log_voice_capture_event(
        self,
        event_type: str,
        call_id: Optional[str] = None,
        voice_captured: bool = False,
        audio_file_path: Optional[str] = None,
        capture_duration: Optional[float] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log a voice capture event to Elasticsearch.

        Args:
            event_type: Type of event (e.g., 'voice_capture_started',
                'voice_capture_finished', 'voice_capture_error')
            call_id: Call identifier
            voice_captured: Whether voice was captured
            audio_file_path: Path to the audio file
            capture_duration: Duration of capture in seconds
            additional_data: Additional data to include

        Returns:
            True if successfully logged, False otherwise
        """
        if not self.connected:
            if not self._connect():
                return False

        try:
            # Prepare document
            doc = {
                "@timestamp": datetime.utcnow().isoformat() + "Z",
                "event_type": event_type,
                "call_id": call_id,
                "voice_captured": voice_captured,
                "audio_file_path": audio_file_path,
                "capture_duration": capture_duration,
                "host": self.host,
                "service": "pjsua2",
            }

            # Add additional data if provided
            if additional_data:
                doc.update(additional_data)

            # Remove None values
            doc = {k: v for k, v in doc.items() if v is not None}

            # Index the document in unified index
            index_name = self._get_index_name()
            client = self.client
            if client is None:
                return False
            response = client.index(index=index_name, document=doc, refresh=False)

            self.logger.debug(f"Logged {event_type} event: {response['_id']}")
            return True

        except Exception as e:
            self.logger.error(f"Error logging voice capture event: {e}")
            return False

    def log_intent_event(
        self,
        event_type: str,
        call_id: Optional[str] = None,
        intent: Optional[str] = None,
        confidence: Optional[float] = None,
        audio_file: Optional[str] = None,
        transcription_length: Optional[int] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log an intent classification event to Elasticsearch.

        Args:
            event_type: Type of event (e.g., 'intent_classified',
                'intent_response_played')
            call_id: Call identifier
            intent: Classified intent name
            confidence: Confidence score for the classification
            audio_file: Path to the response audio file (for response_played events)
            transcription_length: Length of transcription used for classification
            additional_data: Additional data to include

        Returns:
            True if successfully logged, False otherwise
        """
        if not self.connected:
            if not self._connect():
                return False

        try:
            # Prepare document
            doc = {
                "@timestamp": datetime.utcnow().isoformat() + "Z",
                "event_type": event_type,
                "call_id": call_id,
                "intent": intent,
                "confidence": confidence,
                "audio_file": audio_file,
                "transcription_length": transcription_length,
                "host": self.host,
                "service": "pjsua2",
            }

            # Add additional data if provided
            if additional_data:
                doc.update(additional_data)

            # Remove None values
            doc = {k: v for k, v in doc.items() if v is not None}

            # Index the document in unified index
            index_name = self._get_index_name()
            client = self.client
            if client is None:
                return False
            response = client.index(index=index_name, document=doc, refresh=False)

            self.logger.debug(f"Logged {event_type} event: {response['_id']}")
            return True

        except Exception as e:
            self.logger.error(f"Error logging intent event: {e}")
            return False

    def health_check(self) -> Dict[str, Any]:
        """Check Elasticsearch cluster health."""
        if not self.connected:
            # Try to reconnect
            if self._connect():
                pass  # Connection successful, continue with health check
            else:
                return {
                    "status": "disconnected",
                    "error": "Not connected to Elasticsearch",
                }

        try:
            # Get cluster info first
            client = self.client
            if client is None:
                return {
                    "status": "disconnected",
                    "error": "Not connected to Elasticsearch",
                }
            cluster_info = client.info()
            cluster_name = cluster_info.get("cluster_name", "unknown")
            version = cluster_info.get("version", {}).get("number", "unknown")

            # Get cluster health
            health = client.cluster.health()
            return {
                "status": "connected",
                "cluster_name": cluster_name,
                "version": version,
                "cluster_status": health.get("status"),
                "number_of_nodes": health.get("number_of_nodes"),
                "active_shards": health.get("active_shards"),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


class _LazyElasticsearchLogger:
    """Proxy that defers creating/connecting the ES client until first use.

    This keeps module import side-effect free (important for unit tests/CI).
    """

    def __init__(self) -> None:
        object.__setattr__(self, "_instance", cast(ElasticsearchLogger | None, None))

    def _get(self) -> ElasticsearchLogger:
        inst = object.__getattribute__(self, "_instance")
        if inst is None:
            inst = ElasticsearchLogger(connect_on_init=False)
            object.__setattr__(self, "_instance", inst)
        return cast(ElasticsearchLogger, inst)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_instance":
            object.__setattr__(self, name, value)
            return
        setattr(self._get(), name, value)


# Global instance for easy access (lazy; does not connect at import time)
es_logger: Any = _LazyElasticsearchLogger()
