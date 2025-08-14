# Real-World Example: Multi-Site Network Configuration

This example demonstrates a realistic network configuration for a company with multiple sites using the enhanced configuration system.

## Scenario

**Company**: TechCorp with 3 sites
- **Headquarters**: Main office with core infrastructure
- **Branch Office**: Smaller office with access switches
- **Lab Environment**: Testing and development equipment

## Directory Structure

```
config/
├── config.yml
├── devices/                 # All device definitions
│   ├── core-infrastructure.yml     # Shared core infrastructure
│   ├── headquarters.yml            # HQ-specific devices
│   ├── branch-office.csv           # Branch office bulk import
│   └── lab-equipment.csv           # Lab devices from inventory
├── groups/                  # All group definitions
│   ├── core-groups.yml             # Infrastructure groups
│   ├── site-groups.yml             # Site-based groups
│   └── operational.csv             # Operational groups
└── sequences/               # All sequence definitions
    ├── common-sequences.yml        # Common sequences
    ├── monitoring.yml              # Complex monitoring sequences
    └── maintenance.csv             # Simple maintenance tasks
```

## Configuration Files

### Main Configuration (config.yml)
```yaml
general:
  timeout: 30
  results_dir: "./results"
  backup_dir: "./backups"
  output_mode: "dark"
  
# Default connection settings
transport: "ssh"
port: 22
connection_retries: 3
retry_delay: 5
```

### Core Infrastructure (devices/core-infrastructure.yml)
```yaml
devices:
  # Core infrastructure shared across all sites
  fw-main:
    host: "10.0.0.1"
    device_type: "mikrotik_routeros"
    description: "Main Firewall - HQ"
    model: "CCR2004-16G-2S+"
    location: "HQ Data Center"
    tags:
      - "firewall"
      - "critical"
      - "headquarters"
      - "edge"
  
  sw-core-01:
    host: "10.0.1.1"
    device_type: "mikrotik_routeros"
    description: "Core Switch 1 - HQ"
    model: "CRS354-48G-4S+2Q+"
    location: "HQ Data Center Rack A"
    tags:
      - "switch"
      - "core"
      - "critical"
      - "headquarters"
```

### Headquarters Equipment (devices/headquarters.yml)
```yaml
devices:
  sw-hq-floor1:
    host: "10.0.1.10"
    device_type: "mikrotik_routeros"
    description: "HQ Floor 1 Access Switch"
    model: "CRS326-24G-2S+"
    location: "HQ Floor 1 IDF"
    tags:
      - "switch"
      - "access"
      - "headquarters"
      - "floor1"
  
  sw-hq-floor2:
    host: "10.0.1.11"
    device_type: "mikrotik_routeros"
    description: "HQ Floor 2 Access Switch"
    model: "CRS326-24G-2S+"
    location: "HQ Floor 2 IDF"
    tags:
      - "switch"
      - "access"
      - "headquarters"
      - "floor2"
  
  ap-hq-lobby:
    host: "10.0.2.10"
    device_type: "mikrotik_routeros"
    description: "HQ Lobby Wireless AP"
    model: "cAP ac"
    location: "HQ Lobby"
    tags:
      - "wireless"
      - "access"
      - "headquarters"
      - "public"
```

### Branch Office Devices (devices/branch-office.csv)
```csv
name,host,device_type,description,platform,model,location,tags
sw-branch-main,10.1.0.1,mikrotik_routeros,Branch Office Main Switch,mipsbe,CRS326-24G-2S+,Branch Office IDF,switch;access;branch;critical
ap-branch-office,10.1.2.1,mikrotik_routeros,Branch Office Wireless AP,arm,cAP ac,Branch Office Ceiling,wireless;access;branch
sw-branch-conference,10.1.0.2,mikrotik_routeros,Branch Conference Room Switch,mipsbe,CRS309-1G-8S+,Branch Conference Room,switch;access;branch;conference
rtr-branch-edge,10.1.0.254,mikrotik_routeros,Branch Office Edge Router,arm,RB4011iGS+,Branch Office IDF,router;edge;branch;critical
```

### Lab Equipment (devices/lab-equipment.csv)
```csv
name,host,device_type,description,platform,model,location,tags
sw-lab-01,192.168.100.1,mikrotik_routeros,Lab Test Switch 1,mipsbe,CRS326-24G-2S+,Lab Rack 1,switch;access;lab;test
sw-lab-02,192.168.100.2,mikrotik_routeros,Lab Test Switch 2,mipsbe,CRS326-24G-2S+,Lab Rack 1,switch;access;lab;test
rtr-lab-edge,192.168.100.254,mikrotik_routeros,Lab Edge Router,arm,RB4011iGS+,Lab Rack 2,router;edge;lab;test
fw-lab-test,192.168.100.253,mikrotik_routeros,Lab Test Firewall,x86,CCR1009-7G-1C-1S+,Lab Rack 2,firewall;lab;test
ap-lab-wireless,192.168.100.10,mikrotik_routeros,Lab Wireless Test AP,arm,cAP ac,Lab Ceiling,wireless;lab;test
```

### Core Groups (groups/core-groups.yml)
```yaml
groups:
  all_firewalls:
    description: "All firewall devices across all sites"
    match_tags:
      - "firewall"
  
  critical_infrastructure:
    description: "Mission-critical devices requiring priority support"
    match_tags:
      - "critical"
  
  wireless_infrastructure:
    description: "All wireless access points"
    match_tags:
      - "wireless"
```

