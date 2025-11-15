# 🚀 Quick Start Guide

## Cài đặt nhanh

### Linux/Mac:

```bash
cd desktop_audio_generator
./run.sh
```

### Windows:

```cmd
cd desktop_audio_generator
run.bat
```

## Hoặc cài đặt thủ công:

```bash
# 1. Tạo virtual environment
python3 -m venv venv

# 2. Kích hoạt virtual environment
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate  # Windows

# 3. Cài đặt dependencies
pip install -r requirements.txt

# 4. Copy file cấu hình
cp .env.example .env

# 5. (Optional) Test API connection
python test_api.py

# 6. Chạy ứng dụng
python main.py
```

## Kiểm tra kết nối API

Trước khi chạy ứng dụng chính, bạn có thể test API:

```bash
python test_api.py
```

Nếu thành công, bạn sẽ thấy:

```
✅ All tests passed! API is working correctly.
```

## Cấu hình API

Mở file `.env` và chỉnh sửa:

```bash
API_BASE_URL=http://localhost:7777/api
```

Đổi thành địa chỉ API server của bạn nếu cần.

## Giao diện ứng dụng

```
┌─────────────────────────────────────────────────────────────┐
│  🎵 Audio Generator - Desktop App                           │
├──────────────────┬──────────────────────────────────────────┤
│ 📚 Danh sách     │ 📖 Story Name - Author                   │
│    truyện        │ ─────────────────────────────────────    │
│                  │ [ ] 📋 Chọn tất cả  🤖 Tạo tuần tự (0)  │
│ 📖 Truyện 1      │ ─────────────────────────────────────    │
│ 📖 Truyện 2      │                                          │
│ 📖 Truyện 3      │ ☐ Chương 1: Tiêu đề                     │
│                  │   [TTS] [Selenium] [AI] [Upload] [Xem]  │
│                  │                                          │
│                  │ ☐ Chương 2: Tiêu đề 🎵                   │
│ [🔄 Làm mới]     │   [TTS] [Selenium] [AI] [Upload] [▶]   │
│                  │                                          │
│                  │ ◀ Trước | Trang 1 | Sau ▶               │
└──────────────────┴──────────────────────────────────────────┘
```

## Các tính năng chính

### 1️⃣ Tạo audio cho một chương

- Click vào truyện bên trái
- Chọn chương bên phải
- Click nút "🎵 TTS Audio" hoặc "🤖 Selenium"

### 2️⃣ Tạo audio cho nhiều chương (Batch)

- Tick checkbox ở nhiều chương
- Click "🤖 Tạo audio tuần tự (n)"
- Xác nhận và theo dõi tiến độ

### 3️⃣ Upload audio từ máy

- Click "📁 Upload Audio"
- Chọn file MP3/WAV/M4A
- Đợi upload hoàn thành

### 4️⃣ Nghe audio

- Click "▶️ Phát" để mở trong browser

## Troubleshooting

### ❌ Không kết nối được API

```bash
# Kiểm tra Django API đang chạy
curl http://localhost:7777/api/stories/

# Hoặc chạy test script
python test_api.py
```

### ❌ PyQt5 lỗi trên Linux

```bash
sudo apt-get install python3-pyqt5
pip install --upgrade PyQt5
```

### ❌ Timeout khi tạo audio

Chỉnh trong `.env`:

```
MAX_POLL_ATTEMPTS=60  # Tăng lên
```

## Support

Xem thêm chi tiết trong `README.md`
