"""
Demo: Tự động tạo characters.json template
Chạy script này để xem cách hệ thống xử lý khi không có characters.json
"""

import os
import json
import asyncio
from runware_image_generator import (
    RunwareImageGenerator,
    create_characters_json_template
)

# Test prompts không có characters.json
TEST_PROMPTS = {
    "prompts": [
        {
            "id": 1,
            "content": "A young warrior standing at city gate"
        },
        {
            "id": 2,
            "content": "An elegant female cultivator meditating"
        }
    ]
}


async def demo_without_characters_json():
    """Demo 1: Chạy không có characters.json (normal mode)"""
    print("\n" + "="*60)
    print("DEMO 1: Chạy KHÔNG có characters.json")
    print("="*60 + "\n")

    # Tạo test directory
    os.makedirs("demo_test", exist_ok=True)

    # Tạo prompts.json
    prompts_path = "demo_test/prompts.json"
    with open(prompts_path, "w", encoding="utf-8") as f:
        json.dump(TEST_PROMPTS, f, ensure_ascii=False, indent=2)

    print("📁 Created: demo_test/prompts.json")
    print("❌ NO characters.json exists\n")

    print("Simulating image generation...\n")
    print("Expected behavior:")
    print("  ⚠️ Warning: No characters.json found")
    print("  💡 Instructions to create one")
    print("  ℹ️ Generating images in normal mode (no character consistency)\n")

    # Simulate (không thực sự gọi API)
    generator = RunwareImageGenerator()

    # Chỉ load và check characters.json, không generate
    json_dir = os.path.dirname(prompts_path)
    auto_char_path = os.path.join(json_dir, 'characters.json')

    if not os.path.exists(auto_char_path):
        print(f"⚠️ No characters.json found at: {auto_char_path}")
        print("💡 To enable character consistency:")
        print("   1. Create characters.json with your character info")
        print("   2. Add character references (e.g., characters/han_lap_ref.jpg)")
        print("   3. See characters.json.example for template")
        print("   OR run with auto_create_characters_template=True\n")
        print("ℹ️ Generating images WITHOUT character consistency (normal mode)\n")


async def demo_auto_create_template():
    """Demo 2: Tự động tạo template"""
    print("\n" + "="*60)
    print("DEMO 2: Tự động tạo characters.json template")
    print("="*60 + "\n")

    template_path = "demo_test/characters.json"

    print(f"Creating template at: {template_path}\n")

    # Tạo template
    success = create_characters_json_template(template_path, "Demo Story")

    if success:
        print("\n✅ Template created successfully!\n")

        # Show nội dung
        with open(template_path, "r", encoding="utf-8") as f:
            content = json.load(f)

        print("📄 Template content:")
        print(json.dumps(content, indent=2, ensure_ascii=False))

        print("\n📝 Next steps:")
        print("   1. Edit demo_test/characters.json")
        print("   2. Replace 'character_1' with your character ID (e.g., 'han_lap')")
        print("   3. Update character info (name, aliases, description)")
        print("   4. Generate first images")
        print("   5. Pick best image as reference")
        print("   6. Save to characters/character_id_ref.jpg")
        print("   7. Update reference_image path in JSON")


async def demo_with_auto_create_flag():
    """Demo 3: Sử dụng auto_create_characters_template=True"""
    print("\n" + "="*60)
    print("DEMO 3: Sử dụng auto_create_characters_template=True")
    print("="*60 + "\n")

    # Xóa characters.json nếu tồn tại
    char_path = "demo_test/characters.json"
    if os.path.exists(char_path):
        os.remove(char_path)
        print(f"🗑️ Removed existing: {char_path}\n")

    print("Code example:")
    print("-" * 40)
    print("""
result = await generator.generate_images_from_json(
    json_path="demo_test/prompts.json",
    auto_create_characters_template=True  # <-- Tự động tạo template
)
    """)
    print("-" * 40)

    print("\nExpected behavior:")
    print("  ✓ Auto-detect: No characters.json found")
    print("  ✓ Creating characters.json template")
    print("  📝 Please edit characters.json to add your character info")
    print("  ℹ️ For now, generating images without character consistency\n")

    # Simulate
    json_dir = "demo_test"
    auto_char_path = os.path.join(json_dir, 'characters.json')

    if not os.path.exists(auto_char_path):
        print(f"Creating characters.json template at: {auto_char_path}")
        create_characters_json_template(auto_char_path, "Demo Story")
        print("📝 Template created! Please edit it to add your character info\n")


def cleanup():
    """Cleanup demo files"""
    import shutil
    if os.path.exists("demo_test"):
        shutil.rmtree("demo_test")
        print("🗑️ Cleaned up: demo_test/")


async def main():
    """Run all demos"""
    print("="*60)
    print("AUTO-CREATE CHARACTERS.JSON TEMPLATE - DEMOS")
    print("="*60)

    try:
        await demo_without_characters_json()
        await demo_auto_create_template()
        await demo_with_auto_create_flag()

        print("\n" + "="*60)
        print("✓ ALL DEMOS COMPLETED")
        print("="*60)

        print("\n📚 Summary:")
        print("   1. Không có characters.json → Chạy normal mode")
        print("   2. Dùng create_characters_json_template() → Tạo template thủ công")
        print("   3. Dùng auto_create_characters_template=True → Tự động tạo")

        print("\n💡 Recommendation:")
        print("   - Lần đầu: Dùng auto_create_characters_template=True")
        print("   - Edit template với character info")
        print("   - Generate lần đầu → chọn reference image")
        print("   - Các lần sau: Tự động dùng reference\n")

    finally:
        print("\nCleanup? (y/n): ", end="")
        # Auto cleanup for demo
        cleanup()


if __name__ == "__main__":
    asyncio.run(main())
