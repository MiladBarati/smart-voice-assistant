# FreePBX Docker Deployment

## Overview

This Docker Compose configuration deploys a complete FreePBX telephony system with a separate MariaDB database. FreePBX is an open-source telecommunications system that allows you to create and manage a PBX (Private Branch Exchange) for handling voice calls, extensions, and SIP trunks.

The setup includes:

* **FreePBX Application** : The main PBX management interface and call handling system
* **MariaDB Database** : Persistent storage for FreePBX configuration and data
* **Persistent Volumes** : Configuration, logs, SSL certificates, and database data are stored in Docker volumes for data persistence

## Prerequisites

* Docker and Docker Compose installed
* A server with sufficient resources (recommended: 2+ CPU cores, 4GB+ RAM)
* An external network connection if accessing remotely
* Ports 80, 443, and 5060-5061 (SIP) should be available

## Installation & Running

1. **Clone or download** this Docker Compose file to your server
2. **Update configuration** (optional but recommended):
   * Change `VIRTUAL_HOST=hostname.example.com` to your actual domain or IP
   * Update database credentials for security:
     * `MYSQL_ROOT_PASSWORD`
     * `DB_PASS` and `MYSQL_PASSWORD` (should match)
3. **Start the services** :

```bash
   docker-compose up -d
```

1. **Wait for initialization** : The first startup may take 2-3 minutes as FreePBX initializes and configures the database
2. **Verify services are running** :

```bash
   docker-compose ps
```

Both `freepbx-app` and `freepbx-db` containers should show as "running"

## Accessing the FreePBX Admin Panel

1. **Open your browser** and navigate to:

   ```
   http://YOUR_SERVER_IP/admin
   ```

   Replace `YOUR_SERVER_IP` with your server's actual IP address
2. **Default credentials** :

* Username: `admin`
* Password: `admin` (change this immediately after first login)

1. **First login** : Accept the license agreement and complete the initial setup wizard

## Creating Extensions (Internal Phones)

Once logged into the FreePBX admin panel:

1. Navigate to **Connectivity → Extensions** (or **Applications → Extensions** depending on FreePBX version)
2. Click **Add Extension** button
3. Select **Generic SIP Device** as the extension type
4. Configure the extension:
   * **Display Name** : Give it a descriptive name (e.g., "Office Phone")
   * **Extension/User ID** : Assign a number (e.g., 100, 101, etc.)
   * Leave other settings at defaults or customize as needed
5. Click **Submit** and then **Apply Config** button at the top right
6. **Configure your SIP phone/application** :

* Server/PBX: Your server's IP or domain
* Username/Extension: The number you created
* Password: Will be displayed in the extension details
* Port: 5060 (default SIP port)

1. Register your phone/app with these credentials

## Stopping and Managing Services

* **Stop services** :

```bash
  docker-compose down
```

* **View logs** :

```bash
  docker-compose logs -f freepbx-app
```

* **Restart services** :

```bash
  docker-compose restart
```

## Accessing the Container Shell

To execute commands inside the FreePBX container or view detailed logs:

1. **SSH into your server** first:
   ```bash
   ssh user@your_server_ip
   ```
2. **Enter the FreePBX container** :

```bash
   sudo docker exec -it freepbx-app bash
```

1. **Now you can run commands inside the container** , such as:

* View real-time Asterisk logs:
  ```bash
  tail -f /var/log/asterisk/full
  ```
* Check Asterisk status:
  ```bash
  asterisk -rv
  ```
* View FreePBX logs:
  ```bash
  tail -f /var/log/fop2/fop2.log
  ```
* List active SIP channels:
  ```bash
  asterisk -rx "sip show peers"
  ```

1. **Exit the container** :

```bash
   exit
```

## Troubleshooting

* **Can't access admin panel** : Verify firewall allows port 80/443, check if containers are running with `docker-compose ps`
* **Extensions not connecting** : Ensure RTP ports (18000-18100) are not blocked by firewall. Check Asterisk logs with `tail -f /var/log/asterisk/full`
* **Database connection errors** : Verify `DB_HOST` IP is accessible and database credentials match in both services
* **Fail2ban issues** : Fail2ban is enabled by default; disable with `ENABLE_FAIL2BAN=FALSE` if causing problems
* **Check SIP registration** : Inside the container, run `asterisk -rx "sip show peers"` to see connected extensions

## Additional Resources

* FreePBX Documentation: https://docs.freepbx.org/
* Asterisk SIP Configuration: https://www.asterisk.org/
