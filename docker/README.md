# 🌐 Networka Docker Container

Production-ready Docker container for the Networka network automation tool with comprehensive network debugging capabilities and SSH access.

## 🚀 Quick Start

```bash
# 1. Start the container
docker compose -f docker/docker-compose.yml up -d

# 2. Access via SSH
ssh networka@localhost -p 2222
# Password: networka

# 3. Start automating!
nw --help
```

## 📋 What's Included

### ⚡ Network Automation
- **Networka CLI**: Full `nw` command suite for multi-vendor automation
- **SSH Fanout**: `nw ssh` for multi-device management with tmux
- **Device Management**: Comprehensive device, group, and sequence support
- **File Operations**: Upload/download capabilities

### 🛠️ Network Debugging Arsenal
- **Connectivity**: ping, traceroute, mtr
- **Packet Analysis**: tcpdump (with aliases)
- **Network Scanning**: nmap, arp-scan  
- **Protocol Analysis**: netstat, ss, netcat
- **DNS Tools**: dig, nslookup
- **Network Config**: ip (iproute2), ifconfig (net-tools)
- **HTTP Tools**: curl, wget
- **Network Info**: whois
- **Terminal Multiplexer**: tmux

### 🎯 Built-in Aliases
```bash
# Network Information
myip           # Get public IP
localip        # Get local IP  
ports          # Show listening ports

# Network Analysis
scan           # nmap shortcut
trace          # traceroute shortcut
dig-short      # dig +short
mtr-report     # mtr --report

# Packet Analysis
tcpdump-any    # tcpdump -i any
arp-table      # arp -a

# System Monitoring
netstat-listen # netstat -tlnp
ss-listen      # ss -tlnp

# Networka Shortcuts
nw-help        # nw --help
nw-devices     # nw list devices
nw-groups      # nw list groups
```

## 🔐 Access Methods

### SSH Access (Recommended)
```bash
# Connect via SSH
ssh networka@localhost -p 2222
# Default password: networka

# Setup SSH keys for passwordless access
ssh-copy-id -p 2222 networka@localhost
```

### Direct Container Access
```bash
# Direct shell access
docker exec -it networka bash

# Run single commands
docker exec -it networka nw list devices
```

## 💾 Data Persistence

All data persists in the `networka_data` Docker volume:

```
/app/data/
├── config/     # Device definitions, groups, sequences
├── results/    # Command execution results
├── backups/    # Device configuration backups
└── logs/       # Application logs
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Device credentials
NW_USER_DEFAULT=admin
NW_PASSWORD_DEFAULT=your-password

# Container settings
TZ=America/New_York
```

### Device Configuration

Configure your devices in `/app/data/config/devices.yml`:

```yaml
devices:
  router1:
    host: "192.168.1.1"
    device_type: "mikrotik_routeros"
    platform: "arm"
    
  switch1:
    host: "192.168.1.10"
    device_type: "cisco_ios"
    platform: "cisco"

device_groups:
  infrastructure:
    - router1
    - switch1
```

## 🔧 Common Usage Examples

### Device Operations
```bash
# Device information
nw info router1

# Execute commands
nw run router1 "/system resource print"
nw run switch1 "show version"

# File operations
nw upload router1 firmware.npk
nw download switch1 startup-config.txt

# Backup configurations
nw backup router1
nw backup all
```

### Network Debugging
```bash
# Test connectivity
ping 192.168.1.1
trace google.com
mtr-report 8.8.8.8

# Network scanning
scan -sT 192.168.1.0/24
arp-table

# Packet capture
tcpdump-any host 192.168.1.1

# DNS analysis
dig-short google.com
```

### SSH Fanout (Multi-device)
```bash
# SSH to multiple devices with tmux
nw ssh infrastructure  # SSH to device group
nw ssh router1 switch1 # SSH to specific devices

# Commands are synchronized across all panes
# Ctrl+B then T to toggle synchronization
```

## 🐳 Container Management

### Build from Source
```bash
git clone https://github.com/narrowin/networka.git
cd networka
docker compose -f docker/docker-compose.yml build
```

### Update Container
```bash
docker compose -f docker/docker-compose.yml pull
docker compose -f docker/docker-compose.yml up -d
```

### View Logs
```bash
docker compose -f docker/docker-compose.yml logs -f
```

### Container Status
```bash
docker compose -f docker/docker-compose.yml ps
```

## 🚨 Troubleshooting

### Container Won't Start
```bash
# Check logs
docker compose -f docker/docker-compose.yml logs

# Verify system
docker --version
docker compose --version
```

### SSH Connection Issues
```bash
# Test SSH service
docker exec networka systemctl status ssh

# Check port mapping
docker port networka

# Reset password
docker exec -it networka passwd networka
```

### Network Connectivity Issues
```bash
# Test from container
docker exec networka ping 8.8.8.8

# Check host networking
ping 8.8.8.8
```

### Permission Issues
```bash
# Fix data permissions
docker exec networka sudo chown -R networka:networka /app/data
```

## 🔒 Security

- **Non-root execution**: All operations run as `networka` user
- **SSH hardening**: Root login disabled, secure configuration
- **Minimal attack surface**: Only essential packages installed
- **Data isolation**: User data in dedicated volume
- **Environment-based credentials**: No hardcoded passwords

## 📚 Additional Resources

