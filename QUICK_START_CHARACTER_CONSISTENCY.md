# Quick Start - Character Consistency

Hướng dẫn nhanh để sử dụng tính năng đồng bộ nhân vật qua các cảnh.

## ⚡ Không có characters.json?

**Không sao!** Hệ thống sẽ tự chạy ở **normal mode** (không có character consistency).

### Option 1: Tự động tạo template

```python
result = generate_images_from_json_sync(
    json_path="prompts.json",
    auto_create_characters_template=True  # <-- Tự động tạo template
)
```

### Option 2: Tạo thủ công

```python
from runware_image_generator import create_characters_json_template

create_characters_json_template("characters.json", "Your Story Name")
```

Sau khi có template → Edit với character info của bạn → Chạy lại!

---

## 📋 Chuẩn bị (Lần đầu)

### Bước 1: Tạo `characters.json`

```json
{
  "story_name": "Tu Tiên Chi Lộ",
  "characters": {
    "han_lap": {
      "full_name": "Hàn Lập",
      "aliases": ["Hàn", "Lập"],
      "reference_image": "characters/han_lap_ref.jpg"
    },
    "dong_cung_uyen": {
      "full_name": "Đông Cung Uyển",
      "aliases": ["Đông Cung", "Uyển"],
      "reference_image": "characters/dong_cung_uyen_ref.jpg"
    }
  }
}
```

### Bước 2: Tạo thư mục và lưu reference images

```bash
mkdir characters
# Copy ảnh reference vào đây (sẽ sinh ở lần đầu)
```

### Bước 3: Tạo prompts với metadata

```json
{
  "prompts": [
    {
      "id": 1,
      "content": "Hàn Lập đứng trước cổng thành",
      "characters": ["han_lap"]
    },
    {
      "id": 2,
      "content": "Đông Cung Uyển và Hàn Lập nói chuyện",
      "characters": ["dong_cung_uyen", "han_lap"]
    }
  ]
}
```

## 🚀 Sử dụng

### Cách 1: Từ Python code

```python
from runware_image_generator import generate_images_from_json_sync

# Tự động tìm characters.json trong cùng thư mục
result = generate_images_from_json_sync(
    json_path="prompts.json",
    model="civitai:118441@162380",
    width=768,
    height=1344,
    instant_id_strength=0.8  # 0.6-1.0, cao hơn = giống reference hơn
)

print(f"Generated: {result['generated_images']} images")
```

### Cách 2: Async version

```python
import asyncio
from runware_image_generator import RunwareImageGenerator

async def main():
    generator = RunwareImageGenerator()

    result = await generator.generate_images_from_json(
        json_path="prompts.json",
        characters_json_path="characters.json",  # Optional
        instant_id_strength=0.8
    )

    return result

result = asyncio.run(main())
```

## 📁 Cấu trúc thư mục

```
your_project/
├── characters.json          # Character database
├── characters/              # Reference images
│   ├── han_lap_ref.jpg
│   └── dong_cung_uyen_ref.jpg
├── prompts.json            # Prompts
└── output/                 # Generated images
```

## 🔄 Workflow thực tế

### Lần đầu gặp nhân vật mới:

1. **Không có reference** → Sinh ảnh bình thường
2. **Chọn ảnh đẹp nhất** → Lưu vào `characters/han_lap_ref.jpg`
3. **Cập nhật characters.json** → Thêm thông tin nhân vật

### Các lần sau:

- Hệ thống **tự động detect** nhân vật từ prompt
- **Tự động dùng** reference image
- Nhân vật **đồng nhất** qua các cảnh

## ⚙️ Tuning Parameters

### `instant_id_strength` (0.0 - 1.0)

- **0.6-0.7**: Linh hoạt, có biến đổi nhẹ
- **0.8**: Cân bằng ⭐ (khuyến nghị)
- **0.9-1.0**: Giống reference tối đa

## 📝 Tips

### 1. Chọn reference image tốt

- Ảnh rõ nét, khuôn mặt đầy đủ
- Front view hoặc 3/4 view
- Ánh sáng tốt, không bị che khuất

### 2. Metadata vs Auto-detect

**Metadata** (khuyến nghị):
```json
{"characters": ["han_lap"]}  ✅ Chính xác 100%
```

**Auto-detect**:
```json
"Hàn Lập đang đi"  ⚠️ Có thể sai nếu tên giống nhau
```

### 3. Nhiều nhân vật trong 1 cảnh

```json
{
  "content": "Hàn Lập và Đông Cung Uyển",
  "characters": ["han_lap", "dong_cung_uyen"]
}
```

⚠️ InstantID chỉ dùng reference đầu tiên → Sắp xếp nhân vật quan trọng lên đầu

## 🐛 Troubleshooting

### Reference không work?

✅ **Check:**
1. Đường dẫn file đúng chưa?
2. File có tồn tại không?
3. Tăng `instant_id_strength` lên 0.9

### Không detect được nhân vật?

✅ **Solutions:**
1. Dùng metadata thay vì auto-detect
2. Kiểm tra tên trong `aliases`
3. Check log: `Detected characters: [...]`

### Lỗi "IInstantID not found"?

```bash
pip install --upgrade runware
```

## 📚 Example Files

- `characters.json.example` - Character database mẫu
- `prompts_with_characters.json.example` - Prompts có metadata
- `CHARACTER_CONSISTENCY_GUIDE.md` - Hướng dẫn chi tiết

## 🎯 Test

```bash
python test_character_consistency.py
```

## ❓ Câu hỏi thường gặp

**Q: Có thể dùng cho nhiều story khác nhau?**
A: Có! Mỗi story có 1 `characters.json` riêng.

**Q: Reference image phải là ảnh đã generate?**
A: Có thể dùng bất kỳ ảnh nào, nhưng ảnh từ cùng model thường tốt hơn.

**Q: InstantID có hoạt động với mọi model?**
A: Hầu hết model SD1.5 và SDXL đều support.

**Q: Có tốn thêm credit không?**
A: Không, InstantID không tốn thêm credit.