### Site-Based Groups (groups/site-groups.yml)
```yaml
groups:
  headquarters_all:
    description: "All headquarters equipment"
    match_tags:
      - "headquarters"
  
  branch_office_all:
    description: "All branch office equipment"
    match_tags:
      - "branch"
  
  lab_environment:
    description: "Lab and testing equipment"
    match_tags:
      - "lab"
  
  headquarters_access:
    description: "HQ access layer switches"
    match_tags:
      - "headquarters"
      - "access"
  
  branch_critical:
    description: "Critical branch office infrastructure"
    match_tags:
      - "branch"
      - "critical"
```

### Operational Groups (groups/operational.csv)
```csv
name,description,members,match_tags
backup_priority_high,High priority backup devices,,critical
backup_priority_normal,Normal priority backup devices,,switch;router
monitoring_24x7,24/7 monitored devices,,critical;core
maintenance_weekend,Weekend maintenance window devices,,access;lab
edge_devices,All edge devices (routers and firewalls),,edge
access_switches,All access layer switches,,access
```

### Common Sequences (sequences/common-sequences.yml)
```yaml
sequences:
  health_check:
    description: "Comprehensive device health check"
    commands:
      - "/system/resource/print"
      - "/system/health/print"
      - "/interface/print stats"
      - "/ip/route/print count-only"
    tags:
      - "monitoring"
      - "health"
  
  security_audit:
    description: "Security configuration review"
    commands:
      - "/user/print"
      - "/ip/service/print"
      - "/ip/firewall/filter/print"
      - "/system/logging/print where topics~firewall"
    tags:
      - "security"
      - "audit"
```

### Monitoring Sequences (sequences/monitoring.yml)
```yaml
sequences:
  interface_monitoring:
    description: "Detailed interface monitoring and statistics"
    commands:
      - "/interface/print detail"
      - "/interface/ethernet/print stats"
      - "/interface/monitor-traffic interface=ether1 count=5"
      - "/queue/simple/print stats"
    tags:
      - "monitoring"
      - "interface"
      - "performance"
  
  wireless_monitoring:
    description: "Wireless-specific monitoring commands"
    commands:
      - "/interface/wireless/print"
      - "/interface/wireless/registration-table/print"
      - "/interface/wireless/monitor 0"
    tags:
      - "monitoring"
      - "wireless"
  
  routing_analysis:
    description: "Routing table and protocol analysis"
    commands:
      - "/ip/route/print detail"
      - "/routing/ospf/neighbor/print"
      - "/routing/ospf/lsa/print"
      - "/routing/bgp/peer/print status"
    tags:
      - "monitoring"
      - "routing"
      - "ospf"
      - "bgp"
```

### Maintenance Tasks (sequences/maintenance.csv)
```csv
name,description,commands,tags
backup_config,Create configuration backup,/export file=backup-$(date +%Y%m%d),backup;maintenance
update_time,Synchronize system time,/system/ntp/client/set enabled=yes;/system/clock/print,maintenance;time
clear_logs,Clear old system logs,/log/remove [find where time<(now-7d)],maintenance;logs
reboot_safe,Safe system reboot with confirmation,/system/reboot,maintenance;reboot;critical
interface_reset,Reset interface statistics,/interface/reset-counters-all,maintenance;interface;stats
```

## Usage Examples

### Site-Specific Operations

```bash
# Check health of all headquarters equipment
nw run headquarters_all health_check

# Monitor all branch office devices
nw run branch_office_all interface_monitoring

# Backup all critical devices
nw run critical_infrastructure backup_config
```

### Device Type Operations

```bash
# Security audit on all firewalls
nw run all_firewalls security_audit

# Monitor all wireless access points
nw run wireless_infrastructure wireless_monitoring

# Check routing on edge devices
nw run edge_devices routing_analysis
```

### Maintenance Operations

```bash
# Weekend maintenance on access switches
nw run maintenance_weekend clear_logs

# Update time on all devices
nw run backup_priority_high update_time

# Health check on lab equipment before testing
nw run lab_environment health_check
```

### Individual Device Operations

```bash
# Check specific device
nw info sw-hq-floor1

# Run command on specific device
nw run fw-main "/ip/firewall/connection/print count-only"

# Upload firmware to lab device
nw upload sw-lab-01 firmware/routeros-7.x.npk
```

## Benefits Demonstrated

1. **Scalability**: Easy to add new sites by creating new CSV files
2. **Flexibility**: Mix YAML for complex configs and CSV for bulk data
3. **Organization**: Clear separation of concerns by site and device type
4. **Maintainability**: Updates to device lists don't require YAML editing
5. **Integration**: CSV files can be generated from asset management systems
6. **Consistency**: Standardized tagging enables powerful group operations

## Migration Strategy

1. **Start with core devices** in YAML format for complex configurations
2. **Add site-specific devices** using CSV for bulk additions
3. **Create logical groups** based on operational needs
4. **Define common sequences** for routine operations
5. **Gradually migrate** from manual processes to automated sequences

This example shows how the enhanced configuration system scales from small networks to enterprise deployments while maintaining clarity and ease of management.
