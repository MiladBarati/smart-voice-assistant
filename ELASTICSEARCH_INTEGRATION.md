# Elasticsearch Integration for PJSUA2 Call Monitoring

This document describes the Elasticsearch integration added to the PJSUA2 call bot for comprehensive call monitoring and logging.

## Overview

The integration adds structured logging of all call events, registration events, and media events to Elasticsearch, allowing for:
- Real-time call monitoring
- Call analytics and reporting
- Troubleshooting and debugging
- Performance monitoring

## Configuration

### Elasticsearch Connection

The integration connects to your Elasticsearch cluster with the following configuration:
- **Host**: 185.243.48.247
- **Port**: 9200
- **Username**: elastic
- **Password**: h2xzKBNaD2Qub5zVE12
- **SSL**: Enabled
- **Certificate Verification**: Disabled

### Index Structure

Data is stored in a single unified index:

- `pjsua-calls` - Contains all events (registration, call, media, call records)

## Event Types

### Call Events
- `incoming_call` - Incoming call received
- `call_answered` - Call answered (200 OK)
- `call_ringing` - Call ringing (180 Ringing)
- `call_connected` - Call connected
- `call_disconnected` - Call disconnected
- `call_state_change` - Any call state change
- `outbound_call` - Outbound call initiated
- `call_error` - Call error occurred

### Registration Events
- `registration_success` - Successful registration
- `registration_failed` - Registration failed
- `registration_attempt` - Registration attempt

### Media Events
- `media_active` - Media stream active
- `playback_started` - Audio playback started
- `playback_finished` - Audio playback finished
- `audio_bridged` - Audio bridged to sound device
- `media_error` - Media error occurred

## Data Structure

### Call Event Document
```json
{
  "@timestamp": "2024-01-15T10:30:00.000Z",
  "event_type": "incoming_call",
  "call_id": "12345",
  "call_state": "ringing",
  "call_code": 180,
  "remote_uri": "sip:caller@example.com",
  "local_uri": "sip:user@domain.com",
  "duration": 5.5,
  "host": "185.243.48.247",
  "service": "pjsua2",
  "additional_data": {
    "auto_answer": true
  }
}
```

### Registration Event Document
```json
{
  "@timestamp": "2024-01-15T10:30:00.000Z",
  "event_type": "registration_success",
  "user": "username",
  "domain": "domain.com",
  "status": "OK",
  "code": 200,
  "host": "185.243.48.247",
  "service": "pjsua2"
}
```

### Media Event Document
```json
{
  "@timestamp": "2024-01-15T10:30:00.000Z",
  "event_type": "playback_started",
  "call_id": "12345",
  "media_type": "audio",
  "media_status": "active",
  "file_played": "welcome_message.wav",
  "host": "185.243.48.247",
  "service": "pjsua2"
}
```

## Usage

### Running with Elasticsearch Logging

The integration is automatically enabled when running the register_bot.py script. No additional configuration is required.

```bash
python register_bot.py --user username --password password --domain domain.com --stay-online
```

### Testing the Integration

Run the test script to verify Elasticsearch connectivity and logging:

```bash
python test_elasticsearch.py
```

This will:
1. Test the Elasticsearch connection
2. Log sample events of each type
3. Verify successful logging

### Viewing Data in Kibana

1. Access Kibana at: https://kibana.aminraay.ir
2. Login with the provided credentials
3. Create index pattern for:
   - `pjsua-calls`
4. Explore the data in the Discover section

## Monitoring and Alerts

### Key Metrics to Monitor
- Call success/failure rates
- Registration status
- Media playback success
- Call duration statistics
- Error rates

### Sample Kibana Queries

**All calls in the last hour:**
```
event_type:call_* AND @timestamp:[now-1h TO now]
```

**Failed registrations:**
```
event_type:registration_failed
```

**Calls with errors:**
```
event_type:call_error OR event_type:media_error
```

**Call duration analysis:**
```
event_type:call_disconnected AND duration:>0
```

## Troubleshooting

### Connection Issues
- Verify Elasticsearch cluster is running
- Check network connectivity to 185.243.48.247:9200
- Verify credentials are correct
- Check SSL/TLS configuration

### Logging Issues
- Check Python logs for Elasticsearch errors
- Verify index permissions
- Check disk space on Elasticsearch cluster
- Monitor Elasticsearch cluster health

### Performance Considerations
- Logs are sent asynchronously to avoid blocking call processing
- Failed log writes don't affect call functionality
- Consider log rotation and retention policies
- Monitor Elasticsearch cluster performance

## Files Modified

1. **pyproject.toml** - Added elasticsearch dependency
2. **elasticsearch_client.py** - New Elasticsearch client module
3. **register_bot.py** - Integrated logging throughout call flow
4. **test_elasticsearch.py** - Test script for integration
5. **ELASTICSEARCH_INTEGRATION.md** - This documentation

## Dependencies

- `elasticsearch>=8.0.0` - Elasticsearch Python client
- `pjsua2` - PJSUA2 library (native)

## Security Notes

- Credentials are hardcoded for simplicity - consider using environment variables in production
- SSL verification is disabled - enable for production use
- Consider implementing proper authentication and authorization
- Monitor access logs for security

## Future Enhancements

- Configurable Elasticsearch settings via command line
- Environment variable support for credentials
- Custom log formatting and filtering
- Real-time dashboards
- Automated alerting
- Call quality metrics
- Integration with other monitoring tools

