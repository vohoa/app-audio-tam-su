# 🔧 Cải thiện xử lý lỗi 403 Forbidden

## 📋 Tổng quan

Tài liệu này mô tả các cải thiện được thực hiện để xử lý lỗi **403 Forbidden** khi generate audio trên Google AI Studio.

---

## 🎯 Nguyên nhân lỗi 403

### 1. **Rate Limiting** ⚡
- Google giới hạn số lượng requests trong 1 khoảng thời gian
- Quá nhiều requests liên tiếp → bị tạm khóa

### 2. **Quota Exceeded** 📊
- Tài khoản đã sử dụng hết quota miễn phí
- Google AI Studio có giới hạn sử dụng hàng ngày/tháng

### 3. **Bot Detection** 🤖
- Google phát hiện hành vi automation
- Pattern không giống người dùng thật

### 4. **Policy Violation** 🚫
- Nội dung vi phạm chính sách của Google
- Có từ ngữ nhạy cảm, không phù hợp

### 5. **Authentication Issues** 🔐
- Session/Cookie hết hạn
- Không đủ quyền truy cập

---

## ✅ Các cải thiện đã thực hiện

### 1. **Network Monitoring** 🛡️

**Mục đích**: Phát hiện lỗi 403 ngay từ network layer

**Thay đổi**:
- Enable Performance Logging trong Chrome ([google_aistudio_automation_chrome.py:752](google_aistudio_automation_chrome.py#L752))
- Thêm method `_check_network_403_errors()` để monitor network requests ([google_aistudio_automation_chrome.py:2892](google_aistudio_automation_chrome.py#L2892))
- Tích hợp vào `wait_for_audio_generation()` ([google_aistudio_automation_chrome.py:2709](google_aistudio_automation_chrome.py#L2709))

**Code**:
```python
# Enable performance logging
options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

# Check network logs
def _check_network_403_errors(self) -> bool:
    logs = self.driver.get_log('performance')
    # Parse logs và detect 403 errors
```

**Lợi ích**:
- ✅ Phát hiện lỗi 403 sớm hơn
- ✅ Thông báo rõ ràng về nguyên nhân
- ✅ Dừng ngay khi phát hiện lỗi (tiết kiệm thời gian)

---

### 2. **Exponential Backoff** ⏳

**Mục đích**: Tăng thời gian chờ sau mỗi lần thất bại để tránh rate limiting

**Thay đổi**:
- Thêm logic exponential backoff trong `generate_audio_from_text()` ([google_aistudio_automation_chrome.py:3589](google_aistudio_automation_chrome.py#L3589))
- Phát hiện lỗi 403/rate limit và áp dụng backoff thông minh

**Code**:
```python
if '403' in error_msg.lower() or 'rate' in error_msg.lower():
    backoff_multiplier = 2 ** attempt  # 2^1, 2^2, 2^3... = 2s, 4s, 8s...
    wait_time = backoff_time * backoff_multiplier
    logger.warning(f"⏳ Đợi {wait_time}s trước khi thử lại...")
    time.sleep(wait_time)
```

**Cơ chế**:
- Lần 1 thất bại: Đợi 10s (5 × 2¹)
- Lần 2 thất bại: Đợi 20s (5 × 2²)
- Lần 3 thất bại: Đợi 40s (5 × 2³)

**Lợi ích**:
- ✅ Giảm khả năng bị rate limiting liên tiếp
- ✅ Tự động recovery sau khi Google lift ban
- ✅ Không waste requests khi đang bị block

---

### 3. **Human-like Delays** 🎭

**Mục đích**: Mô phỏng hành vi người dùng thật để tránh bot detection

**Thay đổi**:

#### a) Delay trước khi click Generate ([google_aistudio_automation_chrome.py:2650](google_aistudio_automation_chrome.py#L2650))
```python
# Random delay 2-5 giây trước khi click
pre_click_delay = 2.0 + (3.0 * random.random())
logger.info(f"⏳ Đợi {pre_click_delay:.1f}s trước khi click...")
time.sleep(pre_click_delay)
```

#### b) Tăng delay sau click ([google_aistudio_automation_chrome.py:2661](google_aistudio_automation_chrome.py#L2661))
```python
# Tăng từ 1-2s lên 2-4s
self._human_delay(2.0, 4.0)
```

#### c) Delays khi input text ([google_aistudio_automation_chrome.py:2372](google_aistudio_automation_chrome.py#L2372))
```python
# Delay trước khi click vào text field
self._human_delay(0.5, 1.5)

# Delay sau click, trước khi nhập text
self._human_delay(0.3, 0.8)
```

**Lợi ích**:
- ✅ Giảm bot detection score
- ✅ Hành vi giống người dùng thật hơn
- ✅ Tránh gửi requests quá nhanh

---

### 4. **Enhanced Error Detection** 🔍

**Mục đích**: Phát hiện và phân tích lỗi 403 chi tiết hơn

**Thay đổi**:
- Cải thiện `_check_generation_errors()` ([google_aistudio_automation_chrome.py:2831](google_aistudio_automation_chrome.py#L2831))
- Thêm keywords: 'forbidden', '403', 'rate limit', 'quota', 'permission denied'
- Phân tích và đưa ra giải pháp cụ thể cho từng loại lỗi

**Code**:
```python
if '403' in error_text.lower() or 'forbidden' in error_text.lower():
    logger.error("🚫 Lỗi 403 Forbidden - Nguyên nhân có thể:")
    logger.error("   1. Rate limiting: Quá nhiều requests...")
    logger.error("   2. Quota exceeded: Đã hết quota...")
    logger.error("   3. Policy violation: Nội dung vi phạm...")
    logger.error("💡 Giải pháp:")
    logger.error("   - Đợi 15-30 phút trước khi thử lại")
    logger.error("   - Kiểm tra quota tại: https://aistudio.google.com/")
```

**Lợi ích**:
- ✅ Thông báo lỗi rõ ràng, dễ hiểu
- ✅ Hướng dẫn giải pháp cụ thể
- ✅ Giúp debug nhanh hơn

---

## 📊 Kết quả

### Trước khi cải thiện:
- ❌ Lỗi 403 không được phát hiện rõ ràng
- ❌ Retry ngay lập tức → bị block tiếp
- ❌ Không có thông báo nguyên nhân cụ thể
- ❌ Delays giống nhau → dễ bị bot detection

### Sau khi cải thiện:
- ✅ Phát hiện lỗi 403 ngay từ network layer
- ✅ Exponential backoff tự động → giảm rate limiting
- ✅ Human-like delays → giảm bot detection
- ✅ Thông báo lỗi chi tiết với giải pháp cụ thể
- ✅ Tự động recovery sau khi Google lift ban

---

## 🎯 Khuyến nghị sử dụng

### 1. **Khi gặp lỗi 403 liên tiếp**:
```bash
# Đợi 15-30 phút trước khi thử lại
# Hoặc đổi sang profile/tài khoản khác
```

### 2. **Để tránh lỗi 403**:
- Không generate quá nhiều audio liên tiếp (khuyến nghị: tối đa 10-15/lần)
- Thêm delay dài hơn giữa các lần generate (2-5 phút)
- Sử dụng nhiều profile/tài khoản Google luân phiên

### 3. **Kiểm tra quota**:
- Truy cập: https://aistudio.google.com/
- Kiểm tra usage/quota hiện tại
- Nếu hết quota, đợi reset hoặc upgrade plan

### 4. **Kiểm tra nội dung**:
- Đảm bảo nội dung không vi phạm policy của Google
- Tránh từ ngữ nhạy cảm, không phù hợp
- Tham khảo: https://ai.google.dev/gemini-api/docs/safety-settings

---

## 🔄 Workflow mới

```
1. Khởi động browser → Random profile
2. Navigate to AI Studio
3. Input text → Human-like delays
4. Click Generate → Random delay 2-5s
5. Wait for audio → Monitor network 403
6. [Nếu 403] → Exponential backoff → Retry
7. [Nếu thành công] → Download audio
8. [Giữ browser alive] → Reuse cho lần sau
```

---

## 📝 File changes

| File | Lines | Changes |
|------|-------|---------|
| [google_aistudio_automation_chrome.py](google_aistudio_automation_chrome.py) | 752 | Enable performance logging |
| [google_aistudio_automation_chrome.py](google_aistudio_automation_chrome.py) | 2650-2662 | Random delays before/after click |
| [google_aistudio_automation_chrome.py](google_aistudio_automation_chrome.py) | 2372-2382 | Human-like delays in input |
| [google_aistudio_automation_chrome.py](google_aistudio_automation_chrome.py) | 2709-2712 | Integrate 403 check in wait loop |
| [google_aistudio_automation_chrome.py](google_aistudio_automation_chrome.py) | 2831-2876 | Enhanced error detection |
| [google_aistudio_automation_chrome.py](google_aistudio_automation_chrome.py) | 2892-2946 | Network 403 monitoring |
| [google_aistudio_automation_chrome.py](google_aistudio_automation_chrome.py) | 3589-3599 | Exponential backoff logic |

---

## 🧪 Testing

### Test case 1: Normal generation
```python
result = automation.generate_audio_from_text(
    text="Test content",
    use_fast_paste=True
)
# Expected: ✅ Success với human-like delays
```

### Test case 2: Rate limiting
```python
# Generate nhiều audio liên tiếp
for i in range(20):
    result = automation.generate_audio_from_text(text=f"Test {i}")
# Expected:
# - Lần 1-10: ✅ Success
# - Lần 11+: Có thể gặp 403 → Exponential backoff → Retry
```

### Test case 3: Policy violation
```python
result = automation.generate_audio_from_text(
    text="Nội dung vi phạm policy..."
)
# Expected:
# - 🚫 Detect 403 from network
# - ❌ Show policy violation message
```

---

## 📚 References

- [Google AI Studio](https://aistudio.google.com/)
- [Gemini API Safety Settings](https://ai.google.dev/gemini-api/docs/safety-settings)
- [HTTP Status Codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/403)
- [Exponential Backoff](https://en.wikipedia.org/wiki/Exponential_backoff)

---

**Tạo bởi**: Claude Code
**Ngày**: 2025-10-31
**Version**: 1.0.0
