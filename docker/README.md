# Networka Docker Container

Simple Docker setup for the Networka network automation tool with essential network debugging tools and SSH access.

## Quick Start

1. **Build and run:**
   ```bash
   docker compose up -d
   ```

2. **Access via SSH:**
   ```bash
   ssh networka@localhost -p 2222
   # Password: networka
   ```

3. **Or enter container directly:**
   ```bash
   docker exec -it networka bash
   ```

4. **Use networka:**
   ```bash
   nw --help
   ```

## SSH Access (MANDATORY)

The container runs an SSH server for remote access:

**Connection:**
```bash
ssh networka@localhost -p 2222
```

**Default credentials:**
- Username: `networka`
- Password: `networka`

**Setup SSH keys:**
```bash
# Copy your public key to container
ssh-copy-id -p 2222 networka@localhost

# Or manually:
cat ~/.ssh/id_rsa.pub | ssh -p 2222 networka@localhost "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

**Change password:**
```bash
docker exec -it networka passwd networka
```

## Network Debugging Tools

Essential Linux network tools included:
- **Connectivity**: ping, traceroute, mtr
- **Packet Analysis**: tcpdump
- **Network Scanning**: nmap, arp-scan  
- **Protocol Analysis**: netstat, ss, netcat
- **DNS Tools**: dig, nslookup (dnsutils)
- **Network Config**: ip (iproute2), ifconfig (net-tools)
- **HTTP Tools**: curl, wget
- **Network Info**: whois
- **Terminal Multiplexer**: tmux

## Useful Aliases

```bash
myip           # Get public IP
localip        # Get local IP  
ports          # Show listening ports
scan           # nmap shortcut
trace          # traceroute shortcut
tcpdump-any    # Capture on all interfaces
arp-table      # Show ARP table
dig-short      # Dig with +short
mtr-report     # MTR in report mode
netstat-listen # Show listening processes
ss-listen      # Show listening sockets
```

## Data Persistence

All data is stored in `/app/data` volume:
- `config/` - Device definitions, groups, sequences
- `results/` - Command execution results  
- `backups/` - Device configuration backups
- `logs/` - Application logs

Data persists across container restarts.

## Environment Variables

Set in `.env` file or environment:

```bash
NW_USER_DEFAULT=admin
NW_PASSWORD_DEFAULT=yourpassword
TZ=America/New_York
```

## Build Only

```bash
docker build -f docker/Dockerfile -t networka .
docker run -it networka
```

## Platform Support

- Docker Desktop
- Podman Desktop
- DevContainers/DevPods
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
