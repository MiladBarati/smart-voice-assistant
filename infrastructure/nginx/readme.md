# Nginx Recordings Server

A lightweight, containerized solution for serving audio recordings via Nginx with Docker Compose.

## Prerequisites

* Docker Engine 20.10+
* Docker Compose 2.0+
* Existing Docker network: `elk-stack_elk`

## Quick Start

1. Create project directory with `nginx.conf` and `docker-compose.yml` files
2. Ensure your recordings directory exists and contains audio files
3. Run `docker-compose up -d`
4. Access recordings at `http://your-server:7070/recordings/`

## Directory Structure

Your recordings should follow this structure:

```
recordings/
├── 2025-10-29/
│   ├── call_20251029_142301_1001/
│   │   └── incoming.wav
│   └── call_20251029_153045_1002/
│       └── incoming.wav
└── 2025-10-30/
    └── call_20251030_091523_1003/
        └── incoming.wav
```

## Configuration

### Port Configuration

Default port is 7070. Change it in docker-compose.yml if needed.

### Supported Audio Formats

* WAV - Wave Audio
* MP3 - MPEG Audio
* OGG - Ogg Vorbis
* FLAC - Free Lossless Audio Codec

## Usage

### Access Recordings

**List all dates:**

```
http://your-server:7070/recordings/
```

**List recordings for a specific date:**

```
http://your-server:7070/recordings/2025-10-29/
```

**Access a specific recording:**

```
http://your-server:7070/recordings/2025-10-29/call_20251029_142301_1001/incoming.wav
```

### Security

### Basic Authentication

Add password protection by creating a `.htpasswd` file and mounting it in the container. Update nginx.conf to enable auth_basic.

### IP Whitelisting

Restrict access to specific IP addresses by modifying the nginx.conf location block with allow/deny directives.

### HTTPS/SSL

For production, use a reverse proxy like Nginx Proxy Manager, Traefik, or Caddy to add SSL/TLS encryption.

## Troubleshooting

### Container won't start

Check logs with `docker-compose logs nginx-recordings` and verify that the elk-stack_elk network exists.

### 404 Not Found errors

Verify that the recordings directory exists and is properly mounted. Check volume mounting with `docker inspect nginx-recordings`.

### Permission denied errors

Ensure the recordings directory has proper read permissions. Use `chmod -R 755 recordings/` if needed.

### Empty directory listing

Verify files exist inside the container with `docker exec nginx-recordings ls -la /usr/share/nginx/html/recordings/`.

## Maintenance

### View Logs

```bash
docker-compose logs -f
```

### Restart Server

```bash
docker-compose restart
```

### Update Nginx

```bash
docker-compose pull
docker-compose up -d
```

### Backup Recordings

Create regular backups of the recordings directory using tar or your preferred backup tool.

## API Reference

### Endpoints

**GET /health** - Health check endpoint, returns "healthy"

**GET /recordings/** - List all available recordings with directory browsing

**GET /recordings/{date}/{call_id}/{filename}** - Download or stream a specific recording

### Response Headers

* Content-Type: audio/wav
* Access-Control-Allow-Origin: *
* Cache-Control: public, max-age=3600
