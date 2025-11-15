# 1. Kill tất cả processes cũ
pkill -9 3proxy

# 2. Xác nhận đã kill hết
ps aux | grep 3proxy

# 3. Xóa service cũ
systemctl stop 3proxy
systemctl disable 3proxy

# 4. Copy service file mới từ script
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

# 5. Reload systemd
systemctl daemon-reload

# 6. Enable và start lại
systemctl enable 3proxy
systemctl start 3proxy

# 7. Kiểm tra status
systemctl status 3proxy

# 8. Kiểm tra ports - BÂY GIỜ PHẢI THẤY CÁC PORT KHÁC NHAU
netstat -tlnp | grep 3proxy | sort -t: -k2 -n