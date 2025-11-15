# Character Consistency Workflow

## 📊 Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    User calls generate_images_from_json()       │
│                         with prompts.json                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                   ┌─────────────────────┐
                   │ Look for            │
                   │ characters.json     │
                   │ in same directory   │
                   └──────┬──────────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
     ┌────────────────┐      ┌────────────────┐
     │ File EXISTS    │      │ File NOT FOUND │
     └────┬───────────┘      └────┬───────────┘
          │                       │
          │                       ▼
          │              ┌─────────────────────────┐
          │              │ auto_create_template?   │
          │              └──────┬──────────────────┘
          │                     │
          │          ┌──────────┴──────────┐
          │          ▼                     ▼
          │   ┌─────────────┐      ┌─────────────┐
          │   │ YES         │      │ NO          │
          │   └──────┬──────┘      └──────┬──────┘
          │          │                    │
          │          ▼                    ▼
          │   ┌─────────────┐      ┌─────────────────┐
          │   │ Create      │      │ Show warning    │
          │   │ template    │      │ & instructions  │
          │   └──────┬──────┘      └──────┬──────────┘
          │          │                    │
          │          └────────┬───────────┘
          │                   │
          │                   ▼
          │         ┌──────────────────┐
          │         │ Run NORMAL MODE  │
          │         │ (no char refs)   │
          │         └──────────────────┘
          │
          ▼
┌──────────────────────┐
│ Load characters.json │
│ Initialize           │
│ CharacterManager     │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ For each prompt:     │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ 1. Extract prompt text           │
│ 2. Check if images exist (cache) │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ If NOT cached:                   │
│ ├─ Extract characters metadata   │
│ ├─ OR auto-detect from text      │
│ └─ Get reference images          │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ generate_image() with:           │
│ ├─ prompt                        │
│ ├─ character_references (if any) │
│ └─ instant_id_strength           │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ IImageInference with InstantID:  │
│ ├─ positivePrompt                │
│ ├─ model, width, height          │
│ └─ instantID (face reference)    │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ Runware API generates image      │
│ with consistent character face   │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ Save images to output directory  │
└──────────────────────────────────┘
```

## 🔄 Character Detection Flow

```
┌─────────────────────────────────┐
│ Prompt data from JSON           │
└────────┬────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│ Has "characters" metadata?         │
└────┬───────────────────────────────┘
     │
     ├─ YES ──▶ Use metadata
     │           ["han_lap", "dong_cung_uyen"]
     │
     └─ NO ───▶ Auto-detect from text
                 ├─ Check full_name: "Hàn Lập"
                 ├─ Check aliases: "Hàn", "Lập"
                 └─ Check normalized: "han lap"
```

## 📁 Reference Image Resolution

```
Character ID: "han_lap"
     │
     ▼
┌─────────────────────────────────┐
│ Get from characters.json:       │
│ "reference_image": "..."        │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ Is absolute path?               │
│ (starts with / or C:\)          │
└────┬────────────────────────────┘
     │
     ├─ YES ──▶ Use as-is
     │           /full/path/to/image.jpg
     │
     └─ NO ───▶ Relative path
                 │
                 ▼
          ┌──────────────────────────┐
          │ Join with base path:     │
          │ characters_json_dir +    │
          │ reference_image          │
          └──────┬───────────────────┘
                 │
                 ▼
          ┌──────────────────────────┐
          │ Check if file exists     │
          └──────┬───────────────────┘
                 │
     ┌───────────┴───────────┐
     ▼                       ▼
   EXISTS               NOT FOUND
     │                       │
     ▼                       ▼
   RETURN              RETURN None
   path                (skip InstantID)
```

## 🎯 InstantID Integration

```
character_references = [
    "characters/han_lap_ref.jpg"
]
instant_id_strength = 0.8

     │
     ▼
┌──────────────────────────────────┐
│ Create IInstantID instance       │
│ ├─ faceImage: reference[0]       │
│ └─ strength: 0.8                 │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ Add to IImageInference params    │
│ request_params["instantID"] = .. │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ Runware processes:               │
│ ├─ Extract face from reference   │
│ ├─ Apply to generated image      │
│ └─ Maintain face similarity      │
└──────────────────────────────────┘
```

## 🌟 Complete Workflow Example

### Scenario: Generate images for Chapter 1 with 2 characters

```
Input Files:
├── prompts.json          (3 prompts)
├── characters.json       (2 characters defined)
└── characters/
    ├── han_lap_ref.jpg   (reference exists)
    └── dong_cung_uyen_ref.jpg (reference exists)

Step 1: Load prompts.json
   ├─ Prompt 1: "Hàn Lập đứng trước cổng"
   ├─ Prompt 2: "Đông Cung Uyển thiền định"
   └─ Prompt 3: "Hàn Lập và Đông Cung Uyển"

Step 2: Load characters.json
   ├─ han_lap (ref: characters/han_lap_ref.jpg) ✓
   └─ dong_cung_uyen (ref: characters/dong_cung_uyen_ref.jpg) ✓

Step 3: Process Prompt 1
   ├─ Detect: ["han_lap"]
   ├─ Reference: characters/han_lap_ref.jpg
   ├─ Generate with InstantID (strength: 0.8)
   └─ Save: prompt_1_0.png, prompt_1_1.png

Step 4: Process Prompt 2
   ├─ Detect: ["dong_cung_uyen"]
   ├─ Reference: characters/dong_cung_uyen_ref.jpg
   ├─ Generate with InstantID
   └─ Save: prompt_2_0.png, prompt_2_1.png

Step 5: Process Prompt 3
   ├─ Detect: ["han_lap", "dong_cung_uyen"]
   ├─ Reference: characters/han_lap_ref.jpg (first one)
   ├─ Generate with InstantID
   └─ Save: prompt_3_0.png, prompt_3_1.png

Result:
   ✓ Hàn Lập has same face in prompt 1 and 3
   ✓ Đông Cung Uyển has same face in prompt 2 (and similar in 3)
```

## 🔧 Configuration Options

### instant_id_strength

```
0.0 ─────────────────────────────── 1.0
│                                    │
No effect                    Maximum similarity
                │
        ┌───────┼───────┐
        │       │       │
      0.6     0.8     0.9
        │       │       │
    Flexible Balanced Strict
```

### Behavior Matrix

| Scenario | characters.json | Reference Images | Behavior |
|----------|----------------|------------------|----------|
| 1 | ❌ Not found | - | Normal mode |
| 2 | ✅ Found | ❌ Not found | Normal mode (warn) |
| 3 | ✅ Found | ✅ Exists | Character consistency ON |
| 4 | ❌ + auto_create | - | Create template → Normal |

## 🐛 Error Handling

```
Try:
    ├─ Load characters.json
    │  └─ Error → Log warning, continue normal mode
    │
    ├─ Detect characters
    │  └─ No match → Continue without refs
    │
    ├─ Load reference image
    │  └─ File not found → Log warning, skip InstantID
    │
    └─ Generate with InstantID
       └─ Error → Retry without InstantID
```

## 💡 Tips

1. **First time setup**: Use `auto_create_characters_template=True`
2. **Metadata vs Auto-detect**: Metadata is 100% accurate, auto-detect may have false positives
3. **Multiple characters**: InstantID uses first character in list
4. **Reference quality**: Use clear, front-facing images for best results
5. **Model compatibility**: Most SD1.5 and SDXL models support InstantID
