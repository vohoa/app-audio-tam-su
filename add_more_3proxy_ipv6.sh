#!/bin/bash

#############################################
# Add More 3proxy IPv6 Proxies Script
# For Ubuntu 22.04
# Adds additional proxies to existing setup
#############################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Add More 3proxy IPv6 Proxies${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

# Check if 3proxy is installed
if [ ! -f "/usr/local/3proxy/bin/3proxy" ]; then
    echo -e "${RED}3proxy is not installed. Please run install_3proxy_ipv6.sh first.${NC}"
    exit 1
fi

# Check existing config
if [ ! -f "/usr/local/3proxy/conf/3proxy.cfg" ]; then
    echo -e "${RED}3proxy config not found!${NC}"
    exit 1
fi

# Output file
OUTPUT_FILE="/root/proxy_ipv6.txt"

# Get current proxy count from config
CURRENT_COUNT=$(grep -c "^proxy -6" /usr/local/3proxy/conf/3proxy.cfg || echo "0")
echo -e "${YELLOW}Current number of proxies: ${CURRENT_COUNT}${NC}"

# Get last port used
LAST_PORT=$(grep "^proxy -6" /usr/local/3proxy/conf/3proxy.cfg | tail -n1 | grep -oP '\-p\K[0-9]+' || echo "9999")
echo -e "${YELLOW}Last port used: ${LAST_PORT}${NC}"

# Get last proxy number
LAST_PROXY_NUM=$(grep "^users" /usr/local/3proxy/conf/3proxy.cfg | tail -n1 | grep -oP 'proxy\K[0-9]+' || echo "0")
echo -e "${YELLOW}Last proxy number: proxy${LAST_PROXY_NUM}${NC}"

# Get user input
echo -e "${YELLOW}How many proxies to add:${NC}"
read -r ADD_COUNT

# Validate count
if ! [[ "$ADD_COUNT" =~ ^[0-9]+$ ]] || [ "$ADD_COUNT" -lt 1 ]; then
    echo -e "${RED}Invalid number. Please enter a positive integer.${NC}"
    exit 1
fi

echo -e "${YELLOW}Enter proxy password (should match existing):${NC}"
read -rs PROXY_PASS
echo

if [ -z "$PROXY_PASS" ]; then
    echo -e "${RED}Password cannot be empty${NC}"
    exit 1
fi

# Get existing configuration
USER_PREFIX=$(grep "^users" /usr/local/3proxy/conf/3proxy.cfg | head -n1 | grep -oP '^users \K[a-z]+' || echo "proxy")
echo -e "${GREEN}Using username prefix: ${USER_PREFIX}${NC}"

# Get IPv6 configuration
IPV6_SUBNET=$(ip -6 addr show | grep "scope global" | grep -v "temporary" | awk '{print $2}' | head -n1)
if [ -z "$IPV6_SUBNET" ]; then
    echo -e "${RED}No IPv6 address found.${NC}"
    exit 1
fi

IPV6_BASE=$(echo $IPV6_SUBNET | cut -d':' -f1-4)
IPV6_PREFIX=$(echo $IPV6_SUBNET | cut -d'/' -f2)
NET_INTERFACE=$(ip route | grep default | awk '{print $5}' | head -n1)

echo -e "${GREEN}IPv6 Base: $IPV6_BASE${NC}"
echo -e "${GREEN}Network interface: $NET_INTERFACE${NC}"

# Get server IP
SERVER_IP=$(curl -s ifconfig.me)

# Generate new IPv6 addresses and add to interface
echo -e "${GREEN}Configuring new IPv6 addresses...${NC}"
declare -a NEW_IPV6_ADDRESSES

for i in $(seq 1 $ADD_COUNT); do
    PROXY_NUM=$((LAST_PROXY_NUM + i))
    IPV6_SUFFIX=$(printf "%x" $((1000 + PROXY_NUM)))
    IPV6_ADDR="${IPV6_BASE}::${IPV6_SUFFIX}"
    NEW_IPV6_ADDRESSES+=("$IPV6_ADDR")

    # Add IPv6 address to interface
    ip -6 addr add ${IPV6_ADDR}/${IPV6_PREFIX} dev ${NET_INTERFACE} 2>/dev/null || true
    echo -e "${BLUE}Added IPv6: ${IPV6_ADDR}${NC}"
done

# Stop 3proxy service
echo -e "${YELLOW}Stopping 3proxy service...${NC}"
systemctl stop 3proxy
sleep 2

# Backup current config
cp /usr/local/3proxy/conf/3proxy.cfg /usr/local/3proxy/conf/3proxy.cfg.backup
echo -e "${GREEN}Backed up config to 3proxy.cfg.backup${NC}"

# Add new users to config (before "# Proxy instances" line)
echo -e "${GREEN}Adding new users to config...${NC}"
for i in $(seq 1 $ADD_COUNT); do
    PROXY_NUM=$((LAST_PROXY_NUM + i))
    USERNAME="${USER_PREFIX}${PROXY_NUM}"

    # Add user after last existing user
    sed -i "/^users.*:CL:/a users ${USERNAME}:CL:${PROXY_PASS}" /usr/local/3proxy/conf/3proxy.cfg
