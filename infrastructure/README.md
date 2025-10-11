# Asterisk VoIP Server - Docker Setup

A production-ready Asterisk VoIP server deployment using Docker Compose, designed for AI assistant telephony integration and testing environments.

## Quick Start

### Prerequisites

* Docker Engine 20.10+
* Docker Compose 2.0+
* Ports 5060, 8080, 10000-10099 available

### Installation

1. **Start the service**

```bash
docker-compose up -d
```

3. **Verify it's running**

```bash
docker-compose ps
docker-compose exec asterisk asterisk -rx "core show version"
```

## Configuration

### Basic Settings

The default configuration includes:

| Parameter    | Value       | Description           |
| ------------ | ----------- | --------------------- |
| SIP UDP Port | 5060        | Standard SIP protocol |
| SIP TCP Port | 5060        | TCP-based SIP         |
| SIP TLS Port | 5061        | Secure SIP            |
| RTP Ports    | 10000-10099 | Media streams         |
| WebSMS Port  | 8080        | SMS interface         |

### Environment Variables

Edit `docker-compose.yml` to customize:

```yaml
environment:
  - SYSLOG_LEVEL=5          # 1-8 (8=debug)
  - TLS_KEYBITS=2048        # TLS key strength
  - TLS_CERTDAYS=365        # Certificate validity
  - TZ=Asia/Tehran          # Your timezone
```

## Managing Extensions

### View Existing Extensions

```bash
docker-compose exec asterisk asterisk -rx "pjsip show endpoints"
```

### Create a New Extension

1. **Access the container**

```bash
docker-compose exec asterisk sh
```

2. **Edit configuration**

```bash
vi /srv/etc/asterisk/pjsip_endpoint.conf
```

3. **Add extension configuration**

```ini
[1001]
type=endpoint
context=internal
allow=!all,ulaw,alaw,g722
auth=1001
aors=1001

[1001]
type=auth
auth_type=userpass
password=SecurePassword123
username=1001

[1001]
type=aor
max_contacts=3
```

4. **Reload configuration**

```bash
docker-compose exec asterisk asterisk -rx "core reload"
```

### Quick Extension Creation (via Makefile)

```bash
make create-extension
```

## AI Bot Integration

### Connection Details for Your Bot

Use these SIP credentials to connect your AI assistant:

| Field     | Value                              |
| --------- | ---------------------------------- |
| Server    | `YOUR_SERVER_IP`                 |
| Port      | `5060`(UDP/TCP) or `5061`(TLS) |
| Username  | `1001`(or your extension)        |
| Password  | As configured                      |
| Transport | UDP/TCP/TLS                        |
| Codec     | ulaw, alaw, g722                   |

### Example SIP Client Configuration

```python
# Python example using pjsua
import pjsua as pj

lib = pj.Lib()
lib.init()
transport = lib.create_transport(pj.TransportType.UDP)
lib.start()

acc_cfg = pj.AccountConfig()
acc_cfg.id = "sip:1001@YOUR_SERVER_IP"
acc_cfg.reg_uri = "sip:YOUR_SERVER_IP"
acc_cfg.auth_cred = [pj.AuthCred("*", "1001", "SecurePassword123")]

acc = lib.create_account(acc_cfg)
```

## Management Commands

Using the included Makefile:

```bash
make up          # Start services
make down        # Stop services
make restart     # Restart services
make logs        # View live logs
make cli         # Access Asterisk CLI
make status      # Show service status
make extensions  # List all extensions
make reload      # Reload configuration
make calls       # Show active calls
make destroy     # Remove everything (⚠️ destructive)
```

### Manual Commands

```bash
# Access Asterisk CLI
docker-compose exec asterisk asterisk -rvvv

# View endpoints
asterisk -rx "pjsip show endpoints"

# View active channels
asterisk -rx "core show channels"

# Reload dialplan
asterisk -rx "dialplan reload"

# Show SIP registrations
asterisk -rx "pjsip show registrations"
```

## Security Features

### AutoBan (Built-in IDS/IPS)

Automatically blocks IP addresses after repeated failed authentication attempts:

* Monitors SIP security events
* Uses nftables for blocking
* No additional configuration needed

### TLS/SRTP Support

Secure communication enabled by default:

* Self-signed certificate auto-generated
* Custom certificates supported
* SRTP media encryption available

### Best Practices

1. **Use strong passwords** (10+ characters, mixed case, numbers, symbols)
2. **Change default ports** if exposed to internet
3. **Enable TLS** for external connections
4. **Limit RTP port range** to reduce attack surface
5. **Regular updates** - pull latest image periodically

## Monitoring & Logs

### View Logs

```bash
# Real-time logs
docker-compose logs -f asterisk

# Last 100 lines
docker-compose logs --tail=100 asterisk

# Specific time range
docker-compose logs --since 1h asterisk
```

### Log Levels

Adjust `SYSLOG_LEVEL` in docker-compose.yml:

| Level | Description              |
| ----- | ------------------------ |
| 1     | Emergency only           |
| 4     | Error or worse (default) |
| 5     | Warning or worse         |
| 7     | Info or worse            |
| 8     | Debug (verbose)          |

### Health Check

```bash
# Check container health
docker-compose ps

# Manual health check
docker-compose exec asterisk asterisk -rx "core show uptime"
```

## Testing Internal Calls

### Using Zoiper Softphone

1. **Install Zoiper** on mobile/desktop
2. **Configure Account:**
   * Domain: `YOUR_SERVER_IP`
   * Username: `1001`
   * Password: `SecurePassword123`
   * Transport: `UDP`
3. **Create second extension** (1002)
4. **Make test call:** Dial `1002` from extension `1001`

### Test Call Flow

```
Extension 1001 → Asterisk Server → Extension 1002
     (Bot)                             (Test Client)
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs asterisk

# Check port conflicts
netstat -tuln | grep -E '5060|8080'

# Restart with clean state
docker-compose down && docker-compose up -d
```

### No Audio in Calls

**One-way audio:**

* Check NAT settings in `pjsip_endpoint.conf`
* Verify RTP ports are accessible
* Disable strict RTP learning

**No audio at all:**

* Check firewall rules
* Verify codec compatibility
* Review SDP negotiation in logs

### Registration Failures

```bash
# Check endpoint configuration
docker-compose exec asterisk asterisk -rx "pjsip show endpoint 1001"

# View authentication failures
docker-compose logs asterisk | grep "authentication"

# Check network connectivity
docker-compose exec asterisk ping YOUR_CLIENT_IP
```

### Common Issues

| Issue               | Solution                                  |
| ------------------- | ----------------------------------------- |
| Port already in use | Change port mapping in docker-compose.yml |
| Permission denied   | Check cap_add permissions                 |
| Codec mismatch      | Update allow= in endpoint config          |
| NAT issues          | Configure external_media_address          |

## Updating

```bash
# Pull latest image
docker-compose pull

# Restart with new image
docker-compose up -d
```

## Additional Resources

* [Asterisk Official Docs](https://wiki.asterisk.org/)
* [PJSIP Configuration Guide](https://wiki.asterisk.org/wiki/display/AST/Configuring+res_pjsip)
* [Docker Image Source](https://github.com/mlan/docker-asterisk)
* [SIP Protocol RFC 3261](https://tools.ietf.org/html/rfc3261)
