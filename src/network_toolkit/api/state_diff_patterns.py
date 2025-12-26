"""Regex patterns for heuristic operational state diffing.

This module centralizes regex patterns used for:
1. Volatile field detection (timestamps, counters, uptimes)
2. Entity extraction (interfaces, IPs, MACs)
3. Table detection (separators, headers)
4. Ignore patterns (banners, crypto blobs)

Patterns are derived from industry standard tools like diffios, netcompare, and Genie.
"""

import re

# --- Volatile Field Patterns (Timestamps, Uptimes, Counters) ---

# Timestamps (ISO, US, HH:MM:SS, day-month text)
TIMESTAMP_PATTERNS = [
    # ISO-like: 2023-10-25T12:34:56.789
    re.compile(r"\d{4}[-/]\d{2}[-/]\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?"),
    # US format: 10/25/2023 12:34:56
    re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}(?::\d{2})?"),
    # Time only: 12:34:56.789
    re.compile(r"\d{1,2}:\d{2}:\d{2}(?:\.\d+)?"),
    # Day/month text: Wed Oct 25 12:34:56 2023
    re.compile(
        r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4}"
    ),
    # Cisco "timestamp abs first": timestamp abs first: 12:34:56.789
    re.compile(r"timestamp abs first:\s+[\d\:\.]+"),
]

# Uptimes (Cisco style, colon format, "up for")
UPTIME_PATTERNS = [
    # Cisco style: 1 year, 2 weeks, 3 days, 4 hours, 5 minutes
    re.compile(r"\d+\s+(?:year|week|day|hour|minute|second)s?,?\s*"),
    # Colon format: 12:34:56.789
    re.compile(r"\d+:\d{2}:\d{2}(?:\.\d+)?"),
    # "Up for X" style: up for 1 year, 2 weeks
    re.compile(r"up\s+(?:for\s+)?[\d\w\s,]+"),
    # Tunnel uptime: Tunnel has been up for: 12:34:56
    re.compile(r"Tunnel has been up for:\s+.+"),
]

# Counters (Packets, Bytes, Rates, Large Numbers)
COUNTER_PATTERNS = [
    # Large numbers with commas: 1,234,567
    re.compile(r"\b\d{1,3}(?:,\d{3})+\b"),
    # Packet/byte counters: 1234 packets, 5678 bytes
    re.compile(r"(?:packets?|bytes?|pkts?|frames?)[\s:]+\d+"),
    # Number followed by unit: 100 packets, 50 bytes/sec
    re.compile(
        r"\d+\s+(?:packets?|bytes?|frames?|bits?|errors?|drops?|flushes?)(?:/sec)?"
    ),
    # Rate fields: 1000 bps, 1.5 mbps
    re.compile(r"\d+(?:\.\d+)?\s*(?:bps|kbps|mbps|gbps|pps)"),
    # Delta values: delta 123, change -5
    re.compile(r"(?:delta|change|diff)[\s:]+[-+]?\d+"),
    # Input/Output rates: 5 minute input rate 0 bits/sec, 0 packets/sec
    re.compile(r"\d+\s+minute\s+(?:input|output)\s+rate\s+\d+\s+\w+/sec"),
]

# Volatile IDs (Session IDs, Sequence Numbers)
VOLATILE_ID_PATTERNS = [
    re.compile(r"seq(?:uence)?\s*(?:num(?:ber)?)?[\s:#]+\d+"),
    re.compile(r"session[\s-]?id[\s:]+[\da-fA-F]+"),
    re.compile(r"transaction[\s-]?id[\s:]+\d+"),
    re.compile(r"(?:flow|connection)[\s-]?id[\s:]+\d+"),
]

# --- Entity Extraction Patterns (Interfaces, IPs, MACs) ---

# Interface Identity
INTERFACE_IDENTITY_PATTERN = re.compile(
    r"""
    (?:interface\s+)?
    (?P<type>
        (?:Gigabit|TenGigabit|HundredGigabit|Fast)?Ethernet|
        (?:Port-?channel|Bundle-Ether|bond)|
        (?:Vlan|BVI|Loopback|Tunnel|Serial|Dialer|Cellular)
    )
    [\s-]?
    (?P<id>\d+(?:[/.:]\d+)*)
""",
    re.VERBOSE | re.IGNORECASE,
)

# Route Entry Identity
ROUTE_IDENTITY_PATTERN = re.compile(
    r"""
    (?P<prefix>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})
    [/\s]+
    (?P<mask>(?:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})|(?:\d{1,2}))
    (?:\s+via\s+(?P<nexthop>\S+))?
""",
    re.VERBOSE,
)

# BGP Neighbor Identity
BGP_NEIGHBOR_IDENTITY_PATTERN = re.compile(
    r"""
    neighbor\s+
    (?P<address>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|[\da-fA-F:]+)
    (?:\s+(?P<attribute>\S+))?
""",
    re.VERBOSE | re.IGNORECASE,
)

# MAC Address Identity
MAC_ADDRESS_PATTERN = re.compile(
    r"(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}|(?:[0-9a-fA-F]{4}\.){2}[0-9a-fA-F]{4}"
)

# --- Table Detection Patterns ---

# Separator lines: ---, ===, ___
TABLE_SEPARATOR_PATTERN = re.compile(r"^[\s\-=+|]+$")

# Header pattern: Multiple words starting with capitals (heuristic)
TABLE_HEADER_PATTERN = re.compile(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){2,}")

# --- Ignore Patterns ---

IGNORE_PATTERNS = [
    re.compile(r"building configuration", re.IGNORECASE),
    re.compile(r"current configuration", re.IGNORECASE),
    re.compile(r"ntp clock-period", re.IGNORECASE),
    re.compile(r"^!"),  # Comments
    re.compile(r"^end$"),
    re.compile(r"--More--"),  # Pagination
]
