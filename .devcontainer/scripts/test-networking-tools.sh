#!/usr/bin/env bash
set -euo pipefail

# Quick probes that don't require root or extra caps
python - <<'PY'
import socket
print('DNS OK:', socket.gethostbyname('example.com'))
print('TCP OK:', socket.create_connection(('example.com', 80), timeout=3).getsockname())
PY

ssh -V || true
which ping && ping -c1 1.1.1.1 || echo "ping failed (ICMP may require caps)"
