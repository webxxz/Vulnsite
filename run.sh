#!/bin/bash
cd "$(dirname "$0")"

echo ""
echo "  ██╗   ██╗██╗   ██╗██╗     ███╗   ██╗███████╗██╗████████╗███████╗"
echo "  ██║   ██║██║   ██║██║     ████╗  ██║██╔════╝██║╚══██╔══╝██╔════╝"
echo "  ██║   ██║██║   ██║██║     ██╔██╗ ██║███████╗██║   ██║   █████╗  "
echo "  ╚██╗ ██╔╝██║   ██║██║     ██║╚██╗██║╚════██║██║   ██║   ██╔══╝  "
echo "   ╚████╔╝ ╚██████╔╝███████╗██║ ╚████║███████║██║   ██║   ███████╗"
echo "    ╚═══╝   ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚══════╝╚═╝   ╚═╝   ╚══════╝"
echo ""
echo "  Web Security Practice Lab — For Educational Use Only"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "[!] Python3 not found. Please install Python 3.8+"
  exit 1
fi

# Install Flask if needed
python3 -c "import flask" 2>/dev/null || {
  echo "[*] Installing Flask..."
  pip3 install flask --quiet
}

echo "[*] Starting vulnsite on http://localhost:5000"
echo "[*] Press Ctrl+C to stop"
echo ""
echo "  Labs available:"
echo "  /bac      → Broken Access Control + IDOR"
echo "  /payment  → Payment Bypass (3 labs)"
echo "  /bypass   → 403 Bypass (8 challenges)"
echo "  /sqli     → SQL Injection"
echo "  /xss      → Cross-Site Scripting"
echo "  /cmdi     → Command Injection"
echo "  /ssrf     → Server-Side Request Forgery"
echo "  /redirect → Open Redirect"
echo "  /exposure → Sensitive Data Exposure"
echo "  /deser    → Insecure Deserialization"
echo ""

python3 app.py
