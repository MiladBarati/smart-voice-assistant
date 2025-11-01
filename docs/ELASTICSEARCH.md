# Elasticsearch Integration

This project logs exactly one structured document per call to Elasticsearch. The single document is created and sent only once at call end (disconnect) and contains the complete call record (caller/callee, timing, duration, status, media and bot metadata). No per-event or per-stage logs are sent during the call.

## Install Client

Use the 7.x Python client for compatibility with Elasticsearch 8.x servers:

```bash
pip install "elasticsearch>=7.0.0,<8.0.0"
pip install python-dotenv
```

## Configuration

The integration is enabled by default via the internal logger. All configuration is now done through environment variables for security and flexibility.

### Environment Variables

Create a `.env` file in your project root with your Elasticsearch configuration:

```bash
# Elasticsearch Configuration
ES_HOST="your-elasticsearch-host"
ES_PORT="9200"
ES_USERNAME="elastic"
ES_PASSWORD="your-password"
ES_USE_SSL="false"
ES_VERIFY_CERTS="false"
ELASTIC_INDEX_PREFIX="pjsua-calls"
```

### Default Values

If environment variables are not set, the following defaults are used:

- Host: `localhost`
- Port: `9200`
- Username: `elastic`
- Password: (empty)
- SSL: `false`
- Verify Certs: `false`
- Index Prefix: `pjsua-calls`

### Security Benefits

- **No hardcoded credentials** in source code
- **Environment-specific configuration** for dev/staging/prod
- **Easy credential rotation** without code changes
- **Version control safety** - credentials not committed to repository

## Index Pattern

All call records are stored in a single unified index:

- `pjsua-calls` — Contains one record per call

In Kibana (Stack Management → Index Patterns) create:

- `pjsua-calls`

## Unique Call ID System

The bot now uses UUID-based call IDs to ensure uniqueness across program restarts. This solves the issue where PJSUA2's internal call ID counter resets to zero on each restart, causing duplicate call IDs in logs.

**Key Features:**
- **UUID-based IDs**: Each call gets a globally unique identifier
- **Cross-session persistence**: Call IDs remain unique even after program restarts
- **Elasticsearch compatibility**: UUIDs work perfectly with Elasticsearch indexing
- **Backward compatibility**: Original PJSUA2 call ID is preserved for reference

**Implementation Details:**
- Uses Python's `uuid.uuid4()` for generating unique identifiers
- Each `AnyCall` instance gets a `unique_call_id` attribute
- Call records use the UUID as the primary `call_id` field
- Original PJSUA2 call ID is available for debugging purposes

## Structured Call Record Schema

On call disconnect, the bot writes one document that matches this mapping (example mapping shown; create in Elasticsearch if you need strict types):

```json
{
  "mappings": {
    "properties": {
      "call_id":        {"type":"keyword"},
      "caller_number":  {"type":"keyword"},
      "callee_ext":     {"type":"keyword"},
      "start_time":     {"type":"date"},
      "end_time":       {"type":"date"},
      "duration_sec":   {"type":"integer"},
      "status":         {"type":"keyword"},
      "direction":      {"type":"keyword"},
      "media":          {"type":"object","enabled": true},
      "bot":            {"type":"object","enabled": true},
      "host":           {"type":"keyword"},
      "ingest_ts":      {"type":"date"}
    }
  }
}
```

Fields populated by the bot on disconnect:

- `call_id`: **UUID-based unique identifier** (prevents duplicates across restarts)
- `caller_number`: parsed from remote SIP URI
- `callee_ext`: parsed from local SIP URI
- `start_time`, `end_time`: UTC ISO8601
- `duration_sec`: integer seconds (computed)
- `status`: `disconnected`
- `direction`: `inbound` (outbound support can be extended)
- `media`: `{ file_played, playback_started, playback_finished }`
- `bot`: `{ auto_answer, domain, user }`
- `host`: machine hostname
- `ingest_ts`: set at index time

**Note**: The `call_id` field now uses UUID format (e.g., `"550e8400-e29b-41d4-a716-446655440000"`) instead of sequential integers, ensuring uniqueness across program restarts and multiple bot instances.

## Testing Integration

Quick test script (connectivity and basic indexing checks):

```bash
python test_elasticsearch.py
```

Expected successful output includes cluster health and ✅ for each sample event type. Then, verify data in Kibana (`Discover`) using the index patterns above.


