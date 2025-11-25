#!/usr/bin/env python3
"""
Quick test để verify LoRA conversion hoạt động đúng
"""
import config
from runware_image_generator import convert_lora_to_objects

print("=" * 60)
print("QUICK TEST: LoRA Configuration")
print("=" * 60)

# Test 1: Load config from .env
print("\n1. Testing LoRA config from .env:")
print(f"   Config value: {config.RUNWARE_LORA_CONFIG}")
print(f"   Type: {type(config.RUNWARE_LORA_CONFIG)}")

# Test 2: Convert to objects
print("\n2. Converting to ILora objects:")
lora_objects = convert_lora_to_objects(config.RUNWARE_LORA_CONFIG)
print(f"   Result: {lora_objects}")
if lora_objects:
    print(f"   Type: {type(lora_objects)}")
    print(f"   First object type: {type(lora_objects[0])}")
    print(f"   First object model: {lora_objects[0].model}")
    print(f"   First object weight: {lora_objects[0].weight}")
else:
    print("   ❌ Conversion failed!")

# Test 3: Manual conversion test
print("\n3. Manual conversion test:")
test_lora = [
    {"model": "civitai:1107395@1244162", "weight": 1.0},
    {"model": "civitai:xxx@yyy", "weight": 0.8}
]
print(f"   Input: {test_lora}")
test_objects = convert_lora_to_objects(test_lora)
if test_objects:
    print(f"   ✓ Converted {len(test_objects)} LoRA objects")
    for idx, obj in enumerate(test_objects):
        print(f"     [{idx}] model={obj.model}, weight={obj.weight}")
else:
    print("   ❌ Conversion failed!")

print("\n" + "=" * 60)
print("TEST COMPLETED")
print("=" * 60)
