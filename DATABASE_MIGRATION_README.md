# 🔄 Chuyển đổi sang Database Local

## Tổng quan

Ứng dụng đã được thiết kế lại để sử dụng **SQLite database local** thay vì gọi API từ server. Điều này giúp:

- ✅ **Hoạt động offline** - Không cần kết nối internet để quản lý truyện
- ✅ **Tốc độ nhanh hơn** - Truy vấn database local nhanh hơn API calls
- ✅ **Đơn giản hóa** - Không cần đăng nhập, không cần authentication
- ✅ **Quản lý dễ dàng** - Thêm/sửa/xóa truyện và chương trực tiếp trong app

## Các thay đổi chính

### 1. Database Service (`database_service.py`)

File mới thay thế `api_service.py`:
- Sử dụng SQLite để lưu trữ dữ liệu
- Hỗ trợ đầy đủ CRUD operations cho stories và chapters
- Database file: `stories.db` (tự động tạo khi chạy app lần đầu)

**Schema:**
- **stories**: id, name, description, author, category, cover_image, created_at, updated_at
- **chapters**: id, story_id, chapter_number, title, content, audio_file, audio_duration, created_at, updated_at

### 2. Giao diện quản lý mới

#### Quản lý truyện (`story_manager_dialog.py`)
- ➕ **Thêm truyện mới**: Button "➕ Thêm truyện" ở panel bên trái
- ✏️ **Sửa truyện**: Button "✏️ Sửa truyện" (chọn truyện trước)
- 🗑️ **Xóa truyện**: Button "🗑️ Xóa truyện" (sẽ xóa cả các chương)

#### Quản lý chương (`chapter_manager_dialog.py`)
- ➕ **Thêm chương mới**: Button "➕ Thêm chương" ở panel bên phải
- ✏️ **Sửa chương**: Button "✏️ Sửa chương" (tick chọn 1 chương)
- 🗑️ **Xóa chương**: Button "🗑️ Xóa chương" (tick chọn chương cần xóa)

### 3. Loại bỏ authentication

- ❌ Không còn màn hình đăng nhập
- ❌ Không còn menu "Đăng xuất"
- ✅ App khởi động trực tiếp và load stories từ database

## Hướng dẫn sử dụng

### Khởi động ứng dụng

```bash
python main.py
```

App sẽ tự động:
1. Tạo database `stories.db` nếu chưa có
2. Load danh sách truyện từ database

### Quản lý truyện

1. **Thêm truyện mới:**
   - Click button "➕ Thêm truyện"
   - Nhập tên truyện (bắt buộc)
   - Nhập tác giả, thể loại, mô tả (tùy chọn)
   - Click "💾 Lưu"

2. **Sửa truyện:**
   - Chọn truyện trong danh sách
   - Click button "✏️ Sửa truyện"
   - Chỉnh sửa thông tin
   - Click "💾 Lưu"

3. **Xóa truyện:**
   - Chọn truyện trong danh sách
   - Click button "🗑️ Xóa truyện"
   - Xác nhận xóa (⚠️ Sẽ xóa cả các chương)

### Quản lý chương

1. **Thêm chương mới:**
   - Chọn truyện ở panel bên trái
   - Click button "➕ Thêm chương"
   - Nhập số chương (tự động gợi ý)
   - Nhập tiêu đề và nội dung (bắt buộc)
   - Click "💾 Lưu"

2. **Sửa chương:**
   - Tick chọn 1 chương trong danh sách
   - Click button "✏️ Sửa chương"
   - Chỉnh sửa thông tin
   - Click "💾 Lưu"

3. **Xóa chương:**
   - Tick chọn chương cần xóa (có thể chọn nhiều)
   - Click button "🗑️ Xóa chương"
   - Xác nhận xóa

### Tạo audio cho chương

Chức năng tạo audio vẫn hoạt động như cũ:
1. Chọn truyện
2. Tick chọn chương cần tạo audio
3. Click "🤖 Tạo audio tuần tự"
4. Audio sẽ được lưu vào database sau khi tạo xong

## Migration từ phiên bản cũ

Nếu bạn đang sử dụng phiên bản cũ với API:

### Backup files

```bash
cp main.py main_old.py
cp api_service.py api_service_backup.py
```

### Các file đã thay đổi

- ✏️ **main.py** - Updated to use DatabaseService
- ➕ **database_service.py** - NEW: Database service layer
- ➕ **story_manager_dialog.py** - NEW: Story management UI
- ➕ **chapter_manager_dialog.py** - NEW: Chapter management UI
- 🗄️ **stories.db** - NEW: SQLite database file (auto-created)

### Import data từ API (nếu cần)

Tạo script để import data từ API sang database:

```python
from api_service import APIService
from database_service import DatabaseService

api = APIService()
api.login('username', 'password')

db = DatabaseService()

# Import stories
stories = api.get_stories()
for story in stories:
    db_story = db.create_story(
        name=story['name'],
        description=story.get('description', ''),
        author=story.get('author', ''),
        category=story.get('category', '')
    )

    # Import chapters for this story
    chapters = api.get_chapters_by_story(story['id'])
    for chapter in chapters['results']:
        db.create_chapter(
            story_id=db_story['id'],
            title=chapter['title'],
            content=chapter['content'],
            chapter_number=chapter.get('chapter_number')
        )

print("✅ Import completed!")
```

## Troubleshooting

### Database bị lỗi

Xóa và tạo lại database:
```bash
rm stories.db
python main.py  # Sẽ tạo database mới
```

### Lỗi "no such table"

Database chưa được khởi tạo đúng. Xóa file `stories.db` và chạy lại app.

### Muốn backup database

```bash
cp stories.db stories_backup_$(date +%Y%m%d).db
```

### Restore database

```bash
cp stories_backup_20231113.db stories.db
```

## Các tính năng vẫn hoạt động

- ✅ Tạo audio bằng Selenium (Google AI Studio)
- ✅ Batch processing nhiều chương
- ✅ Quản lý Chrome profiles
- ✅ Quản lý proxy
- ✅ Channel intro management
- ✅ Video generation với RunWare API
- ✅ Tất cả settings và preferences

## Lợi ích của database local

1. **Không phụ thuộc server** - App hoạt động hoàn toàn offline
2. **Tốc độ cao** - Truy vấn local nhanh hơn API calls nhiều lần
3. **Dễ backup** - Chỉ cần copy file `stories.db`
4. **Không giới hạn** - Không bị rate limiting hay timeout từ server
5. **Privacy** - Dữ liệu lưu hoàn toàn trên máy local

## Support

Nếu gặp vấn đề:
1. Check logs trong thư mục `logs/`
2. Kiểm tra file `stories.db` có tồn tại không
3. Thử xóa database và tạo lại
4. Check quyền ghi file trong thư mục project

---

**Version**: 2.0.0 - Database Local Edition
**Updated**: 2025-11-13
