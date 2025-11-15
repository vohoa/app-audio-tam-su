# 🏗️ Kiến trúc Ứng dụng Desktop Audio Generator

## 📊 Tổng quan

Ứng dụng Desktop này là một **Standalone Application** xử lý audio generation HOÀN TOÀN ĐỘC LẬP, chỉ kết nối API backend để lấy dữ liệu và upload kết quả.

```
┌─────────────────────────────────────────────────────────┐
│       DESKTOP APP (Standalone - Chạy trên máy user)     │
│  ┌───────────────────────────────────────────────────┐  │
│  │              PyQt5 UI Layer                       │  │
│  │  • Hiển thị danh sách truyện/chương              │  │
│  │  • Quản lý user interactions                      │  │
│  │  • Progress indicators                            │  │
│  └─────────────┬──────────────────┬──────────────────┘  │
│                │                  │                      │
│  ┌─────────────▼──────┐  ┌───────▼──────────────────┐  │
│  │   API Service      │  │ Selenium Audio Generator │  │
│  │  (READ/WRITE only) │  │  (LOCAL PROCESSING)      │  │
│  │                    │  │                          │  │
│  │  • Get Stories     │  │  • Chrome + ChromeDriver │  │
│  │  • Get Chapters    │  │  • Google AI Studio      │  │
│  │  • Upload Audio    │  │  • Generate Audio        │  │
│  │  • Delete Audio    │  │  • Save to local disk    │  │
│  └─────────────┬──────┘  └──────────────────────────┘  │
│                │                                         │
└────────────────┼─────────────────────────────────────────┘
                 │ HTTP REST API
                 │ (CHỈ data I/O)
                 ▼
┌─────────────────────────────────────────────────────────┐
│            BACKEND API SERVER (Optional)                │
│  ┌────────────────────────────────────────────────┐   │
│  │          Django REST API                       │   │
│  │  • Lưu trữ Stories/Chapters (Database)         │   │
│  │  • Nhận upload Audio files                     │   │
│  │  • KHÔNG xử lý Selenium/Audio generation       │   │
│  └────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Xác nhận các điểm chính

### Desktop App (Client - Standalone)

**✅ Cần cài đặt:**

- Python 3.8+
- PyQt5 (UI framework)
- requests (HTTP client)
- **Selenium** (xử lý audio)
- **Chrome Browser**
- **ChromeDriver**

**✅ Chức năng:**

1. **Hiển thị UI**

   - Danh sách truyện
   - Danh sách chương
   - Progress indicators
   - Batch processing UI

2. **Gọi API (CHỈ đọc/ghi dữ liệu)**

   - GET /api/stories/ → Lấy danh sách truyện
   - GET /api/chapters/?story=X → Lấy chapters
   - POST /api/chapters/{id}/upload-audio/ → Upload audio
   - DELETE /api/chapters/{id}/audio/ → Xóa audio

3. **Xử lý Selenium LOCAL (KHÔNG qua API)**
   - ✅ Khởi động Chrome với Selenium
   - ✅ Truy cập Google AI Studio
   - ✅ Generate audio từ text
   - ✅ Download audio về máy local
   - ✅ Upload audio lên server (nếu cần)

**❌ KHÔNG làm:**

- Không gọi API để generate audio
- Không phụ thuộc vào Celery worker
- Không cần backend xử lý Selenium

---

### Backend API (Server - Optional)

**✅ Chức năng:**

- Lưu trữ dữ liệu truyện/chương (Database)
- Trả về dữ liệu qua REST API
- Nhận upload audio files
- Lưu trữ audio files

**❌ KHÔNG làm:**

- KHÔNG xử lý Selenium
- KHÔNG cần Chrome/ChromeDriver
- KHÔNG cần Celery worker
- KHÔNG generate audio

---

## 📦 Dependencies

### Desktop App Requirements

```txt
# UI Framework
PyQt5==5.15.10

# HTTP Client (chỉ lấy data)
requests==2.31.0

# Configuration
python-decouple==3.8

# Selenium cho audio generation LOCAL
selenium==4.15.2
webdriver-manager==4.0.1
pyperclip==1.8.2
```

### System Requirements

**Desktop App cần:**

- ✅ Chrome Browser (latest)
- ✅ ChromeDriver (compatible với Chrome version)
- ✅ Python 3.8+

**Backend API cần:**

- ✅ Python + Django (chỉ lưu data)
- ❌ KHÔNG cần Chrome
- ❌ KHÔNG cần Selenium
- ❌ KHÔNG cần Celery

---

## 🔄 Workflow

### 1. Khởi động App

```
User chạy: python main.py
    ↓
Khởi tạo PyQt5 UI
    ↓
Kết nối API → Load danh sách truyện
    ↓
Hiển thị UI sẵn sàng
```

### 2. Tạo Audio cho một chương

```
User click "🤖 Generate Audio"
    ↓
Desktop App → Khởi động Selenium
    ↓
Selenium → Mở Chrome Browser
    ↓
Chrome → Truy cập Google AI Studio
    ↓
Selenium → Nhập text, click generate
    ↓
AI Studio → Tạo audio
    ↓
Selenium → Download audio về local
    ↓
Desktop App → Hiển thị "Hoàn thành"
    ↓
(Optional) Upload audio lên backend
```

### 3. Batch Processing

```
User chọn nhiều chương → Click "Batch Generate"
    ↓
Khởi tạo Selenium một lần
    ↓
For each chapter:
    ├─ Lấy content từ API
    ├─ Generate audio với Selenium
    ├─ Save to local
    └─ (Optional) Upload to backend
    ↓
