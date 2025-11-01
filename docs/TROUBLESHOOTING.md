# Troubleshooting

Common issues and solutions for using the PJSUA2 SIP bot.

## Registration Fails

**Problem**: Registration timeout or 401/403 errors

**Solutions**:
- Verify credentials (`--user`, `--password`, `--auth-user`)
- Check if domain is correct (`--domain`)
- Try different transport (`--transport tcp` instead of udp)
- Increase wait time (`--wait-seconds 20`)
- Check firewall/NAT rules
- Increase log level (`--log-level 5`) for details

## Port Already in Use

**Problem**: `Transport creation error` or port binding failure

**Solutions**:
- Use a different port: `--local-port 5070`
- Kill existing process using the port
- On Linux: `sudo lsof -i :5060` to find process

## Audio Not Playing

**Problem**: No audio heard on remote side

**Solutions**:
- Ensure WAV file format is correct (8kHz/16kHz, mono, 16-bit PCM)
- Verify file path is correct and accessible
- Check that call media state becomes `ACTIVE` (look for "Media: playing file" log)
- Test with a simple beep/tone WAV file first
- Verify the bot shows "***WAV file duration: X seconds" at startup

## Audio Keeps Looping

**Problem**: Welcome message plays multiple times instead of once

**Solutions**:
- This should be fixed automatically - the bot stops player transmission after the detected duration
- Check logs for "***Stopped player transmission to prevent looping"
- Adjust `--message-duration` if the auto-detection is incorrect
- Ensure your WAV file is properly formatted (corrupted files may have incorrect duration metadata)

## Call Drops Immediately

**Problem**: Call connects then disconnects

**Solutions**:
- Check codec compatibility between endpoints
- Verify RTP/media ports are not blocked
- Try disabling ICE/STUN if behind complex NAT
- Increase log level to see detailed SIP/SDP negotiation

## TLS Handshake Fails

**Problem**: Registration fails when using `--transport tls`

**Solutions**:
- Ensure server supports TLS on the expected port (usually 5061)
- Try without `--tls-verify` if using self-signed certificates
- Check certificate validity and CA trust chain
- Verify server certificate includes correct hostname/IP

## Elasticsearch Connection Issues

**Problem**: Elasticsearch logging fails or connection errors

**Solutions**:
- Verify `.env` file exists and contains correct credentials
- Check Elasticsearch server is running and accessible
- Test connectivity: `python test_connectivity.py`
- Verify environment variables are loaded: `python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('ES_HOST:', os.getenv('ES_HOST'))"`
- Check firewall rules for Elasticsearch port (default 9200)
- Ensure `python-dotenv` is installed: `pip install python-dotenv`

**Common Error Messages**:
- `ModuleNotFoundError: No module named 'dotenv'` → Install python-dotenv
- `ConnectionError` → Check ES_HOST and ES_PORT in .env file
- `AuthenticationException` → Verify ES_USERNAME and ES_PASSWORD
- `SSLHandshakeError` → Set `ES_USE_SSL="false"` or fix SSL configuration

## Duplicate Call IDs (Fixed)

**Problem**: Call IDs starting from 0 on each restart causing duplicate entries

**Solution**: ✅ **Fixed in current version** - The bot now uses UUID-based call IDs that are globally unique across program restarts and multiple instances. Each call gets a unique identifier like `"550e8400-e29b-41d4-a716-446655440000"` instead of sequential numbers.


