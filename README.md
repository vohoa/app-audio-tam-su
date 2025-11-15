# 🎵 Desktop Audio Generator - Standalone App

## 📖 Giới thiệu

Ứng dụng desktop **hoàn toàn độc lập** để tạo audio cho các chương truyện, sử dụng Google AI Studio thông qua Selenium automation.

### ✨ Đặc điểm

- ✅ **Standalone**: Xử lý Selenium LOCAL, không phụ thuộc backend
- ✅ **Cross-platform**: Windows, macOS, Linux
- ✅ **Auto-setup**: ChromeDriver tự động download
- ✅ **UI thân thiện**: PyQt5 với giao diện trực quan
- ✅ **Batch processing**: Xử lý nhiều chương cùng lúc
- 🎲 **Profile Pool**: Random luân phiên profiles để tránh antibot (NEW!)

---

## 🏗️ Kiến trúc

```
Desktop App (Standalone)
├── UI Layer (PyQt5)
│   └── Hiển thị truyện/chương, quản lý tác vụ
│
├── API Service
│   └── CHỈ lấy/ghi dữ liệu từ backend
│
└── Selenium Audio Generator ⭐
    ├── Chrome + ChromeDriver (LOCAL)
    ├── Google AI Studio automation
    └── Generate audio → Save local → Upload backend
```

**Backend API chỉ làm:**

- Lưu trữ dữ liệu Stories/Chapters
- Trả về dữ liệu qua REST API
- Nhận upload audio files

**Backend KHÔNG làm:**

- ❌ KHÔNG xử lý Selenium
- ❌ KHÔNG cần Chrome/ChromeDriver
- ❌ KHÔNG cần Celery worker