- **Networka Documentation**: [https://narrowin.github.io/networka/](https://narrowin.github.io/networka/)
- **Docker Compose Reference**: [https://docs.docker.com/compose/](https://docs.docker.com/compose/)
- **Network Debugging Guide**: See container's welcome message

## 🆘 Support

For issues and questions:
1. Check container logs: `docker compose logs`
2. Review troubleshooting section above
3. Visit project documentation
4. Open GitHub issue with logs and configuration
    platform: "arm"
  
  switch1:
    host: "192.168.1.10"  
    device_type: "cisco_ios"
    platform: "cisco"
```

### 4. Start Network Automation
```bash
# Test device connectivity
nw info router1

# Run commands
nw run router1 "/system resource print"
nw run switch1 "show version"

# Backup configurations
nw backup router1
```

## 🛠️ Container Features

### Network Automation Tools
- **Networka CLI** with full bash completion
- **Pre-configured** devices, groups, and sequences
- **Results persistence** across container restarts
- **SSH key integration** from host system

### Network Debugging Arsenal
- **Packet Analysis**: tcpdump, wireshark-common
- **Network Scanning**: nmap, arp-scan  
- **Connectivity Testing**: ping, traceroute, mtr
- **Protocol Analysis**: netstat, ss, netcat
- **DNS Tools**: dig, nslookup, host
- **HTTP Tools**: curl, wget
- **Network Utilities**: ip, iproute2, net-tools

### Pre-installed Aliases
```bash
# Networka shortcuts
nw-info, nw-run, nw-list, nw-backup

# Network debugging
myip, localip, ports, scan, trace
tcpdump-eth0, arp-table, dig-short

# System utilities  
ll, la, tree, top
```

## 📁 Volume Mounts Explained

### Configuration Mount
```yaml
./config:/app/config:rw
```
- **Purpose**: Device configurations, groups, command sequences
- **Persistence**: Survives container restarts  
- **Access**: Edit from host or container

### Results Mount
```yaml
./results:/app/results:rw
```
- **Purpose**: Command outputs, backups, logs
- **Persistence**: All automation results saved permanently
- **Access**: View results on host computer

### SSH Keys Mount
```yaml
~/.ssh:/home/networka/.ssh:ro
```
- **Purpose**: Use your existing SSH keys for device auth
- **Security**: Read-only, keys stay on host
- **Benefit**: No key copying needed

## 🔧 Usage Examples

### Network Device Operations
```bash
# Device information
nw info router1

# Execute commands
nw run switch1 "show ip interface brief"
nw run router1 "/interface print"

# File operations
nw upload router1 firmware.npk
nw download switch1 startup-config.txt

# Bulk operations
nw run all "show version"
nw backup all
```

### Network Debugging
```bash
# Connectivity testing
ping 192.168.1.1
traceroute google.com
mtr --report 8.8.8.8

# Network scanning
nmap -sT 192.168.1.0/24
arp-scan --local

# Packet capture
tcpdump -i eth0 host 192.168.1.1
tcpdump-eth0

# DNS analysis  
dig google.com
nslookup github.com
```

### Container Management
```bash
# View logs
docker-compose logs networka

# Restart container
docker-compose restart

# Update to latest version
docker-compose pull
docker-compose up -d

# Stop container
docker-compose down
```

## 🌍 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NW_USER_DEFAULT` | `admin` | Default username for device connections |
| `NW_PASSWORD_DEFAULT` | _(empty)_ | Default password for device connections |
| `TZ` | `UTC` | Container timezone |

## 🔐 Security Features

- **Non-root execution** (networka user)
- **Read-only SSH key mount** 
- **Minimal attack surface**
- **Network capabilities** only for debugging tools
- **Environment variable** credential management

## 🚨 Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose logs networka

# Verify Docker daemon
docker --version
docker ps

# Check system resources
docker system df
```

### Can't Connect to Devices
```bash
# Test network connectivity
docker-compose exec networka ping 192.168.1.1

# Check SSH keys
docker-compose exec networka ls -la ~/.ssh/

# Test from host
ping 192.168.1.1
```

### Bash Completions Not Working
```bash
# Reload completions
docker-compose exec networka bash
source ~/.bashrc

# Manual completion setup
eval "$(nw --show-completion bash)"
```

### Credentials Issues
```bash
# Check environment variables
docker-compose exec networka env | grep NW_

# Update credentials
echo "NW_PASSWORD_DEFAULT=newpassword" >> .env
docker-compose restart
```

## 🔄 Updates and Maintenance

### Update Container
```bash
# Pull latest version
docker-compose pull

# Restart with new image
docker-compose up -d

# Verify version
docker-compose exec networka nw --version
```

### Backup Your Data
```bash
# Backup configurations
tar -czf networka-config-backup.tar.gz config/

# Backup results
tar -czf networka-results-backup.tar.gz results/
```

### Container Registry
- **Primary**: `ghcr.io/narrowin/networka:latest`
- **Versions**: `ghcr.io/narrowin/networka:v1.0.0`
- **Development**: `ghcr.io/narrowin/networka:main`

## 🎯 Advanced Configuration

### Custom Network Mode
```yaml
# For isolated testing
services:
  networka:
    networks:
      - management
    ports:
      - "2222:22"

networks:
  management:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
```

### Resource Limits
```yaml
services:
  networka:
    mem_limit: 2g
    cpus: '1.0'
```

---

## 📞 Support

- **Documentation**: [https://narrowin.github.io/networka/](https://narrowin.github.io/networka/)
- **Issues**: [GitHub Issues](https://github.com/narrowin/networka/issues)
- **Container Registry**: [GitHub Packages](https://github.com/narrowin/networka/pkgs/container/networka)

---

**Ready to automate your network? 🚀**
