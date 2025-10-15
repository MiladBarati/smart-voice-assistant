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

1. **Start the services** :

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
   https://pbx.aminraay.ir/
   ```
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

## Fail2Ban

Create a new Fail2Ban jail for Asterisk
```bash
sudo vi /etc/fail2ban/jail.d/asterisk.conf
```
adding the following content:
```bash
[asterisk-iptables]
enabled = true
filter = asterisk
action = iptables-allports[name=asterisk, protocol=all]
logpath = /var/log/asterisk/full
maxretry = 3
findtime = 300
bantime = 86400
```
Save the file, then restart Fail2Ban:
```bash
sudo systemctl restart fail2ban
sudo fail2ban-client status
sudo fail2ban-client status asterisk-iptables
```