👉 Xem chi tiết: [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 📋 Yêu cầu hệ thống

### Bắt buộc

- ✅ **Python 3.8+**
- ✅ **Chrome Browser** (latest stable)
- ✅ **ChromeDriver** (tự động tải hoặc cài thủ công)

### Optional

- Backend API (Django REST) để lấy dữ liệu truyện

---

## 🚀 Quick Start

### Linux/Mac

```bash
cd desktop_audio_generator
./run.sh
```

### Windows

```cmd
cd desktop_audio_generator
run.bat
```

Script sẽ tự động:

1. Tạo virtual environment
2. Cài đặt dependencies
3. Tạo file .env từ template
4. Chạy ứng dụng

---

## 📦 Cài đặt Manual

### 1. Clone hoặc copy folder

```bash
cd /path/to/aistudio-generate-speech/desktop_audio_generator
```

### 2. Cài đặt Chrome Browser

**Windows/Mac:**

- Tải từ: https://www.google.com/chrome/

**Linux:**

```bash
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
```

👉 Chi tiết: [SETUP_GUIDE.md](SETUP_GUIDE.md)

### 3. Setup Python environment

```bash
# Tạo virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 4. Configuration

```bash
# Copy config template
cp .env.example .env

# Edit config (optional)
nano .env  # Hoặc text editor khác
```

### 5. Test setup

```bash
# Test Chrome + ChromeDriver
python test_chrome_setup.py

# Test API connection
python test_api.py
```

### 6. Run app

```bash
python main.py
```

---

## ⚙️ Configuration

File `.env`:

```bash
# ============================================
# API Backend (CHỈ lấy dữ liệu)
# ============================================
API_BASE_URL=http://localhost:8000/api
API_TIMEOUT=30

# ============================================
# Selenium Audio Generation (LOCAL)
# ============================================

# Chrome/ChromeDriver paths (tự động detect nếu để trống)
# CHROME_BINARY_PATH=/path/to/chrome
# CHROMEDRIVER_PATH=/path/to/chromedriver

# Audio settings
SELENIUM_HEADLESS=False  # True = ẩn browser
DEFAULT_VOICE_NAME=vi-VN-Neural2-A
DEFAULT_SPEAKING_RATE=1.0

# ============================================
# UI Settings
# ============================================
CHAPTERS_PER_PAGE=50
WINDOW_WIDTH=1400
WINDOW_HEIGHT=900
```

---

## 🎯 Tính năng

### 📚 Quản lý Truyện & Chương

- Hiển thị danh sách truyện
- Xem danh sách chương (phân trang 50/trang)
- Xem nội dung chi tiết chương
- Badge hiển thị trạng thái audio

### 🎵 Tạo Audio (LOCAL với Selenium)

- **Generate Audio**: Click button → Selenium xử lý LOCAL
- **Batch Processing**: Chọn nhiều chương → Tạo tuần tự

### 🎨 Tạo Image Prompts & Video (NEW!)

- **Auto JSON Prompts**: Tự động tạo image prompts từ nội dung chương (Perplexity AI)
- **Runware Image Generation**: Tạo ảnh từ prompts sử dụng Runware API
- **Video Generation**: Tự động ghép ảnh + audio thành video (MoviePy)
- **Batch Processing**: Tạo video cho nhiều chương cùng lúc
- 📹 **Output**: Video MP4 với ảnh minh họa + audio đồng bộ

👉 Xem chi tiết: [VIDEO_GENERATION_GUIDE.md](VIDEO_GENERATION_GUIDE.md)
- **Progress Tracking**: Theo dõi tiến độ real-time
- **Auto Upload**: Tự động upload lên backend (optional)

### 🎲 Profile Pool - Tránh Antibot (NEW!)

- **Multi-Profile Management**: Quản lý nhiều Chrome profiles
- **Random Selection**: Tự động random profile mỗi lần generate
- **Usage Tracking**: Theo dõi số lần sử dụng mỗi profile
- **Active/Inactive Toggle**: Bật/tắt profiles linh hoạt
- **Export/Import**: Backup & restore pool configuration

👉 **Chi tiết**: [PROFILE_POOL_GUIDE.md](PROFILE_POOL_GUIDE.md)

### 📁 Quản lý File

- Upload audio file từ máy tính
- Delete audio đã có
- Play audio trong browser
- Audio lưu local: `audio_downloads/`

---

## 📊 Workflow

### 1. Tạo audio cho một chương

```
User click "🤖 Generate Audio"
    ↓
App khởi động Chrome với Selenium (LOCAL)
    ↓
Selenium truy cập Google AI Studio
    ↓
Generate audio từ text
    ↓
Download về audio_downloads/
    ↓
(Optional) Upload lên backend server
    ↓
Hiển thị "✅ Hoàn thành"
```

### 2. Batch processing

```
User chọn 10 chương → Click "Batch Generate"
    ↓
Khởi động Selenium một lần
    ↓
For each chapter:
  ├─ Lấy content từ API
  ├─ Generate audio LOCAL
  ├─ Save to audio_downloads/
  └─ Upload to backend
    ↓
Hiển thị tổng kết
```

---

## 🖥️ Giao diện

```
┌─────────────────────────────────────────────────────────┐
│  🎵 Audio Generator - Desktop App           [_ □ ✕]    │
├─────────────┬───────────────────────────────────────────┤
│ 📚 Stories  │ 📖 Story Name - Author                    │
│             │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│ Story 1 ◀   │ ☐ Chọn tất cả  🤖 Generate Batch (0)    │
│ Story 2     │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│ Story 3     │                                           │
│ ...         │ ☐ Chương 1: Title                         │
│             │   [🤖 Generate] [📁 Upload] [📄 View]     │
│ [🔄 Refresh]│   ⏳ Đang xử lý...                         │
│             │                                           │
│             │ ☑ Chương 2: Title 🎵                       │
│             │   [🤖 Generate] [▶️ Play] [📄 View]        │
│             │   ✅ Hoàn thành!                           │
│             │                                           │
│             │ ◀ Prev | Page 1/10 | Next ▶               │
└─────────────┴───────────────────────────────────────────┘
```

---

## 🔧 Troubleshooting

### ❌ Chrome/ChromeDriver issues

```bash
# Test setup
python test_chrome_setup.py

# Reinstall webdriver-manager
pip install --upgrade webdriver-manager

# Xem hướng dẫn chi tiết
cat SETUP_GUIDE.md
```

### ❌ API connection issues

```bash
# Test API
python test_api.py

# Check backend is running
curl http://localhost:8000/api/stories/

# Update API URL in .env
API_BASE_URL=http://your-server:8000/api
```

### ❌ Selenium issues

```bash
# Run in non-headless mode to see browser
# Edit .env:
SELENIUM_HEADLESS=False

# Check Chrome version matches ChromeDriver
google-chrome --version
chromedriver --version
```

👉 Xem thêm: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 📂 Cấu trúc File

```
desktop_audio_generator/
├── main.py                          # ⭐ Main application
├── api_service.py                   # API client (data only)
├── selenium_audio_generator.py      # ⭐ Selenium LOCAL processor
├── config.py                        # Configuration loader
├── requirements.txt                 # Python dependencies
├── .env.example                     # Config template
├── .env                             # Your config (create this)
│
├── run.sh                           # Linux/Mac launcher
├── run.bat                          # Windows launcher
├── test_api.py                      # Test API connection
├── test_chrome_setup.py             # Test Chrome/Driver setup
│
├── audio_downloads/                 # Generated audio files
├── chrome_profiles/                 # Chrome session data
│   └── desktop_app/
│
└── docs/
    ├── README.md                    # This file
    ├── ARCHITECTURE.md              # Architecture details
    ├── SETUP_GUIDE.md               # Chrome/Driver setup
    ├── QUICKSTART.md                # 5-minute guide
    ├── TROUBLESHOOTING.md           # Problem solving
    └── ...
```

---

## 📚 Documentation

| File                                     | Description                     |
| ---------------------------------------- | ------------------------------- |
| [README.md](README.md)                   | Main documentation (this file)  |
| [ARCHITECTURE.md](ARCHITECTURE.md)       | ⭐ System architecture & design |
| [SETUP_GUIDE.md](SETUP_GUIDE.md)         | Chrome/ChromeDriver setup       |
| [QUICKSTART.md](QUICKSTART.md)           | Get started in 5 minutes        |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Fix common issues               |
| [FILE_STRUCTURE.md](FILE_STRUCTURE.md)   | Code organization               |
| [INDEX.md](INDEX.md)                     | Documentation index             |

---

## 🎓 Use Cases

### Use Case 1: Tạo audio một chương

1. Mở app: `./run.sh`
2. Chọn truyện từ danh sách bên trái
3. Tìm chương cần tạo audio
4. Click "🤖 Generate Audio"
5. Đợi Selenium xử lý (hiện progress)
6. Done! Audio sẽ được lưu local và upload lên server

### Use Case 2: Batch 10 chương

1. Chọn truyện
2. Tick checkbox 10 chương
3. Click "🤖 Generate Batch (10)"
4. Xác nhận trong dialog
5. Theo dõi tiến độ từng chương
6. Done! Tất cả audio đã được tạo

### Use Case 3: Upload audio có sẵn

1. Chọn truyện & chương
2. Click "📁 Upload"
3. Chọn file MP3/WAV/M4A
4. Done! Audio được upload lên server

---

## 🔐 Requirements.txt

```txt
# UI Framework
PyQt5==5.15.10

# HTTP Client
requests==2.31.0

# Configuration
python-decouple==3.8

# Selenium for LOCAL audio generation ⭐
selenium==4.15.2
webdriver-manager==4.0.1
pyperclip==1.8.2
```

---

## 🌟 Advantages

### ✅ Ưu điểm

1. **Hoàn toàn độc lập**

   - Không phụ thuộc backend Celery
   - Xử lý Selenium LOCAL
   - Chạy được trên bất kỳ máy nào

2. **Dễ cài đặt**

   - Auto-setup scripts
   - ChromeDriver tự động download
   - Cross-platform support

3. **Performance tốt**

   - Xử lý LOCAL = nhanh
   - Không có network overhead cho Selenium
   - Có thể cache data

4. **Dễ debug**
   - Nhìn thấy Chrome chạy
   - Logs rõ ràng
   - Error dễ track

### ⚠️ Lưu ý

1. **Cần Chrome Browser**: Phải cài Chrome trên máy user
2. **Resource intensive**: Chrome tốn RAM (~500MB+)
3. **Google AI Studio limits**: Rate limiting & quota
4. **Batch size**: Không nên xử lý >20-30 chapters cùng lúc

---

## 🔄 Comparison với Backend Processing

| Aspect            | Desktop (Standalone)    | Backend API         |
| ----------------- | ----------------------- | ------------------- |
| Selenium Location | ✅ LOCAL (user machine) | Server              |
| Chrome Required   | ✅ User machine         | Server              |
| Setup Complexity  | Medium (cài Chrome)     | High (server setup) |
| Deployment        | ✅ Easy (any machine)   | Server only         |
| Resource Usage    | User's machine          | Server resources    |
| Performance       | ✅ Fast (no network)    | Network overhead    |
| Scalability       | Limited by user PC      | ✅ Scalable         |
| Cost              | ✅ Free (user's PC)     | Server costs        |

---

## 🚧 Future Enhancements

### Planned

- [ ] Parallel processing (nhiều Chrome instances)
- [ ] Resume batch processing
- [ ] Built-in audio player
- [ ] Chapter editing
- [ ] Export/import data
- [ ] Dark mode

### Ideas

- [ ] Queue management system
- [ ] Cloud storage integration
- [ ] Multiple voice profiles
- [ ] Audio quality settings
- [ ] Keyboard shortcuts
- [ ] System tray integration

---

## 📞 Support

**Gặp vấn đề?**

1. Đọc [QUICKSTART.md](QUICKSTART.md)
2. Chạy `python test_chrome_setup.py`
3. Chạy `python test_api.py`
4. Xem [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
5. Check Django logs (nếu có backend)

**File cấu hình:**

- `.env` - Settings chính
- `SETUP_GUIDE.md` - Chrome/Driver setup
- `ARCHITECTURE.md` - System design

---

## 📄 License

Part of the AI Studio Generate Speech project.

---

## 🎉 Summary

Desktop Audio Generator là ứng dụng **STANDALONE** với:

✅ **Selenium xử lý LOCAL** (không qua API)  
✅ **Cần Chrome + ChromeDriver** trên máy user  
✅ **API chỉ để lấy/ghi dữ liệu**  
✅ **Hoàn toàn độc lập** về audio generation  
✅ **Cross-platform** (Windows/Mac/Linux)  
✅ **Easy deployment** trên nhiều máy

**Start now:**

```bash
./run.sh  # Linux/Mac
run.bat   # Windows
```

🚀 **Happy audio generating!**
