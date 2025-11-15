# Character Consistency Feature

Tính năng đồng bộ khuôn mặt nhân vật qua nhiều cảnh sử dụng InstantID của Runware API.

## 🎯 Vấn đề giải quyết

**Trước đây:**
- Sinh ảnh nhân vật "Hàn Lập" ở cảnh 1 → Khuôn mặt A
- Sinh ảnh nhân vật "Hàn Lập" ở cảnh 2 → Khuôn mặt B (khác hoàn toàn!)
- ❌ Không nhất quán qua các cảnh

**Bây giờ:**
- Sinh ảnh "Hàn Lập" lần đầu → Chọn ảnh đẹp làm reference
- Các lần sau → Tự động dùng reference → Khuôn mặt giống nhau!
- ✅ Nhất quán 100% qua tất cả các cảnh

## ⚡ Quick Start

### Không có characters.json? Không sao!

```python
from runware_image_generator import generate_images_from_json_sync

# Tự động tạo template
result = generate_images_from_json_sync(
    json_path="prompts.json",
    auto_create_characters_template=True  # <-- Magic!
)

# → Tạo file characters.json template
# → Edit template với character info
# → Chạy lại!
```

### Đã có characters.json

```python
result = generate_images_from_json_sync(
    json_path="prompts.json"
    # Tự động tìm và dùng characters.json
)
```

## 📚 Documentation

### 1. [QUICK_START_CHARACTER_CONSISTENCY.md](QUICK_START_CHARACTER_CONSISTENCY.md)
   - Quick start guide
   - Setup instructions
   - Code examples
   - Tips & tricks

### 2. [CHARACTER_CONSISTENCY_GUIDE.md](CHARACTER_CONSISTENCY_GUIDE.md)
   - Chi tiết đầy đủ
   - API reference
   - Troubleshooting
   - Advanced usage

### 3. [CHARACTER_CONSISTENCY_WORKFLOW.md](CHARACTER_CONSISTENCY_WORKFLOW.md)
   - Visual flowcharts
   - Workflow diagrams
   - Error handling
   - Configuration matrix

### 4. Example Files
   - `characters.json.example` - Character database template
   - `prompts_with_characters.json.example` - Prompts với metadata
   - `test_character_consistency.py` - Test suite
   - `demo_auto_template.py` - Demo script

## 🚀 Features

### ✅ Tự động tìm characters.json
```python
prompts.json
characters.json  # ← Tự động tìm trong cùng thư mục
```

### ✅ Auto-detect nhân vật
```python
# Từ metadata (khuyến nghị)
{"characters": ["han_lap"]}

# Từ text
"Hàn Lập đang đi trên đường"
# → Auto-detect: ["han_lap"]
```

### ✅ Tự động tạo template
```python
auto_create_characters_template=True
# → Tạo file characters.json với instructions
```

### ✅ Fallback graceful
- Không có characters.json → Normal mode
- Không có reference → Skip InstantID
- Lỗi → Retry hoặc continue

## 📖 Cách sử dụng chi tiết

### Bước 1: Tạo characters.json

**Option A: Tự động**
```python
from runware_image_generator import create_characters_json_template

create_characters_json_template("characters.json", "Tu Tiên Chi Lộ")
```

**Option B: Thủ công**
```json
{
  "story_name": "Tu Tiên Chi Lộ",
  "characters": {
    "han_lap": {
      "full_name": "Hàn Lập",
      "aliases": ["Hàn", "Lập"],
      "reference_image": "characters/han_lap_ref.jpg"
    }
  }
}
```

### Bước 2: Chuẩn bị prompts với metadata

```json
{
  "prompts": [
    {
      "id": 1,
      "content": "Hàn Lập đứng trước cổng thành",
      "characters": ["han_lap"]  // ← Metadata
    }
  ]
}
```

### Bước 3: Generate lần đầu

```python
result = generate_images_from_json_sync("prompts.json")
# → Sinh ảnh bình thường (chưa có reference)
```

### Bước 4: Chọn reference image

```bash
# Từ kết quả, chọn ảnh đẹp nhất
cp output/prompt_1_0.png characters/han_lap_ref.jpg
```

### Bước 5: Generate các lần sau

```python
result = generate_images_from_json_sync("prompts.json")
# → Tự động dùng reference → Khuôn mặt giống nhau!
```

## 🎛️ Configuration

### instant_id_strength (0.0 - 1.0)

```python
result = generate_images_from_json_sync(
    json_path="prompts.json",
    instant_id_strength=0.8  # Default
)
```

