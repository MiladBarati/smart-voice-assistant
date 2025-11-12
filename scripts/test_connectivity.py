#!/usr/bin/env python3
"""
Simple connectivity test for Elasticsearch.
This script tests basic network connectivity and Elasticsearch access.
"""

import os
from collections.abc import Sequence
from typing import TypedDict

import requests  # type: ignore[import-untyped]
import urllib3
from dotenv import load_dotenv
from urllib3.exceptions import InsecureRequestWarning

# Load environment variables from .env file
load_dotenv()

# Disable SSL warnings for testing
urllib3.disable_warnings(InsecureRequestWarning)


def test_basic_connectivity() -> bool:
    """Test basic HTTP connectivity to Elasticsearch."""
    host = os.getenv("ES_HOST", "localhost")
    port = int(os.getenv("ES_PORT", "9200"))
    username = os.getenv("ES_USERNAME", "elastic")
    password = os.getenv("ES_PASSWORD", "")

    print(f"Testing connectivity to {host}:{port}")

    # Test 1: Basic HTTP request
    try:
        url = f"https://{host}:{port}"
        print(f"1. Testing HTTPS connection to {url}")

        response = requests.get(
            url, auth=(username, password), verify=False, timeout=10
        )

        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")

        if response.status_code == 200:
            print("   ✅ HTTPS connection successful")
            return True
        else:
            print(f"   ❌ HTTPS failed with status {response.status_code}")

    except requests.exceptions.SSLError as e:
        print(f"   ❌ SSL Error: {e}")
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ Connection Error: {e}")
    except requests.exceptions.Timeout as e:
        print(f"   ❌ Timeout Error: {e}")
    except Exception as e:
        print(f"   ❌ Unexpected Error: {e}")

    # Test 2: Try HTTP instead of HTTPS
    try:
        url = f"http://{host}:{port}"
        print(f"2. Testing HTTP connection to {url}")

        response = requests.get(url, auth=(username, password), timeout=10)

        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")

        if response.status_code == 200:
            print("   ✅ HTTP connection successful")
            return True
        else:
            print(f"   ❌ HTTP failed with status {response.status_code}")

    except Exception as e:
        print(f"   ❌ HTTP Error: {e}")

    # Test 3: Try different port (common Elasticsearch ports)
    for test_port in [9200, 443, 80]:
        try:
            url = f"https://{host}:{test_port}"
            print(f"3. Testing port {test_port}")

            response = requests.get(
                url, auth=(username, password), verify=False, timeout=5
            )

            print(f"   Port {test_port} - Status: {response.status_code}")

        except Exception as e:
            print(f"   Port {test_port} - Error: {str(e)[:100]}")

    return False


class ElasticsearchConfig(TypedDict, total=False):
    hosts: Sequence[str]
    basic_auth: tuple[str, str]
    verify_certs: bool
    request_timeout: float


def test_elasticsearch_client() -> bool:
    """Test using the elasticsearch Python client."""
    print("\n4. Testing with elasticsearch Python client")

    try:
        from elasticsearch import Elasticsearch

        # Get configuration from environment variables
        host = os.getenv("ES_HOST", "localhost")
        port = int(os.getenv("ES_PORT", "9200"))
        username = os.getenv("ES_USERNAME", "elastic")
        password = os.getenv("ES_PASSWORD", "")

        # Try different configurations
        configs: list[ElasticsearchConfig] = [
            # Config 1: HTTPS with verify_certs=False
            {
                "hosts": [f"https://{host}:{port}"],
                "basic_auth": (username, password),
                "verify_certs": False,
                "request_timeout": 10,
            },
            # Config 2: HTTP
            {
                "hosts": [f"http://{host}:{port}"],
                "basic_auth": (username, password),
                "request_timeout": 10,
            },
            # Config 3: Different port (443)
            {
                "hosts": [f"https://{host}:443"],
                "basic_auth": (username, password),
                "verify_certs": False,
                "request_timeout": 10,
            },
        ]

        for i, config in enumerate(configs, 1):
            try:
                hosts = config.get("hosts", [])
                host_label = hosts[0] if hosts else "unknown host"
                print(f"   Config {i}: {host_label}")
                client = Elasticsearch(**config)
                result = client.ping()
                print(f"   ✅ Ping successful: {result}")
                return True
            except Exception as e:
                print(f"   ❌ Config {i} failed: {str(e)[:100]}")

    except ImportError:
        print("   ❌ elasticsearch module not available")

    return False


if __name__ == "__main__":
    print("Elasticsearch Connectivity Test")
    print("=" * 40)

    # Test basic connectivity
    basic_success = test_basic_connectivity()

    # Test elasticsearch client
    client_success = test_elasticsearch_client()

    print("\n" + "=" * 40)
    if basic_success or client_success:
        print("✅ At least one connection method worked!")
    else:
        print("❌ All connection methods failed")
        print("\nPossible issues:")
        print("- Elasticsearch server is down")
        print("- Wrong IP address or port")
        print("- Firewall blocking the connection")
        print("- Wrong credentials")
        print("- Network connectivity issues")
