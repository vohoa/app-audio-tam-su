# Runware API Troubleshooting Guide

## Common Errors and Solutions

### 1. `asyncio.exceptions.TimeoutError: timed out during opening handshake`

**Nguyên nhân:**
- WebSocket connection không thể được thiết lập trong thời gian timeout
- API key không đúng hoặc đã hết hạn
- Vấn đề về network/firewall
- Runware API service tạm thời bị quá tải

**Giải pháp:**

#### A. Kiểm tra API Key
```bash
# Kiểm tra API key trong config
cd /home/dragons/Documents/Projects/aistudio-generate-speech/desktop_audio_generator
python3 -c "import config; print('API Key:', config.RUNWARE_API_KEY[:10] + '...' if config.RUNWARE_API_KEY else 'NOT SET')"
```

**Làm thế nào để lấy/kiểm tra API key:**
1. Truy cập: https://runware.ai/
2. Đăng nhập vào tài khoản
3. Vào mục API Keys
4. Copy API key mới hoặc verify key hiện tại
5. Cập nhật trong `.env` hoặc `config.py`:
   ```
   RUNWARE_API_KEY=your_api_key_here
   ```

#### B. Test Connection
```bash
# Chạy script test connection
python3 test_runware_connection.py
```

Chọn option 1 (Quick test) để test nhanh connection.

#### C. Kiểm tra Network

1. **Test internet connection:**
   ```bash
   ping -c 3 google.com
   ```

2. **Test WebSocket connection:**
   ```bash
   # Kiểm tra có thể kết nối tới Runware API
   curl -I https://api.runware.ai
   ```

3. **Kiểm tra firewall:**
   ```bash
   # Ubuntu/Debian
   sudo ufw status

   # Nếu firewall block, có thể cần allow WebSocket connections
   ```

#### D. Giải pháp trong Code

Code đã được cập nhật với các cải tiến:

1. **Retry Logic:**
   - Tự động thử lại 3 lần khi connection timeout
   - Exponential backoff giữa các lần retry

2. **Reconnection:**
   - Tự động reconnect khi connection bị mất
   - Detect connection errors và retry

3. **Timeout Configuration:**
   - Connection timeout: 30s
   - Image generation timeout: 60s
   - Có thể tùy chỉnh nếu cần

#### E. Tối ưu hóa nếu vẫn gặp lỗi

1. **Tăng timeout trong code:**
   ```python
   # Trong runware_image_generator.py, line 56
   async def connect(self, timeout: int = 60, max_retries: int = 5):  # Tăng lên 60s, 5 retries
   ```

2. **Giảm concurrent requests:**
   - Nếu đang generate nhiều images cùng lúc, giảm số lượng xuống
   - Thêm delay giữa các requests

3. **Sử dụng proxy (nếu cần):**
   ```python
   # Có thể cần config proxy nếu ở môi trường corporate
   ```

### 2. `Could not connect to server. Ensure your API key is correct`

**Nguyên nhân:**
- API key sai hoặc không hợp lệ
- API key đã hết hạn
- Tài khoản Runware chưa được kích hoạt

**Giải pháp:**

1. **Verify API key:**
   - Đăng nhập vào https://runware.ai/
   - Kiểm tra API key còn hiệu lực
   - Tạo API key mới nếu cần

2. **Kiểm tra tài khoản:**
   - Đảm bảo tài khoản đã được verify
   - Kiểm tra còn credits/quota

3. **Update API key:**
   ```bash
   # Edit .env file
   nano .env

   # Hoặc edit config.py
   nano config.py
   ```

### 3. Connection bị mất giữa chừng (Connection Lost)

**Nguyên nhân:**
- Network không ổn định
- Runware server restart
- WebSocket timeout

**Giải pháp:**

Code đã tự động handle:
- Detect connection loss
- Auto-reconnect
- Retry failed requests

Nếu vẫn gặp vấn đề:
1. Kiểm tra network stability
2. Restart application
3. Liên hệ Runware support nếu vấn đề persist

## Testing Commands

### 1. Quick Connection Test
```bash
python3 test_runware_connection.py
# Chọn: 1
```

### 2. Full Test (với Image Generation)
```bash
python3 test_runware_connection.py
# Chọn: 2
```

### 3. Check Logs
```bash
# Logs sẽ hiển thị chi tiết về connection attempts, retries, errors
# Theo dõi để diagnose vấn đề
```

## Best Practices

1. **API Key Security:**
   - Không commit API key vào git
   - Sử dụng `.env` file
   - Thêm `.env` vào `.gitignore`

2. **Error Handling:**
   - Code đã có retry logic
   - Kiểm tra logs để xác định vấn đề
   - Monitor connection health

3. **Performance:**
   - Không generate quá nhiều images cùng lúc
   - Sử dụng cache để tránh regenerate
   - Monitor API quota/credits

## Contact Support

Nếu vấn đề vẫn tiếp diễn sau khi thử các giải pháp trên:

1. **Runware Support:**
   - Website: https://runware.ai/
   - Docs: https://docs.runware.ai/
   - Discord/Community forums

2. **Check Status:**
   - Kiểm tra Runware API status page
   - Xem có planned maintenance không

## Code Changes Summary

File `runware_image_generator.py` đã được cập nhật với:

1. **Connection improvements:**
   - Timeout configuration (30s default)
   - Retry logic (3 attempts with exponential backoff)
   - Better error messages

2. **Image generation improvements:**
   - Timeout for generation (60s)
   - Retry on failure (2 attempts)
   - Auto-reconnect on connection loss

3. **Validation:**
   - API key format validation
   - Connection health checks

4. **Logging:**
   - Detailed logging của mọi bước
   - Clear error messages để troubleshoot