done

# Add new proxy instances at the end of config
echo -e "${GREEN}Adding new proxy instances...${NC}"
for i in $(seq 1 $ADD_COUNT); do
    PROXY_NUM=$((LAST_PROXY_NUM + i))
    PORT=$((LAST_PORT + i))
    USERNAME="${USER_PREFIX}${PROXY_NUM}"
    IPV6_ADDR="${NEW_IPV6_ADDRESSES[$((i-1))]}"

    cat >> /usr/local/3proxy/conf/3proxy.cfg << EOF

# Proxy ${PROXY_NUM} - ${USERNAME} on port ${PORT}
auth strong
flush
allow ${USERNAME}
maxconn 100
proxy -6 -n -a -p${PORT} -e${IPV6_ADDR}
flush
EOF
done

# Update IPv6 persistence script
echo -e "${GREEN}Updating IPv6 persistence script...${NC}"
for i in $(seq 1 $ADD_COUNT); do
    PROXY_NUM=$((LAST_PROXY_NUM + i))
    IPV6_ADDR="${NEW_IPV6_ADDRESSES[$((i-1))]}"
    echo "ip -6 addr add ${IPV6_ADDR}/${IPV6_PREFIX} dev ${NET_INTERFACE} 2>/dev/null || true" >> /usr/local/3proxy/add_ipv6.sh
done

# Update firewall
echo -e "${GREEN}Updating firewall rules...${NC}"
if command -v ufw &> /dev/null; then
    for i in $(seq 1 $ADD_COUNT); do
        PORT=$((LAST_PORT + i))
        ufw allow ${PORT}/tcp >/dev/null 2>&1
    done
    ufw reload
    NEW_LAST_PORT=$((LAST_PORT + ADD_COUNT))
    echo -e "${GREEN}UFW firewall rules added for ports $((LAST_PORT + 1))-${NEW_LAST_PORT}${NC}"
fi

# Start 3proxy service
echo -e "${GREEN}Starting 3proxy service...${NC}"
systemctl start 3proxy
sleep 3

# Add new proxies to proxy list files
echo -e "${GREEN}Adding to proxy list files...${NC}"
OUTPUT_CSV="/root/proxy_ipv6.csv"

for i in $(seq 1 $ADD_COUNT); do
    PROXY_NUM=$((LAST_PROXY_NUM + i))
    PORT=$((LAST_PORT + i))
    USERNAME="${USER_PREFIX}${PROXY_NUM}"
    IPV6_ADDR="${NEW_IPV6_ADDRESSES[$((i-1))]}"

    # Append to TXT file
    echo "http://${USERNAME}:${PROXY_PASS}@${SERVER_IP}:${PORT}" >> "$OUTPUT_FILE"

    # Append to CSV file
    echo "${SERVER_IP},${PORT},${USERNAME},${PROXY_PASS},http" >> "$OUTPUT_CSV"
done

# Check service status
if systemctl is-active --quiet 3proxy; then
    NEW_TOTAL=$((CURRENT_COUNT + ADD_COUNT))
    NEW_LAST_PORT=$((LAST_PORT + ADD_COUNT))

    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Successfully added ${ADD_COUNT} proxies!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "${YELLOW}Summary:${NC}"
    echo -e "Server IP: ${SERVER_IP}"
    echo -e "Previous total: ${CURRENT_COUNT} proxies"
    echo -e "Added: ${ADD_COUNT} proxies"
    echo -e "New total: ${NEW_TOTAL} proxies"
    echo -e "New port range: $((LAST_PORT + 1))-${NEW_LAST_PORT}"
    echo -e ""
    echo -e "${GREEN}Updated proxy list: ${OUTPUT_FILE}${NC}"
    echo -e ""
    echo -e "${YELLOW}New proxies added:${NC}"
    tail -n ${ADD_COUNT} "$OUTPUT_FILE"
    echo -e ""
    echo -e "${YELLOW}Verify all ports:${NC}"
    echo -e "netstat -tlnp | grep 3proxy"
    echo -e ""
    echo -e "${YELLOW}Test new proxy:${NC}"
    FIRST_NEW_PROXY=$(tail -n ${ADD_COUNT} "$OUTPUT_FILE" | head -n1)
    echo -e "curl -x ${FIRST_NEW_PROXY} https://ipv6.icanhazip.com"
    echo -e "${GREEN}========================================${NC}"
else
    echo -e "${RED}Failed to start 3proxy service${NC}"
    echo -e "${YELLOW}Restoring backup...${NC}"
    cp /usr/local/3proxy/conf/3proxy.cfg.backup /usr/local/3proxy/conf/3proxy.cfg
    systemctl start 3proxy
    echo -e "${YELLOW}Check logs: journalctl -xe | grep 3proxy${NC}"
    exit 1
fi

echo -e "${GREEN}Done! Added ${ADD_COUNT} new proxies.${NC}"
