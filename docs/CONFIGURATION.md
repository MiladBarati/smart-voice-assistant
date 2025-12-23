# Configuration Options

This document describes all configuration options available for the bot.

## CLI Options

### `register_bot.py` CLI Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--user` | string | *required* | SIP username or extension |
| `--password` | string | *required* | SIP password |
| `--domain` | string | *required* | Registrar/realm host or domain |
| `--auth-user` | string | `None` | Authentication username (if different from user) |
| `--local-port` | int | 5060 | Local SIP port to bind |
| `--wait-seconds` | int | 10 | Time to wait for registration/connect |
| `--stay-online` | flag | `False` | Keep endpoint running to receive calls |
| `--auto-answer` | flag | `True` | Answer incoming calls with 200 OK (enabled by default) |
| `--no-auto-answer` | flag | `False` | Disable auto-answering of incoming calls |
| `--dest` | string | `None` | Destination SIP URI or extension for outbound call |
| `--hangup-seconds` | int | 0 | Auto hangup after N seconds of connection; 0 to disable |
| `--outbound-proxy` | string | `None` | Outbound proxy URI (e.g., `sip:host:5060;lr`) |
| `--transport` | choice | `udp` | SIP transport: udp, tcp, or tls |
| `--tls-verify` | flag | `False` | Verify TLS server certificate (when using TLS) |
| `--log-level` | int | 3 | Endpoint log level (0-6, higher = more verbose) |
| `--play-file` | string | `welcome_message.wav` | Path to WAV file to play to remote when call connects |
| `--hangup-delay` | int       
| 2 | Seconds to wait after welcome message before hanging up |
| `--message-duration` | int | 5 | Fallback duration if WAV file cannot be read (auto-detected from file) |
| `--enable-recording` | flag | `False` | Enable voice capture for incoming calls |
| `--recording-path` | string | `./artifacts/recordings` | Base directory for storing recorded audio files |

## Environment Variables

This project uses environment variables for secure configuration management, particularly for Elasticsearch integration.

### Elasticsearch Configuration

Create a `.env` file in your project root with the following variables:

```bash
# Elasticsearch Configuration
ES_HOST="your-elasticsearch-host"
ES_PORT="9200"
ES_USERNAME="elastic"
ES_PASSWORD="your-secure-password"
ES_USE_SSL="false"
ES_VERIFY_CERTS="false"
ELASTIC_INDEX_PREFIX="pjsua-calls"
```

### Environment Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ES_HOST` | `localhost` | Elasticsearch server hostname or IP |
| `ES_PORT` | `9200` | Elasticsearch server port |
| `ES_USERNAME` | `elastic` | Username for Elasticsearch authentication |
| `ES_PASSWORD` | (empty) | Password for Elasticsearch authentication |
| `ES_USE_SSL` | `false` | Whether to use HTTPS for Elasticsearch connection |
| `ES_VERIFY_CERTS` | `false` | Whether to verify SSL certificates |
| `ELASTIC_INDEX_PREFIX` | `pjsua-calls` | Prefix for Elasticsearch index names |

### Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use different `.env` files** for different environments (dev, staging, prod)
3. **Rotate credentials regularly** by updating environment variables
4. **Use strong passwords** for production environments
5. **Enable SSL/TLS** in production (`ES_USE_SSL="true"`)

### Example `.env` Files

#### Development Environment
```bash
# .env.dev
ES_HOST="localhost"
ES_PORT="9200"
ES_USERNAME="elastic"
ES_PASSWORD="dev-password"
ES_USE_SSL="false"
ES_VERIFY_CERTS="false"
ELASTIC_INDEX_PREFIX="pjsua-calls-dev"
```

#### Production Environment
```bash
# .env.prod
ES_HOST="elasticsearch.production.com"
ES_PORT="9200"
ES_USERNAME="elastic"
ES_PASSWORD="super-secure-production-password"
ES_USE_SSL="true"
ES_VERIFY_CERTS="true"
ELASTIC_INDEX_PREFIX="pjsua-calls-prod"
```

### Loading Environment Variables

The application automatically loads environment variables from the `.env` file using `python-dotenv`. You can also:

1. **Set variables in your shell**:
   ```bash
   export ES_HOST="your-host"
   export ES_PASSWORD="your-password"
   ```

2. **Use different `.env` files**:
   ```bash
   # Load specific environment file
   python -c "from dotenv import load_dotenv; load_dotenv('.env.prod')"
   ```

3. **Override at runtime**:
   ```bash
   ES_HOST="override-host" python register_bot.py --user 1001 --password pass --domain pbx.local
   ```


