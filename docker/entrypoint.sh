#!/bin/bash
set -e

# Start SSH daemon - MANDATORY
echo "Starting SSH daemon..."
service ssh start

# Create data subdirectories if they don't exist
mkdir -p /app/data/config
mkdir -p /app/data/results  
mkdir -p /app/data/backups
mkdir -p /app/data/logs

# Set proper permissions for networka user
chown -R networka:networka /app/data

# Initialize default config if it doesn't exist
if [ ! -f /app/data/config/devices.yml ]; then
    echo "Initializing default configuration..."
    if [ -f /app/config/devices.yml ]; then
        cp /app/config/*.yml /app/data/config/ 2>/dev/null || true
        chown -R networka:networka /app/data/config
    fi
fi

# Create useful network debugging aliases for root
cat >> /root/.bashrc << 'EOF'
# Network debugging aliases
alias myip='curl -s ifconfig.me'
alias localip='hostname -I'
alias ports='netstat -tuln'
alias scan='nmap'
alias trace='traceroute'
alias tcpdump-any='tcpdump -i any'
alias arp-table='arp -a'
alias dig-short='dig +short'
alias mtr-report='mtr --report'
alias netstat-listen='netstat -tlnp'
alias ss-listen='ss -tlnp'
EOF

# Create useful network debugging aliases for networka user
cat >> /home/networka/.bashrc << 'EOF'
# Network debugging aliases
alias myip='curl -s ifconfig.me'
alias localip='hostname -I'
alias ports='netstat -tuln'
alias scan='nmap'
alias trace='traceroute'
alias tcpdump-any='tcpdump -i any'
alias arp-table='arp -a'
alias dig-short='dig +short'
alias mtr-report='mtr --report'
alias netstat-listen='netstat -tlnp'
alias ss-listen='ss -tlnp'
EOF

# Welcome message
echo "Networka Docker Container with SSH Access"
echo "Data directory: /app/data"
echo "SSH: ssh networka@localhost -p 2222 (password: networka)"
echo "Direct: docker exec -it networka bash"
echo "Type 'nw --help' to get started"
echo "Network tools: ping, traceroute, tcpdump, nmap, dig, netstat, ss, mtr, tmux"

exec "$@"
   nw config init              - Initialize configuration
   nw run <device> <command>   - Execute command

💡 USEFUL ALIASES:
   nw-config, nw-results, nw-logs, nw-backups

🔧 CONFIGURATION:
   Set NW_USER_DEFAULT and NW_PASSWORD_DEFAULT environment 
   variables for default device credentials.

📖 DOCUMENTATION:
   Visit: https://narrowin.github.io/networka/

=================================================================
EOF

# Show container info on login
if [ "$1" = "bash" ]; then
    echo
    cat /app/.container-info
    echo
fi

# Execute the command
exec "$@"
alias trace='traceroute'
alias trace6='traceroute6'
alias dig-short='dig +short'
alias nslookup-short='nslookup'

# Network scanning and analysis
alias scan='nmap'
alias scan-local='nmap -sT 192.168.1.0/24'
alias scan-ports='nmap -sT'
alias arp-table='arp -a'
alias arp-scan-local='arp-scan --local'

# Packet capture
alias tcpdump-eth0='tcpdump -i eth0'
alias tcpdump-any='tcpdump -i any'
alias tcpdump-verbose='tcpdump -v'

# Network utilities
alias nc='netcat'
alias wget-debug='wget -v'
alias curl-debug='curl -v'
alias mtr-report='mtr --report'

# === SYSTEM UTILITIES ===
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias grep='grep --color=auto'
alias tree='tree -C'
alias top='htop'

# === NETWORKA ENVIRONMENT ===
alias show-config='ls -la /app/config/'
alias show-results='ls -la /app/results/'
alias edit-devices='nano /app/config/devices/devices.yml'
alias edit-config='nano /app/config/config.yml'
alias tail-logs='tail -f /app/logs/*.log'
EOF

# Create a comprehensive welcome message
cat > /home/networka/.welcome << 'EOF'
================================================================
    NETWORKA - Network Automation & Debugging Workstation
================================================================

🚀 NETWORKA COMMANDS:
   nw info <device>              - Get device information  
   nw run <device> <command>     - Execute command on device
   nw list-devices              - Show all configured devices
   nw list-groups               - Show device groups
   nw list-sequences            - Show available command sequences
   nw backup <device>           - Backup device configuration
   nw upload <device> <file>    - Upload file to device
   nw download <device> <file>  - Download file from device

CONFIGURATION:
   /app/config/devices/         - Device definitions
   /app/config/groups/          - Device groups  
   /app/config/sequences/       - Command sequences
   /app/results/                - Command results & backups
   
NETWORK DEBUGGING TOOLS:
   tcpdump, nmap, traceroute, mtr, netstat, ss, ip, dig
   ping, arping, netcat, telnet, curl, wget, whois
   
QUICK ALIASES:
   nw-info, nw-run, nw-list     - Networka shortcuts
   myip, localip, ports        - Network status
   scan, trace, dig-short      - Network analysis
   tcpdump-eth0, arp-table     - Packet analysis

HELP:
   nw --help                   - Full Networka documentation
   nw <command> --help         - Command-specific help
   alias                       - Show all available aliases

GET STARTED:
   1. Edit device config: edit-devices
   2. Test connection: nw info <device-name>
   3. Run commands: nw run <device> <command>

================================================================
EOF

# Ensure bash completions are loaded
if [ ! -f "/home/networka/.bash_completion_loaded" ]; then
    echo "Setting up bash completions..."
    
    # Source bash completion
    if [ -f /etc/bash_completion ]; then
        source /etc/bash_completion
    fi
    
    # Ensure networka completions are available
    if command -v nw &> /dev/null; then
        eval "$(nw --show-completion bash)" 2>/dev/null || echo "Note: Bash completions will be available after first nw command"
    fi
    
    touch /home/networka/.bash_completion_loaded
fi

# Show welcome message on interactive shells
if [ -t 1 ]; then
    cat /home/networka/.welcome
    echo ""
    echo "Current working directory: $(pwd)"
    echo "Container status: Ready"
    echo "Time: $(date)"
    echo ""
    
    # Show quick status
    if [ -f "/app/config/devices/devices.yml" ]; then
        device_count=$(grep -c "host:" /app/config/devices/devices.yml 2>/dev/null || echo "0")
    echo "Configured devices: $device_count"
    else
    echo "No devices configured yet - run 'edit-devices' to get started"
    fi
    
    echo ""
    echo "Type 'nw --help' for full documentation or use tab completion!"
    echo "================================================================"
    echo ""
fi

# Validate networka installation
if ! command -v nw &> /dev/null; then
    echo "ERROR: Networka command 'nw' not found in PATH"
    echo "PATH: $PATH"
    exit 1
fi

# Test basic functionality
if ! nw --help > /dev/null 2>&1; then
    echo "ERROR: Networka command failed basic test"
    exit 1
fi

echo "Networka container initialization complete!"

# Optionally start SSH server if requested
if [ "${ENABLE_SSH:-0}" = "1" ]; then
    echo "Starting sshd..."
    sudo /usr/sbin/sshd -D &
fi

# Execute the command
exec "$@"
