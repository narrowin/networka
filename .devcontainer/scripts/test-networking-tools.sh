#!/bin/bash
set -euo pipefail

echo "=== Testing Networking Tools Installation ==="
echo ""

# Function to test command availability
test_command() {
    local cmd="$1"
    local description="$2"

    if command -v "$cmd" >/dev/null 2>&1; then
        echo "✓ $cmd - $description"
        case "$cmd" in
            "ping")
                echo "  Version: $(ping -V 2>/dev/null | head -1 || echo 'Version info not available')"
                ;;
            "tcpdump")
                echo "  Version: $(tcpdump --version 2>&1 | head -1 || echo 'Version info not available')"
                ;;
            "nmap")
                echo "  Version: $(nmap --version 2>/dev/null | head -1 || echo 'Version info not available')"
                ;;
            "netstat")
                echo "  Version: $(netstat --version 2>&1 | head -1 || echo 'Version info not available')"
                ;;
            *)
                ;;
        esac
    else
        echo "✗ $cmd - $description (NOT FOUND)"
    fi
    echo ""
}

echo "Basic networking tools:"
test_command "ping" "Send ICMP echo requests"
test_command "traceroute" "Trace network route to destination"
test_command "telnet" "TCP connection testing"
test_command "nc" "Netcat - network swiss army knife"
test_command "nmap" "Network discovery and security auditing"

echo "Network analysis tools:"
test_command "tcpdump" "Packet capture and analysis"
test_command "netstat" "Display network connections"
test_command "ss" "Socket statistics (modern netstat replacement)"
test_command "ip" "Network interface and routing configuration"
test_command "route" "Display/modify routing table"

echo "DNS and lookup tools:"
test_command "dig" "DNS lookup utility"
test_command "nslookup" "DNS lookup utility"
test_command "host" "DNS lookup utility"
test_command "whois" "Domain registration information"

echo "Performance and monitoring tools:"
test_command "mtr" "Network diagnostic tool (traceroute + ping)"
test_command "iperf3" "Network performance measurement"
test_command "htop" "Interactive process viewer"

echo "Additional utilities:"
test_command "socat" "Multipurpose network utility"
test_command "jq" "JSON processor"
test_command "curl" "Data transfer tool"
test_command "wget" "Web content downloader"
test_command "tree" "Directory tree display"
test_command "atuin" "Shell history management"

echo "=== Test Complete ==="
echo ""
echo "Note: Some tools may require elevated privileges or specific network access to function fully."
echo "This test only verifies that the tools are installed and accessible."
