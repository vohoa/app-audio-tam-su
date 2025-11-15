#!/bin/bash

#############################################
# 3proxy IPv6 Bulk Installation Script
# For Ubuntu 22.04
# Creates multiple proxies with IPv6 support
#############################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}3proxy IPv6 SOCKS5 Installation Script${NC}"
echo -e "${GREEN}Ubuntu 22.04 - SOCKS5 Only${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

# Get user input
echo -e "${YELLOW}Enter number of proxies to create:${NC}"
read -r PROXY_COUNT

# Validate proxy count
if ! [[ "$PROXY_COUNT" =~ ^[0-9]+$ ]] || [ "$PROXY_COUNT" -lt 1 ]; then
    echo -e "${RED}Invalid number. Please enter a positive integer.${NC}"
    exit 1
fi

echo -e "${YELLOW}Enter starting port (default 10000):${NC}"
read -r START_PORT
START_PORT=${START_PORT:-10000}

echo -e "${YELLOW}Enter proxy username prefix (default 'proxy'):${NC}"
read -r USER_PREFIX
USER_PREFIX=${USER_PREFIX:-proxy}

echo -e "${YELLOW}Enter proxy password (same for all):${NC}"
read -rs PROXY_PASS
echo

if [ -z "$PROXY_PASS" ]; then
    echo -e "${RED}Password cannot be empty${NC}"
    exit 1
fi

# Output file
OUTPUT_FILE="./proxy_ipv6.csv"

echo -e "${GREEN}Installing dependencies...${NC}"
apt update
apt install -y build-essential wget curl net-tools iproute2

# Check IPv6
echo -e "${GREEN}Checking IPv6 configuration...${NC}"
IPV6_SUBNET=$(ip -6 addr show | grep "scope global" | grep -v "temporary" | awk '{print $2}' | head -n1)
if [ -z "$IPV6_SUBNET" ]; then
    echo -e "${RED}No IPv6 address found. Please configure IPv6 first.${NC}"
    exit 1
fi

# Extract IPv6 base address and prefix
IPV6_BASE=$(echo $IPV6_SUBNET | cut -d':' -f1-4)
IPV6_PREFIX=$(echo $IPV6_SUBNET | cut -d'/' -f2)
echo -e "${GREEN}IPv6 Subnet: $IPV6_SUBNET${NC}"
echo -e "${GREEN}IPv6 Base: $IPV6_BASE${NC}"

# Get server public IPv4 (force IPv4)
SERVER_IP=$(curl -4 -s ifconfig.me 2>/dev/null || curl -s api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}')
echo -e "${GREEN}Server IPv4: $SERVER_IP${NC}"