| Value | Behavior | Use Case |
|-------|----------|----------|
| 0.6-0.7 | Linh hoạt | Muốn đa dạng, chấp nhận sai lệch nhẹ |
| 0.8 | Cân bằng ⭐ | Khuyến nghị cho hầu hết trường hợp |
| 0.9-1.0 | Nghiêm ngặt | Cần giống reference tối đa |

## 🏗️ Architecture

```
CharacterManager
├─ Load characters.json
├─ Detect characters (metadata or text)
├─ Resolve reference image paths
└─ Return character refs

RunwareImageGenerator
├─ Use CharacterManager
├─ Get character references
├─ Create IInstantID
└─ Generate with InstantID
```

## 📊 Performance

- **No overhead** nếu không có characters.json (normal mode)
- **No extra cost** - InstantID không tốn thêm credit
- **Cache aware** - Skip ảnh đã generate
- **Parallel safe** - Multiple prompts processed efficiently

## 🐛 Troubleshooting

### Không detect được nhân vật?

✅ **Solutions:**
1. Dùng metadata thay vì auto-detect
2. Kiểm tra `aliases` trong characters.json
3. Check log: `Detected characters: [...]`

### Reference không work?

✅ **Check:**
1. File có tồn tại? `ls characters/han_lap_ref.jpg`
2. Đường dẫn đúng trong characters.json?
3. Thử tăng `instant_id_strength` lên 0.9

### Lỗi "IInstantID not found"?

```bash
pip install --upgrade runware
```

## 🧪 Testing

```bash
# Test character detection
python test_character_consistency.py

# Demo auto-template creation
python demo_auto_template.py
```

## 📝 Best Practices

### 1. Reference Image Quality
- ✅ Clear, front-facing or 3/4 view
- ✅ Good lighting
- ✅ Face visible and unobstructed
- ❌ Side view, dark, blurry

### 2. Character Naming
```json
// Good
"han_lap": {
  "full_name": "Hàn Lập",
  "aliases": ["Hàn", "Lập", "Han Lap"]
}

// Bad - too generic
"character_1": {
  "full_name": "Character"
}
```

### 3. Metadata vs Auto-detect
```json
// Best - Metadata (100% accurate)
{"characters": ["han_lap"]}

// OK - Auto-detect (may have false positives)
"Hàn Lập đang đi"
```

### 4. Multiple Characters
```json
// InstantID uses first character
{
  "characters": ["han_lap", "dong_cung_uyen"]
}
// → Uses han_lap as reference
// → dong_cung_uyen may vary slightly
```

## 🌟 Use Cases

### Story with Multiple Chapters
```
story/
├── characters.json          # Shared across all chapters
├── chapter_1/
│   └── prompts.json
├── chapter_2/
│   └── prompts.json
└── chapter_3/
    └── prompts.json

# Character faces consistent across ALL chapters!
```

### Evolving Character Database
```python
# Chapter 1: Meet Han Lap
# → Generate, pick reference, save

# Chapter 3: New character Dong Cung Uyen
# → Generate, pick reference, add to characters.json

# Chapter 5: Another new character
# → Repeat process
```

## 🔮 Future Enhancements

- [ ] Support multiple character references per prompt
- [ ] Auto-select best reference from generated batch
- [ ] Character variation presets (age, mood, style)
- [ ] UI for managing character database

## 📦 Requirements

```bash
pip install runware  # For InstantID support
pip install unidecode  # For character name normalization (optional)
```

## 💬 FAQ

**Q: Có thể dùng ảnh từ nguồn khác làm reference?**
A: Có, nhưng ảnh từ cùng model thường cho kết quả tốt hơn.

**Q: InstantID có tốn thêm credit?**
A: Không, InstantID free và không tốn thêm credit.

**Q: Có thể thay đổi reference giữa chừng?**
A: Có, chỉ cần update `reference_image` path trong characters.json.

**Q: Nếu có 2 nhân vật trong 1 cảnh?**
A: InstantID hiện chỉ dùng reference đầu tiên. Sắp xếp nhân vật quan trọng lên đầu.

**Q: Model nào support InstantID?**
A: Hầu hết SD1.5 và SDXL models đều support.

## 🤝 Contributing

Có ý tưởng hoặc gặp bug? Welcome contributions!

## 📄 License

MIT License - Use freely in your projects!

---

**Happy generating! 🎨✨**

*Nhân vật của bạn giờ đây sẽ có khuôn mặt nhất quán qua tất cả các cảnh!*