Hiển thị kết quả tổng hợp
```

---

## 🌍 Deployment

### Chạy trên nhiều máy khác nhau

**Máy Windows:**

```cmd
1. Cài Python 3.8+
2. Cài Chrome Browser
3. cd desktop_audio_generator
4. run.bat
```

**Máy Mac:**

```bash
1. Cài Python 3.8+
2. Cài Chrome Browser
3. cd desktop_audio_generator
4. ./run.sh
```

**Máy Linux:**

```bash
1. Cài Python 3.8+
2. Cài Chrome Browser
3. cd desktop_audio_generator
4. ./run.sh
```

### ChromeDriver Auto-detect

App sử dụng `webdriver-manager` để tự động download ChromeDriver phù hợp:

- ✅ Tự động detect Chrome version
- ✅ Tự động download ChromeDriver tương thích
- ✅ Không cần cấu hình thủ công

---

## 📂 File Structure

```
desktop_audio_generator/
├── main.py                          # UI chính
├── api_service.py                   # API client (CHỈ đọc/ghi data)
├── selenium_audio_generator.py      # Selenium xử lý audio LOCAL
├── config.py                        # Configuration
├── requirements.txt                 # Python dependencies
├── .env.example                     # Config template
│
├── chrome_profiles/                 # Chrome profile data
│   └── desktop_app/                 # Session data
│
├── audio_downloads/                 # Audio files generated
│   └── *.mp3
│
└── docs/
    ├── README.md
    ├── ARCHITECTURE.md              # This file
    └── ...
```

---

## 🔧 Configuration

### File .env

```bash
# API Backend (CHỈ lấy dữ liệu)
API_BASE_URL=http://localhost:8000/api

# Chrome/ChromeDriver (tự động detect nếu để trống)
# CHROME_BINARY_PATH=/path/to/chrome
# CHROMEDRIVER_PATH=/path/to/chromedriver

# Audio settings
SELENIUM_HEADLESS=False  # True = ẩn browser
DEFAULT_VOICE_NAME=vi-VN-Neural2-A
DEFAULT_SPEAKING_RATE=1.0
```

---

## 🎯 Use Cases

### Use Case 1: Tạo audio cho một chương

```python
# User action: Click "Generate Audio" button
    ↓
ChapterWidget.generate_audio_local()
    ↓
SeleniumAudioGenerator.generate_audio(chapter_content)
    ↓
Google AI Studio → Generate audio
    ↓
Save to audio_downloads/chapter_123.mp3
    ↓
(Optional) APIService.upload_chapter_audio()
```

### Use Case 2: Batch processing

```python
# User action: Select 10 chapters → Click "Batch Generate"
    ↓
BatchAudioGenerationDialog.start_batch()
    ↓
Initialize Selenium once
    ↓
For chapter in selected_chapters:
    Generate audio locally
    Show progress
    ↓
Cleanup Selenium
```

---

## 🔐 Security & Performance

### Security

- ✅ Chrome profile riêng cho app
- ✅ Không lưu credentials trong code
- ✅ Session data isolated

### Performance

- ✅ Reuse Chrome instance cho batch
- ✅ Parallel processing có thể thêm sau
- ✅ Local processing = fast

---

## 🚀 Advantages

### ✅ Ưu điểm

1. **Hoàn toàn độc lập**

   - Không phụ thuộc backend Celery
   - Không cần backend xử lý Selenium
   - Chạy được offline (sau khi lấy data)

2. **Dễ deploy**

   - Cài đặt đơn giản
   - ChromeDriver auto-detect
   - Cross-platform (Win/Mac/Linux)

3. **Performance tốt**

   - Không qua network cho Selenium
   - Xử lý local = nhanh
   - Có thể cache data

4. **Dễ debug**
   - Thấy Chrome browser chạy
   - Log rõ ràng
   - Error dễ track

### ⚠️ Lưu ý

1. **Cần Chrome Browser**

   - Phải cài Chrome trên máy user
   - ChromeDriver tự động tải

2. **Resource intensive**

   - Chrome tốn RAM
   - Không phù hợp cho batch lớn (>50 chapters)

3. **Google AI Studio limits**
   - Rate limiting
   - Quota limits
   - Cần Google account

---

## 📊 Comparison

| Aspect                 | Desktop App (Standalone) | Backend API Processing |
| ---------------------- | ------------------------ | ---------------------- |
| **Selenium Location**  | ✅ Local (desktop)       | Backend server         |
| **Chrome Required**    | ✅ User machine          | Backend server         |
| **Network Dependency** | CHỈ lấy data             | Full dependency        |
| **Deployment**         | ✅ Easy (any machine)    | Server only            |
| **Performance**        | ✅ Fast (local)          | Network overhead       |
| **Scalability**        | Limited by user machine  | ✅ Scalable            |
| **Resource**           | User machine             | Server resources       |
| **Debugging**          | ✅ Easy (visible)        | Server logs            |

---

## 🎓 Summary

### Desktop App này:

✅ **XỬ LÝ SELENIUM LOCAL** (không qua API)
✅ **CẦN Chrome + ChromeDriver** trên máy user
✅ **GỌI API CHỈ để lấy/ghi dữ liệu**
✅ **ĐỘC LẬP hoàn toàn** về audio generation
✅ **DỄ DEPLOY** trên nhiều máy khác nhau
✅ **KHÔNG phụ thuộc** backend Celery worker

### Backend API chỉ:

✅ **LƯU TRỮ dữ liệu** (Stories/Chapters)
✅ **TRẢ VỀ dữ liệu** qua REST API
✅ **NHẬN upload** audio files
❌ **KHÔNG xử lý** Selenium
❌ **KHÔNG cần** Chrome/ChromeDriver

---

**Đây là kiến trúc Standalone Desktop Application chuẩn!** 🎉
