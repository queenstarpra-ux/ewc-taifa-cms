#!/bin/bash
clear
echo ""
echo " ============================================================"
echo "  Ebenezer Worship Centre Taifa — Church Management System"
echo "  The Church of Pentecost | Taifa District | Greater Accra"
echo " ============================================================"
echo ""
PY=""
for cmd in python3 python; do
    if command -v $cmd &>/dev/null; then
        V=$($cmd -c "import sys;print(sys.version_info.major)" 2>/dev/null)
        [ "$V" = "3" ] && PY=$cmd && break
    fi
done
if [ -z "$PY" ]; then
    echo " ERROR: Python 3 not found."
    echo " Mac:   Install from https://www.python.org/downloads/"
    echo " Linux: sudo apt install python3"
    exit 1
fi
echo " Python 3 found: $($PY --version)"
echo ""
echo " Open browser: http://127.0.0.1:3000"
echo " Username: admin   Password: admin123"
echo " Press Ctrl+C to stop"
echo " ============================================================"
echo ""
$PY server.py