# Validate IPv4 format
if ! [[ $SERVER_IP =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "${RED}Failed to get valid IPv4 address: $SERVER_IP${NC}"
    echo -e "${YELLOW}Please enter server IPv4 manually:${NC}"
    read -r SERVER_IP
fi

# Get network interface
NET_INTERFACE=$(ip route | grep default | awk '{print $5}' | head -n1)
echo -e "${GREEN}Network interface: $NET_INTERFACE${NC}"

# Download and compile 3proxy
echo -e "${GREEN}Downloading 3proxy source...${NC}"
cd /tmp
PROXY_VERSION="0.9.4"

# Clean up old files if exist
rm -rf ${PROXY_VERSION}.tar.gz 3proxy-${PROXY_VERSION}

wget -q https://github.com/3proxy/3proxy/archive/refs/tags/${PROXY_VERSION}.tar.gz
tar xzf ${PROXY_VERSION}.tar.gz
cd 3proxy-${PROXY_VERSION}

echo -e "${GREEN}Compiling 3proxy...${NC}"
make -f Makefile.Linux

# Check if compilation was successful
if [ ! -f "bin/3proxy" ]; then
    echo -e "${RED}Compilation failed! 3proxy binary not found.${NC}"
    echo -e "${YELLOW}Checking if build directory exists...${NC}"
    ls -la bin/ 2>/dev/null || echo "bin/ directory not found"
    exit 1
fi

# Install 3proxy
echo -e "${GREEN}Installing 3proxy...${NC}"
mkdir -p /usr/local/3proxy/{bin,logs,conf}
cp bin/3proxy /usr/local/3proxy/bin/
chmod +x /usr/local/3proxy/bin/3proxy

# Verify installation
if [ ! -f "/usr/local/3proxy/bin/3proxy" ]; then
    echo -e "${RED}Installation failed! 3proxy binary not found in /usr/local/3proxy/bin/${NC}"
    exit 1
fi

echo -e "${GREEN}3proxy binary installed successfully${NC}"

# Generate IPv6 addresses and add to interface
echo -e "${GREEN}Configuring IPv6 addresses...${NC}"
declare -a IPV6_ADDRESSES

for i in $(seq 1 $PROXY_COUNT); do
    # Generate unique IPv6 address
    IPV6_SUFFIX=$(printf "%x" $((1000 + $i)))
    IPV6_ADDR="${IPV6_BASE}::${IPV6_SUFFIX}"
    IPV6_ADDRESSES+=("$IPV6_ADDR")

    # Add IPv6 address to interface
    ip -6 addr add ${IPV6_ADDR}/${IPV6_PREFIX} dev ${NET_INTERFACE} 2>/dev/null || true
    echo -e "${BLUE}Added IPv6: ${IPV6_ADDR}${NC}"
done

# Create config file with multiple proxies
echo -e "${GREEN}Creating configuration file...${NC}"
cat > /usr/local/3proxy/conf/3proxy.cfg << 'EOF'
# 3proxy configuration file
daemon
nserver 8.8.8.8
nserver 8.8.4.4
nscache 65536
timeouts 1 5 30 60 180 1800 15 60

# Log configuration
log /usr/local/3proxy/logs/3proxy.log D
logformat "- +_L%t.%. %N.%p %E %U %C:%c %R:%r %O %I %h %T"
rotate 30
archiver ext /bin/gzip %F.gz

# No authentication - IP whitelist security
auth none

# SOCKS5 Proxy instances
EOF

# Create SOCKS5 proxy instances - each with its own auth/allow rules
for i in $(seq 1 $PROXY_COUNT); do
    PORT=$((START_PORT + i - 1))
    USERNAME="${USER_PREFIX}${i}"
    IPV6_ADDR="${IPV6_ADDRESSES[$((i-1))]}"

    cat >> /usr/local/3proxy/conf/3proxy.cfg << EOF

# SOCKS5 Proxy $i - No auth, IP whitelist on port ${PORT} (Auto IPv4/IPv6)
# No authentication required - security via IP whitelist
# Auto-select IPv4 or IPv6 based on destination
flush
# Allow only whitelisted IPs (add your IPs here)
allow * 116.96.77.167
# Deny all other IPs
deny *
maxconn 100
# No -e flag = auto-select external IP (IPv4 or IPv6) based on destination
socks -n -p${PORT}
flush
EOF
done

# Create systemd service
echo -e "${GREEN}Creating systemd service...${NC}"
cat > /etc/systemd/system/3proxy.service << 'EOF'
[Unit]
Description=3proxy Proxy Server
After=network.target

[Service]
Type=forking
ExecStart=/usr/local/3proxy/bin/3proxy /usr/local/3proxy/conf/3proxy.cfg
ExecStop=/usr/bin/pkill -9 3proxy
ExecReload=/bin/kill -HUP $MAINPID
KillMode=control-group
KillSignal=SIGTERM
TimeoutStopSec=5
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Create IPv6 persistence script
echo -e "${GREEN}Creating IPv6 persistence script...${NC}"
cat > /usr/local/3proxy/add_ipv6.sh << EOF
#!/bin/bash
# Add IPv6 addresses on boot
EOF

for i in $(seq 1 $PROXY_COUNT); do
    IPV6_ADDR="${IPV6_ADDRESSES[$((i-1))]}"
    echo "ip -6 addr add ${IPV6_ADDR}/${IPV6_PREFIX} dev ${NET_INTERFACE} 2>/dev/null || true" >> /usr/local/3proxy/add_ipv6.sh
done

chmod +x /usr/local/3proxy/add_ipv6.sh

# Add to rc.local or create systemd service for IPv6
cat > /etc/systemd/system/ipv6-proxy-config.service << EOF
[Unit]
Description=Configure IPv6 addresses for proxies
After=network.target
Before=3proxy.service

[Service]
Type=oneshot
ExecStart=/usr/local/3proxy/add_ipv6.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ipv6-proxy-config.service

# Configure firewall
echo -e "${GREEN}Configuring firewall...${NC}"
if command -v ufw &> /dev/null; then
    for i in $(seq 1 $PROXY_COUNT); do
        PORT=$((START_PORT + i - 1))
        ufw allow ${PORT}/tcp >/dev/null 2>&1
    done
    ufw reload
    echo -e "${GREEN}UFW firewall rules added for ports ${START_PORT}-$((START_PORT + PROXY_COUNT - 1))${NC}"
fi

# Enable and start service
echo -e "${GREEN}Starting 3proxy service...${NC}"
systemctl daemon-reload
systemctl enable 3proxy
systemctl restart 3proxy

# Wait for service to start
sleep 3

# Generate proxy list files
echo -e "${GREEN}Generating proxy list...${NC}"

# Generate TXT format (URL format for SOCKS5 - no auth)
> "$OUTPUT_FILE"
for i in $(seq 1 $PROXY_COUNT); do
    PORT=$((START_PORT + i - 1))
    IPV6_ADDR="${IPV6_ADDRESSES[$((i-1))]}"
    echo "socks5://${SERVER_IP}:${PORT}" >> "$OUTPUT_FILE"
done

# Generate CSV format
OUTPUT_CSV="/root/proxy_ipv6.csv"
> "$OUTPUT_CSV"

for i in $(seq 1 $PROXY_COUNT); do
    PORT=$((START_PORT + i - 1))
    IPV6_ADDR="${IPV6_ADDRESSES[$((i-1))]}"
    # Format: IP,PORT,USERNAME,PASSWORD,PROTOCOL (no username/password for no-auth)
    echo "${SERVER_IP},${PORT},,,socks5" >> "$OUTPUT_CSV"
done

echo -e "${GREEN}SOCKS5 proxy list saved to:${NC}"
echo -e "  - TXT format: ${OUTPUT_FILE}"
echo -e "  - CSV format: ${OUTPUT_CSV}"

# Check service status
if systemctl is-active --quiet 3proxy; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}3proxy SOCKS5 installed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "${YELLOW}Configuration Summary:${NC}"
    echo -e "Protocol: SOCKS5 (No Auth - IP Whitelist) ✅"
    echo -e "Server IP: ${SERVER_IP}"
    echo -e "Whitelisted IP: 116.96.77.167"
    echo -e "Total Proxies: ${PROXY_COUNT}"
    echo -e "Port Range: ${START_PORT}-$((START_PORT + PROXY_COUNT - 1))"
    echo -e "Authentication: None (IP-based security)"
    echo -e ""
    echo -e "${GREEN}SOCKS5 proxy lists saved to:${NC}"
    echo -e "  - TXT format: ${OUTPUT_FILE}"
    echo -e "  - CSV format: ${OUTPUT_CSV}"
    echo -e ""
    echo -e "${YELLOW}Sample SOCKS5 proxies (TXT format):${NC}"
    head -n 5 "$OUTPUT_FILE"
    echo -e ""
    echo -e "${YELLOW}Sample SOCKS5 proxies (CSV format):${NC}"
    head -n 5 "$OUTPUT_CSV"
    if [ $PROXY_COUNT -gt 5 ]; then
        echo "..."
        echo -e "${BLUE}(Total ${PROXY_COUNT} SOCKS5 proxies)${NC}"
    fi
    echo -e ""
    echo -e "${YELLOW}Test first SOCKS5 proxy (no auth needed):${NC}"
    FIRST_CSV=$(head -n 1 "$OUTPUT_CSV")
    IFS=',' read -r HOST PORT USER PASS PROTO <<< "$FIRST_CSV"
    echo -e "curl --socks5 ${HOST}:${PORT} https://ipv6.icanhazip.com"
    echo -e "curl --socks5 ${HOST}:${PORT} https://ipv4.icanhazip.com"
    echo -e ""
    echo -e "${YELLOW}Service commands:${NC}"
    echo -e "Check status: systemctl status 3proxy"
    echo -e "Restart: systemctl restart 3proxy"
    echo -e "Stop: systemctl stop 3proxy"
    echo -e "View logs: tail -f /usr/local/3proxy/logs/3proxy.log"
    echo -e "View TXT list: cat ${OUTPUT_FILE}"
    echo -e "View CSV list: cat ${OUTPUT_CSV}"
    echo -e "${GREEN}========================================${NC}"
else
    echo -e "${RED}Failed to start 3proxy service${NC}"
    echo -e "${YELLOW}Check logs: journalctl -xe | grep 3proxy${NC}"
    echo -e "${YELLOW}Check config: cat /usr/local/3proxy/conf/3proxy.cfg${NC}"
    exit 1
fi

# Cleanup
rm -rf /tmp/${PROXY_VERSION}.tar.gz /tmp/3proxy-${PROXY_VERSION}

echo -e "${GREEN}Installation complete!${NC}"
echo -e "${GREEN}All proxy URLs are saved in: ${OUTPUT_FILE}${NC}"
