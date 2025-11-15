#!/bin/bash

#############################################
# Simple script to download proxy_ipv6.csv
# from remote server using scp
#############################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}📡 Download Proxy List from Server${NC}"
echo -e "${GREEN}========================================${NC}"
echo

# Get server details
read -p "🖥️  Server IP/Hostname: " SERVER_HOST
if [ -z "$SERVER_HOST" ]; then
    echo -e "${RED}❌ Server hostname is required!${NC}"
    exit 1
fi

read -p "👤 Username: " USERNAME
if [ -z "$USERNAME" ]; then
    echo -e "${RED}❌ Username is required!${NC}"
    exit 1
fi

read -p "🔌 SSH Port (default: 22): " SSH_PORT
SSH_PORT=${SSH_PORT:-22}

read -p "📁 Remote file path (default: /root/proxy_ipv6.csv): " REMOTE_FILE
REMOTE_FILE=${REMOTE_FILE:-/root/proxy_ipv6.csv}

# Local file path
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOCAL_FILE="${SCRIPT_DIR}/proxy_ipv6.csv"

echo
echo -e "${BLUE}📋 Configuration:${NC}"
echo -e "   Server: ${USERNAME}@${SERVER_HOST}:${SSH_PORT}"
echo -e "   Remote: ${REMOTE_FILE}"
echo -e "   Local:  ${LOCAL_FILE}"
echo

read -p "Continue? (y/n): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo -e "${RED}❌ Cancelled${NC}"
    exit 0
fi

echo
echo -e "${GREEN}========================================${NC}"

# Download using scp
echo -e "${BLUE}📥 Downloading file...${NC}"
scp -P ${SSH_PORT} ${USERNAME}@${SERVER_HOST}:${REMOTE_FILE} ${LOCAL_FILE}

# Check if download was successful
if [ $? -eq 0 ]; then
    if [ -f "${LOCAL_FILE}" ]; then
        FILE_SIZE=$(wc -c < "${LOCAL_FILE}")
        LINE_COUNT=$(wc -l < "${LOCAL_FILE}")

        echo -e "${GREEN}✅ Download completed!${NC}"
        echo -e "   File: ${LOCAL_FILE}"
        echo -e "   Size: ${FILE_SIZE} bytes"
        echo -e "   Proxies: ${LINE_COUNT}"
        echo
        echo -e "${YELLOW}📋 Preview (first 5 lines):${NC}"
        head -n 5 "${LOCAL_FILE}"
        echo
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}✅ SUCCESS!${NC}"
        echo
        echo -e "${YELLOW}Next steps:${NC}"
        echo "1. Run: python import_proxies.py proxy_ipv6.csv"
        echo "2. Or use GUI: Menu -> 🌐 Proxy -> ⚙️ Quản Lý Proxy -> Import CSV"
        echo -e "${GREEN}========================================${NC}"
        exit 0
    else
        echo -e "${RED}❌ Local file not created${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Download failed!${NC}"
    echo -e "${YELLOW}Please check:${NC}"
    echo "  - Server hostname/IP is correct"
    echo "  - Username and password are correct"
    echo "  - Remote file path exists: ${REMOTE_FILE}"
    echo "  - SSH port is correct: ${SSH_PORT}"
    exit 1
fi
