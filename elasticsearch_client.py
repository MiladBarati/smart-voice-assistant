"""
Elasticsearch client configuration and logging utilities for PJSUA2 call monitoring.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, RequestError


class ElasticsearchLogger:
    """Elasticsearch logging client for call events and monitoring."""
    
    def __init__(self, 
                 host: str = "185.243.48.247", 
                 port: int = 9200,
                 username: str = "elastic", 
                 password: str = "h2xzKBNaD2Qub5zVE12",
                 use_ssl: bool = False,
                 verify_certs: bool = False,
                 index_prefix: str = "pjsua-calls"):
        """
        Initialize Elasticsearch client.
        
        Args:
            host: Elasticsearch host
            port: Elasticsearch port
            username: Username for authentication
            password: Password for authentication
            use_ssl: Whether to use SSL/TLS
            verify_certs: Whether to verify SSL certificates
            index_prefix: Prefix for index names
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.verify_certs = verify_certs
        self.index_prefix = index_prefix
        self.client = None
        self.connected = False
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize connection
        self._connect()
    
    def _connect(self) -> bool:
        """Establish connection to Elasticsearch."""
        try:
            # Try different connection methods
            connection_url = f"{'https' if self.use_ssl else 'http'}://{self.host}:{self.port}"
            
            # Use simple configuration for Elasticsearch 7.x client
            self.client = Elasticsearch(
                [connection_url],
                http_auth=(self.username, self.password),
                verify_certs=self.verify_certs,
                request_timeout=10,
                retry_on_timeout=True,
                max_retries=1
            )
            
            # Test connection with cluster info instead of ping
            try:
                # Try to get cluster info instead of ping (more reliable)
                cluster_info = self.client.info()
                if cluster_info:
                    self.connected = True
                    cluster_name = cluster_info.get('cluster_name', 'unknown')
                    version = cluster_info.get('version', {}).get('number', 'unknown')
                    self.logger.info(f"Connected to Elasticsearch cluster '{cluster_name}' (v{version}) at {self.host}:{self.port}")
                    return True
                else:
                    self.logger.error("Failed to get cluster info from Elasticsearch")
                    return False
            except Exception as info_error:
                self.logger.error(f"Cluster info failed with error: {info_error}")
                # Fallback to ping if info() fails
                try:
                    ping_result = self.client.ping()
                    if ping_result:
                        self.connected = True
                        self.logger.info(f"Connected to Elasticsearch at {self.host}:{self.port} (via ping)")
                        return True
                    else:
                        self.logger.error("Both cluster info and ping failed")
                        return False
                except Exception as ping_error:
                    self.logger.error(f"Both cluster info and ping failed: {info_error}, {ping_error}")
                    return False
                
        except Exception as e:
            self.logger.error(f"Failed to create Elasticsearch client: {e}")
            self.connected = False
            return False
    
    def _get_index_name(self, doc_type: str = "call") -> str:
        """Generate index name with date suffix."""
        date_str = datetime.now().strftime("%Y.%m.%d")
        return f"{self.index_prefix}-{doc_type}-{date_str}"

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

            # Index name dedicated for call records
            index_name = self._get_index_name("callrecord")
            self.client.index(index=index_name, body=doc, refresh=False)
            return True
        except Exception as e:
            self.logger.error(f"Error logging call record: {e}")
            return False
    
    def log_call_event(self, 
                      event_type: str, 
                      call_id: Optional[str] = None,
                      call_state: Optional[str] = None,
                      call_code: Optional[int] = None,
                      remote_uri: Optional[str] = None,
                      local_uri: Optional[str] = None,
                      duration: Optional[float] = None,
                      additional_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log a call event to Elasticsearch.
        
        Args:
            event_type: Type of event (e.g., 'incoming_call', 'call_connected', 'call_ended')
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
                "service": "pjsua2"
            }
            
            # Add additional data if provided
            if additional_data:
                doc.update(additional_data)
            
            # Remove None values
            doc = {k: v for k, v in doc.items() if v is not None}
            
            # Index the document
            index_name = self._get_index_name("call")
            response = self.client.index(
                index=index_name,
                body=doc,
                refresh=False  # Don't wait for refresh for better performance
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
    
    def log_registration_event(self, 
                             event_type: str,
                             user: str,
                             domain: str,
                             status: str,
                             code: Optional[int] = None,
                             additional_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log a registration event to Elasticsearch.
        
        Args:
            event_type: Type of event (e.g., 'registration_attempt', 'registration_success', 'registration_failed')
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
                "service": "pjsua2"
            }
            
            # Add additional data if provided
            if additional_data:
                doc.update(additional_data)
            
            # Remove None values
            doc = {k: v for k, v in doc.items() if v is not None}
            
            # Index the document
            index_name = self._get_index_name("registration")
            response = self.client.index(
                index=index_name,
                body=doc,
                refresh=False
            )
            
            self.logger.debug(f"Logged {event_type} event: {response['_id']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error logging registration event: {e}")
            return False
    
    def log_media_event(self, 
                       event_type: str,
                       call_id: Optional[str] = None,
                       media_type: Optional[str] = None,
                       media_status: Optional[str] = None,
                       file_played: Optional[str] = None,
                       additional_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log a media event to Elasticsearch.
        
        Args:
            event_type: Type of event (e.g., 'media_active', 'playback_started', 'playback_finished')
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
                "service": "pjsua2"
            }
            
            # Add additional data if provided
            if additional_data:
                doc.update(additional_data)
            
            # Remove None values
            doc = {k: v for k, v in doc.items() if v is not None}
            
            # Index the document
            index_name = self._get_index_name("media")
            response = self.client.index(
                index=index_name,
                body=doc,
                refresh=False
            )
            
            self.logger.debug(f"Logged {event_type} event: {response['_id']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error logging media event: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Check Elasticsearch cluster health."""
        if not self.connected:
            # Try to reconnect
            if self._connect():
                pass  # Connection successful, continue with health check
            else:
                return {"status": "disconnected", "error": "Not connected to Elasticsearch"}
        
        try:
            # Get cluster info first
            cluster_info = self.client.info()
            cluster_name = cluster_info.get('cluster_name', 'unknown')
            version = cluster_info.get('version', {}).get('number', 'unknown')
            
            # Get cluster health
            health = self.client.cluster.health()
            return {
                "status": "connected",
                "cluster_name": cluster_name,
                "version": version,
                "cluster_status": health.get("status"),
                "number_of_nodes": health.get("number_of_nodes"),
                "active_shards": health.get("active_shards")
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Global instance for easy access
es_logger = ElasticsearchLogger()
