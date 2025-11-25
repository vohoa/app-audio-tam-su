# Hướng Dẫn Sử Dụng LoRA Configuration

## Giới thiệu

LoRA (Low-Rank Adaptation) cho phép bạn tùy chỉnh phong cách hình ảnh được tạo ra mà không cần train lại toàn bộ model. Điều này rất hữu ích cho việc tạo minh họa truyện thiếu nhi với phong cách nhất quán.

## Cấu hình trong .env

### Cấu hình mặc định

Trong file `.env`, thêm hoặc chỉnh sửa dòng sau:

```bash
# Runware LoRA Configuration (JSON format)
# Format: [{"model": "civitai:id@version", "weight": 1.0}]
# Children illustration style LoRA
RUNWARE_LORA_CONFIG=[{"model": "civitai:1259001@1419583", "weight": 1.0}]
```

### Giải thích tham số

- **model**: ID của LoRA model từ Civitai hoặc Runware
  - Format: `civitai:ID@VERSION`
  - Ví dụ: `civitai:1259001@1419583`

- **weight**: Độ mạnh của LoRA (0.0 - 1.0)
  - `1.0` = Áp dụng hoàn toàn phong cách LoRA
  - `0.5` = Kết hợp 50% phong cách LoRA với base model
  - `0.8` = Cân bằng giữa tự nhiên và phong cách

## Sử dụng trong Code

### 1. Tự động sử dụng LoRA từ .env

Khi không truyền tham số `lora`, hệ thống sẽ **tự động** sử dụng config từ `.env`:

```python
import config
from runware_image_generator import RunwareImageGenerator

generator = RunwareImageGenerator()

# Không cần truyền lora parameter
# Tự động sử dụng config.RUNWARE_LORA_CONFIG từ .env
result = await generator.generate_images_from_json(
    json_path="prompts.json",
    story_name="Cổ tích Việt Nam"
)
```

### 2. Sử dụng LoRA từ .env một cách tường minh

```python
import config
from runware_image_generator import RunwareImageGenerator

generator = RunwareImageGenerator()

await generator.generate_image(
    prompt="A happy child reading a book",
    lora=config.RUNWARE_LORA_CONFIG  # Lấy từ .env
)
```

### 3. Override với LoRA tùy chỉnh

```python
# Override với LoRA khác
custom_lora = [
    {"model": "civitai:xxx@yyy", "weight": 0.8}
]

await generator.generate_image(
    prompt="A happy child reading a book",
    lora=custom_lora  # Override config từ .env
)
```

### 4. Kết hợp nhiều LoRA

```python
# Sử dụng nhiều LoRA cùng lúc
multiple_lora = [
    {"model": "civitai:1259001@1419583", "weight": 0.7},  # Style LoRA
    {"model": "civitai:xxx@yyy", "weight": 0.5}           # Quality LoRA
]

await generator.generate_image(
    prompt="A happy child reading a book",
    lora=multiple_lora
)
```

### 5. Không sử dụng LoRA

```python
# Tắt LoRA hoàn toàn
await generator.generate_image(
    prompt="A happy child reading a book",
    lora=[]  # Không dùng LoRA
)
```

## Tìm LoRA Models

### Nguồn LoRA models

1. **Civitai**: https://civitai.com/
   - Tìm kiếm: "children illustration", "book illustration", "anime style"
   - Lấy ID và Version từ URL

2. **Runware Models**: Xem documentation tại https://docs.runware.ai/

### Ví dụ URL Civitai

```
https://civitai.com/models/1259001?modelVersionId=1419583
                         ^^^^^^^                   ^^^^^^^
                         ID                        Version
```

→ LoRA config: `{"model": "civitai:1259001@1419583", "weight": 1.0}`

## Các LoRA phổ biến cho truyện thiếu nhi

```bash
# Trong .env, bạn có thể thử các LoRA này:

# Children's book illustration style
RUNWARE_LORA_CONFIG=[{"model": "civitai:1259001@1419583", "weight": 1.0}]

# Anime/Manga style
RUNWARE_LORA_CONFIG=[{"model": "civitai:xxx@yyy", "weight": 0.8}]

# Watercolor illustration
RUNWARE_LORA_CONFIG=[{"model": "civitai:xxx@yyy", "weight": 0.7}]

# Kết hợp nhiều style
RUNWARE_LORA_CONFIG=[{"model": "civitai:1259001@1419583", "weight": 0.7}, {"model": "civitai:xxx@yyy", "weight": 0.5}]
```

## Testing

Chạy script test để kiểm tra cấu hình:

```bash
python test_lora_config.py
```

Script này sẽ test:
1. ✓ Generate image với LoRA từ .env (auto)
2. ✓ Override LoRA với config khác
3. ✓ Generate image KHÔNG có LoRA

## Troubleshooting

### ⚠️ Invalid RUNWARE_LORA_CONFIG format

Nếu thấy cảnh báo này, kiểm tra format JSON trong `.env`:
- Đảm bảo JSON hợp lệ
- Không có khoảng trắng thừa
- Sử dụng dấu ngoặc kép `"` cho keys và values

**Đúng:**
```bash
RUNWARE_LORA_CONFIG=[{"model": "civitai:1259001@1419583", "weight": 1.0}]
```

**Sai:**
```bash
RUNWARE_LORA_CONFIG=[{model: civitai:1259001@1419583, weight: 1.0}]  # Thiếu dấu ngoặc kép
```

### LoRA không có hiệu ứng

- Kiểm tra `weight` có phù hợp không (thử tăng lên 1.0)
- Đảm bảo LoRA model ID đúng
- Kiểm tra prompt có phù hợp với style của LoRA

## Ví dụ hoàn chỉnh

```python
import asyncio
import config
from runware_image_generator import RunwareImageGenerator

async def main():
    generator = RunwareImageGenerator()

    async with generator:
        # Tự động sử dụng LoRA từ .env
        images = await generator.generate_images_from_json(
            json_path="chapter_1_prompts.json",
            story_name="Cổ Tích Việt Nam",
            chapter_number=1,
            model=config.RUNWARE_DEFAULT_MODEL,
            width=config.RUNWARE_DEFAULT_WIDTH,
            height=config.RUNWARE_DEFAULT_HEIGHT
            # lora tự động lấy từ config.RUNWARE_LORA_CONFIG
        )

        print(f"Generated {images.get('generated_images')} images")

asyncio.run(main())
```

## Kết luận

LoRA configuration giúp bạn:
- ✨ Tùy chỉnh phong cách hình ảnh dễ dàng
- 🎨 Đảm bảo tính nhất quán trong toàn bộ truyện
- 🚀 Không cần train model mới
- ⚙️ Cấu hình linh hoạt qua .env hoặc code
