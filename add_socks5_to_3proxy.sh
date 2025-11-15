#!/bin/bash

#############################################
# Add SOCKS5 support to existing 3proxy
# Keeps existing HTTP proxies
# Adds SOCKS5 on new ports
#############################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Add SOCKS5 to Existing 3proxy${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

# Check if 3proxy is installed
if [ ! -f "/usr/local/3proxy/bin/3proxy" ]; then
    echo -e "${RED}3proxy is not installed!${NC}"
    exit 1
fi

# Check existing config
if [ ! -f "/usr/local/3proxy/conf/3proxy.cfg" ]; then
    echo -e "${RED}3proxy config not found!${NC}"
    exit 1
fi

echo -e "${YELLOW}Current HTTP proxies detected:${NC}"
grep "^proxy -6" /usr/local/3proxy/conf/3proxy.cfg | grep -oP '\-p\K[0-9]+' | head -5
echo "..."

# Count existing proxies
PROXY_COUNT=$(grep -c "^proxy -6" /usr/local/3proxy/conf/3proxy.cfg || echo "0")
echo -e "${GREEN}Total HTTP proxies: ${PROXY_COUNT}${NC}"

# Get configuration from existing setup
echo
echo -e "${YELLOW}SOCKS5 Configuration:${NC}"
read -p "Starting SOCKS5 port (default: 20000): " SOCKS_START_PORT
SOCKS_START_PORT=${SOCKS_START_PORT:-20000}

# Get IPv6 configuration
IPV6_SUBNET=$(ip -6 addr show | grep "scope global" | grep -v "temporary" | awk '{print $2}' | head -n1)
if [ -z "$IPV6_SUBNET" ]; then
    echo -e "${RED}No IPv6 address found${NC}"
    exit 1
fi

IPV6_BASE=$(echo $IPV6_SUBNET | cut -d':' -f1-4)
IPV6_PREFIX=$(echo $IPV6_SUBNET | cut -d'/' -f2)
NET_INTERFACE=$(ip route | grep default | awk '{print $5}' | head -n1)

echo -e "${GREEN}IPv6 Base: $IPV6_BASE${NC}"
echo -e "${GREEN}Network interface: $NET_INTERFACE${NC}"

# Stop 3proxy
echo
echo -e "${YELLOW}Stopping 3proxy...${NC}"
systemctl stop 3proxy
sleep 2

# Backup config
cp /usr/local/3proxy/conf/3proxy.cfg /usr/local/3proxy/conf/3proxy.cfg.backup.$(date +%Y%m%d_%H%M%S)
echo -e "${GREEN}Config backed up${NC}"

# Add SOCKS5 instances
echo
echo -e "${GREEN}Adding SOCKS5 instances...${NC}"

for i in $(seq 1 $PROXY_COUNT); do
    SOCKS_PORT=$((SOCKS_START_PORT + i - 1))
    USERNAME="proxy${i}"

    # Generate IPv6 address (same as HTTP proxy)
    IPV6_SUFFIX=$(printf "%x" $((1000 + $i)))
    IPV6_ADDR="${IPV6_BASE}::${IPV6_SUFFIX}"

    # Add SOCKS5 configuration
    cat >> /usr/local/3proxy/conf/3proxy.cfg << EOF

# SOCKS5 Proxy $i - ${USERNAME} on port ${SOCKS_PORT}
auth strong
flush
allow ${USERNAME}
maxconn 100
socks -6 -n -a -p${SOCKS_PORT} -e${IPV6_ADDR}
flush
EOF

    echo -e "${BLUE}Added SOCKS5: ${USERNAME} on port ${SOCKS_PORT}${NC}"
done

# Configure firewall for SOCKS5 ports
echo
echo -e "${GREEN}Configuring firewall...${NC}"
if command -v ufw &> /dev/null; then
    for i in $(seq 1 $PROXY_COUNT); do
        SOCKS_PORT=$((SOCKS_START_PORT + i - 1))
        ufw allow ${SOCKS_PORT}/tcp >/dev/null 2>&1
    done
    ufw reload >/dev/null 2>&1
    echo -e "${GREEN}Firewall rules added for SOCKS5 ports ${SOCKS_START_PORT}-$((SOCKS_START_PORT + PROXY_COUNT - 1))${NC}"
fi

# Start 3proxy
echo
echo -e "${GREEN}Starting 3proxy...${NC}"
systemctl start 3proxy
sleep 3

# Check status
if systemctl is-active --quiet 3proxy; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ SOCKS5 added successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"

    # Generate SOCKS5 CSV
    OUTPUT_CSV="/root/proxy_ipv6_socks5.csv"
    > "$OUTPUT_CSV"

    SERVER_IP=$(curl -s ifconfig.me)

    # Get password from existing config
    PASSWORD=$(grep "^users proxy1:" /usr/local/3proxy/conf/3proxy.cfg | grep -oP 'CL:\K[^"]+' | head -1)

    for i in $(seq 1 $PROXY_COUNT); do
        SOCKS_PORT=$((SOCKS_START_PORT + i - 1))
        USERNAME="proxy${i}"
        echo "${SERVER_IP},${SOCKS_PORT},${USERNAME},${PASSWORD},socks5" >> "$OUTPUT_CSV"
    done

    echo
    echo -e "${YELLOW}Summary:${NC}"
    echo -e "Server IP: ${SERVER_IP}"
    echo -e "HTTP Proxies: ${PROXY_COUNT} (ports unchanged)"
    echo -e "SOCKS5 Proxies: ${PROXY_COUNT} (ports ${SOCKS_START_PORT}-$((SOCKS_START_PORT + PROXY_COUNT - 1)))"
    echo
    echo -e "${GREEN}SOCKS5 proxy list saved to: ${OUTPUT_CSV}${NC}"
    echo
    echo -e "${YELLOW}Sample SOCKS5 proxies:${NC}"
    head -n 5 "$OUTPUT_CSV"
    if [ $PROXY_COUNT -gt 5 ]; then
        echo "..."
    fi
    echo
    echo -e "${YELLOW}Test SOCKS5 proxy:${NC}"
    FIRST_PROXY=$(head -n 1 "$OUTPUT_CSV")
    IFS=',' read -r HOST PORT USER PASS PROTO <<< "$FIRST_PROXY"
    echo -e "curl --socks5 ${HOST}:${PORT} --proxy-user ${USER}:${PASS} https://ipv6.icanhazip.com"
    echo
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Download: scp root@${SERVER_IP}:${OUTPUT_CSV} ."
    echo "2. Import: python import_proxies.py proxy_ipv6_socks5.csv"
    echo "3. Or use GUI: Menu -> 🌐 Proxy -> Import CSV"
    echo -e "${GREEN}========================================${NC}"

    # Show listening ports
    echo
    echo -e "${YELLOW}Verify ports:${NC}"
    netstat -tlnp | grep 3proxy | grep -E ":(10[0-9]{3}|20[0-9]{3})" | head -10

else
    echo -e "${RED}Failed to start 3proxy!${NC}"
    echo -e "${YELLOW}Restoring backup...${NC}"
    cp /usr/local/3proxy/conf/3proxy.cfg.backup.* /usr/local/3proxy/conf/3proxy.cfg
    systemctl start 3proxy
    exit 1
fi
