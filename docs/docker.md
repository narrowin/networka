# Docker Container

Docker container for Networka with comprehensive network debugging capabilities.

## Quick Start

Pull and run the latest container from GitHub Container Registry:

```bash
# Pull the latest version
docker pull ghcr.io/narrowin/networka:latest

# Start with docker-compose (recommended)
wget https://raw.githubusercontent.com/narrowin/networka/main/docker/docker-compose.yml
docker compose up -d

# Or run directly
docker run -d --name networka \
  -p 2222:22 \
  -v networka_data:/app/data \
  ghcr.io/narrowin/networka:latest
```

## Container Access

Access the container via SSH (recommended) or direct shell:

```bash
# SSH access (password: networka)
ssh networka@localhost -p 2222

# Direct shell access
docker exec -it networka bash
```

## Initial Setup

The container provides the same starting point as a local installation:

```bash
# Inside container - initialize configuration
nw config init

# Follow prompts to set up your first device
# Configuration persists in /app/data volume
```

## Container Features

### Network Automation
- Full Networka CLI with all commands
- Multi-vendor device support
- Async execution capabilities
- Configuration backup and restore

### Network Debugging Tools
- **Connectivity**: ping, traceroute, mtr
- **Packet Analysis**: tcpdump with convenient aliases
- **Network Scanning**: nmap, arp-scan
- **Protocol Analysis**: netstat, ss, netcat
- **DNS Tools**: dig, nslookup
- **Network Config**: ip, ifconfig
- **HTTP Tools**: curl, wget
- **Network Info**: whois
- **Terminal Multiplexer**: tmux for SSH sessions

### Built-in Aliases
```bash
# Network information
myip           # Get public IP address
localip        # Get local IP address
ports          # Show listening ports

# Network analysis
scan           # Quick nmap scan
trace          # Traceroute with hostname resolution
dig-short      # DNS lookup with short output
mtr-report     # MTR network path analysis

# Packet capture
tcpdump-any    # Capture on all interfaces
arp-table      # Display ARP table

# System monitoring
netstat-listen # Show listening processes
ss-listen      # Show listening sockets with details

# Networka shortcuts
nw-help        # Quick help reference
nw-devices     # List configured devices
nw-groups      # List device groups
```

## Data Persistence

All data persists across container restarts in the `/app/data` volume:

```
/app/data/
├── config/     # Device definitions and groups
├── results/    # Command execution results
├── backups/    # Device configuration backups
└── logs/       # Application logs
```

## Configuration

### Environment Variables

Set credentials and configuration via environment variables:

```bash
# Device credentials
NW_USER_DEFAULT=admin
NW_PASSWORD_DEFAULT=your-password

# Container timezone
TZ=America/New_York
```

### Device Configuration

After running `nw config init`, edit your device configuration:

```yaml
# /app/data/config/devices.yml
devices:
  router1:
    host: "192.168.1.1" 
    device_type: "mikrotik_routeros"
    platform: "arm"
    description: "Main router"
    tags:
      - "router"
      - "critical"

groups:
  infrastructure:
    description: "Critical infrastructure"
    match_tags:
      - "critical"
```

## Container Management

### Using Docker Compose (Recommended)

```bash
# Download compose file
wget https://raw.githubusercontent.com/narrowin/networka/main/docker/docker-compose.yml

# Start container
docker compose up -d

# View logs
docker compose logs -f

# Update to latest version
docker compose pull
docker compose up -d

# Stop container
docker compose down
```

### Using Docker CLI

```bash
# Run with volume persistence
docker run -d --name networka \
  --hostname networka \
  -p 2222:22 \
  -v networka_data:/app/data \
  -e TZ=America/New_York \
  ghcr.io/narrowin/networka:latest

# Update container
docker stop networka
docker rm networka
docker pull ghcr.io/narrowin/networka:latest
# Run command above again
```

## Usage Examples

### Basic Operations

```bash
# SSH into container
ssh networka@localhost -p 2222

# Initialize configuration
nw config init

# Check device status
nw info router1

# Execute commands
nw run router1 "/system resource print"
nw run infrastructure "show version"

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

# Network discovery
scan -sT 192.168.1.0/24
arp-table

# Packet analysis
tcpdump-any host 192.168.1.1

# DNS troubleshooting
dig-short example.com
nslookup example.com 8.8.8.8
```

### Multi-device SSH

```bash
# SSH to multiple devices simultaneously
nw ssh infrastructure  # Connect to device group
nw ssh router1 switch1 # Connect to specific devices

# Commands are synchronized across all sessions
# Use Ctrl+B then T to toggle synchronization
```

## SSH Key Authentication

For passwordless access, copy your SSH key to the container:

```bash
# Copy SSH key
ssh-copy-id -p 2222 networka@localhost

# Or manually
cat ~/.ssh/id_rsa.pub | ssh -p 2222 networka@localhost "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

## Container Versions

Container images are automatically built and tagged for each release:

- `ghcr.io/narrowin/networka:latest` - Latest stable release
- `ghcr.io/narrowin/networka:v1.2.3` - Specific version
- `ghcr.io/narrowin/networka:main` - Development branch

## Troubleshooting

### Container Won't Start

```bash
# Check container logs
docker logs networka

# Verify image
docker images | grep networka

# Check port conflicts
netstat -tlnp | grep 2222
```

### SSH Connection Issues

```bash
# Verify SSH service in container
docker exec networka systemctl status ssh

# Check port mapping
docker port networka

# Reset password
docker exec -it networka passwd networka
```

### Network Connectivity

```bash
# Test from container
docker exec networka ping 8.8.8.8

# Check DNS resolution
docker exec networka nslookup google.com
```

### Data Persistence Issues

```bash
# Check volume
docker volume inspect networka_data

# Fix permissions
docker exec networka sudo chown -R networka:networka /app/data
```

## Security

The container follows security best practices:

- **Non-root execution**: All operations run as `networka` user
- **SSH hardening**: Root login disabled, secure configuration
- **Minimal attack surface**: Only essential packages installed
- **Data isolation**: User data in dedicated Docker volume
- **Environment-based credentials**: No hardcoded passwords

## Support

For container-specific issues:

1. Check container logs: `docker logs networka`
2. Verify configuration: `/app/data/config/`
3. Test network connectivity from container
4. Review troubleshooting section above
5. Open [GitHub issue](https://github.com/narrowin/networka/issues) with logs
