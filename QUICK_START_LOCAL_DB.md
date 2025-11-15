# 🚀 Quick Start - Local Database Edition

## Khởi động nhanh

### 1. Tạo dữ liệu mẫu (lần đầu)
```bash
python create_sample_data.py
```

Kết quả:
- ✅ 3 truyện mẫu
- ✅ 8 chương
- ✅ Database: stories.db

### 2. Chạy ứng dụng
```bash
python main.py
```

## Các chức năng mới

### ➕ Thêm truyện
1. Click button "➕ Thêm truyện" ở panel trái
2. Nhập thông tin:
   - Tên truyện (bắt buộc)
   - Tác giả (tùy chọn)
   - Thể loại (tùy chọn)
   - Mô tả (tùy chọn)
3. Click "💾 Lưu"

### ✏️ Sửa truyện
1. Chọn truyện trong danh sách
2. Click button "✏️ Sửa truyện"
3. Chỉnh sửa thông tin
4. Click "💾 Lưu"

### 🗑️ Xóa truyện
1. Chọn truyện trong danh sách
2. Click button "🗑️ Xóa truyện"
3. Xác nhận (⚠️ sẽ xóa cả các chương)

### ➕ Thêm chương
1. Chọn truyện ở panel trái
2. Click button "➕ Thêm chương" ở panel phải
3. Nhập thông tin:
   - Số chương (auto-suggest)
   - Tiêu đề (bắt buộc)
   - Nội dung (bắt buộc)
4. Click "💾 Lưu"

### ✏️ Sửa chương
1. Tick chọn 1 chương
2. Click button "✏️ Sửa chương"
3. Chỉnh sửa
4. Click "💾 Lưu"

### 🗑️ Xóa chương
1. Tick chọn chương cần xóa (có thể nhiều)
2. Click button "🗑️ Xóa chương"
3. Xác nhận

## Tính năng cũ vẫn hoạt động

✅ Tạo audio bằng Selenium
✅ Batch processing
✅ Chrome profiles
✅ Proxy management
✅ Channel intro
✅ Video generation

## Lợi ích

- 🚫 **Không cần login** - Khởi động trực tiếp
- 🚫 **Không cần API** - Hoạt động offline
- ⚡ **Nhanh hơn** - Database local
- 💾 **Dễ backup** - Copy file stories.db
- 🔒 **Riêng tư** - Dữ liệu trên máy local

## Files quan trọng

- `stories.db` - Database chứa tất cả dữ liệu
- `database_service.py` - Service layer
- `story_manager_dialog.py` - UI quản lý truyện
- `chapter_manager_dialog.py` - UI quản lý chương
- `main.py` - Main application (đã update)

## Backup & Restore

### Backup
```bash
cp stories.db stories_backup_$(date +%Y%m%d).db
```

### Restore
```bash
cp stories_backup_20231113.db stories.db
```

### Reset (xóa tất cả và bắt đầu lại)
```bash
rm stories.db
python create_sample_data.py
python main.py
```

## Migration từ API

Nếu bạn có data từ server API cũ:
```bash
python import_from_api.py
```

Nhập thông tin:
- API URL
- Username
- Password

Script sẽ tự động import tất cả stories và chapters.

## Xem thêm

- [CHANGES_SUMMARY.md](CHANGES_SUMMARY.md) - Tổng kết thay đổi
- [DATABASE_MIGRATION_README.md](DATABASE_MIGRATION_README.md) - Chi tiết migration

---

**Cần hỗ trợ?** Check logs trong thư mục `logs/`
