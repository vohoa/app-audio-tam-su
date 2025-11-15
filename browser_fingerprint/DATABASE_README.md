# Hardware & Software Database System

🗄️ **Comprehensive fingerprint database with 123,552+ unique hardware combinations**

## Overview

Version 2.0 of the fingerprint system uses extensive hardware/software databases instead of hardcoded lists, providing:

- **31 CPUs** (Intel Core i3/i5/i7/i9, AMD Ryzen 3/5/7/9)
- **38 GPUs** (NVIDIA GTX/RTX, AMD RX, Intel UHD/Iris/Arc)
- **9 RAM configs** (4GB to 128GB, DDR3/DDR4/DDR5)
- **12 Monitor resolutions** (HD to 4K)
- **9 Audio devices** (Realtek, Intel, AMD, Creative, ASUS)
- **9 Network adapters** (Ethernet: Realtek, Intel; WiFi: Intel, Qualcomm, MediaTek)
- **17 Operating Systems** (Windows 10/11, macOS 10.15-14.0, Linux distros)
- **220+ Fonts** (OS-specific: Windows, macOS, Linux)
- **15 Language packs** (Timezone-matched language strings)

**Total combinations**: 31 × 38 × 9 × 12 = **123,552** hardware mixes (not including OS, fonts, languages)

## Database Structure

```
browser_fingerprint/
├── hardware_db/
│   ├── cpus.json           (31 CPUs with specs, market share)
│   ├── gpus.json           (38 GPUs with WebGL renderer strings)
│   ├── ram.json            (9 RAM configs with performance tiers)
│   ├── monitors.json       (12 resolutions with market share)
│   ├── audio_devices.json  (Integrated + dedicated audio)
│   └── network_adapters.json (Ethernet + WiFi adapters)
├── software_db/
│   ├── operating_systems.json (Windows/macOS/Linux versions)
│   ├── fonts.json             (OS-specific font lists)
│   └── languages.json         (Timezone/region language strings)
├── hardware_software_db.py    (DatabaseManager class)
├── fingerprint_generator.py   (Updated FingerprintGenerator v2.0)
└── test_database_variety.py   (Test script)
```

## Key Features

### 1. Market Share Weighted Selection

Each component has realistic market share percentages for probability weighting:

```json
{
  "model": "Intel Core i5-12400",
  "market_share": 12.5,  // 12.5% probability
  "cores": 6,
  "threads": 12
}
```

Popular hardware (GTX 1650, i5-12400) is selected more often than rare hardware (RTX 4090, i9-13900K).

### 2. Performance Tier Matching

Prevents unrealistic combinations:

- **Entry CPU** (4 cores) → Entry/Mid GPU + 4-8GB RAM
- **Mid CPU** (6-8 cores) → Mid/High GPU + 8-16GB RAM  
- **High CPU** (12+ cores) → High/Enthusiast GPU + 32-128GB RAM

❌ **Prevented**: Intel i3 + RTX 4090 + 128GB RAM  
✅ **Realistic**: Intel i5-12400 + GTX 1660 Ti + 16GB RAM

### 3. Exact WebGL Renderer Strings

GPU database includes exact ANGLE renderer strings that Chrome reports:

```json
{
  "model": "NVIDIA GeForce RTX 3060",
  "webgl_vendor": "Google Inc. (NVIDIA)",
  "webgl_renderer": "ANGLE (NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"
}
```

### 4. OS-Specific Fonts

Font lists match each operating system:

- **Windows**: Segoe UI, Calibri, Consolas, Arial, Times New Roman
- **macOS**: San Francisco, Helvetica Neue, Menlo, Monaco
- **Linux**: DejaVu Sans, Liberation Sans, Ubuntu, Noto Sans

### 5. Geographic Matching

Languages, timezones, and currencies are matched by region:

```json
{
  "timezone": "Asia/Ho_Chi_Minh",
  "primary": ["vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"],
  "country": "VN",
  "currency": "VND"
}
```

## Usage

### Basic Usage

```python
from browser_fingerprint import FingerprintGenerator

# Generate fingerprint (automatic database loading)
generator = FingerprintGenerator(seed="profile_1")
fingerprint = generator.generate()

print(f"CPU: {fingerprint['hardware']['cpu']['model']}")
print(f"GPU: {fingerprint['hardware']['gpu']['model']}")
print(f"RAM: {fingerprint['hardware']['ram']['total_gb']}GB")
```

### With Preferences

```python
# Control hardware selection
fingerprint = generator.generate(
    timezone="Asia/Ho_Chi_Minh",
    cpu_preference="intel",    # "intel", "amd", or "mixed"
    gpu_preference="nvidia",   # "nvidia", "amd", "intel", or "mixed"
    os_preference="windows"    # "windows", "macos", "linux", or "mixed"
)
```

### Direct Database Access

```python
from browser_fingerprint.hardware_software_db import get_database

db = get_database()

# Get random CPU
cpu = db.get_random_cpu(preference="intel")

# Get GPU by performance tier
gpu = db.get_random_gpu(preference="nvidia", performance_tier="high")

# Get RAM matching CPU tier
ram = db.get_random_ram(min_gb=16, max_gb=32)

# Get monitor resolution
monitor = db.get_random_monitor(min_width=1920)

# Get OS-specific fonts
fonts = db.get_fonts_for_os("Win32")

# Get language for timezone
language = db.get_language_for_timezone("Asia/Ho_Chi_Minh")

# Generate realistic hardware mix
hardware = db.generate_realistic_hardware_mix(
    cpu_preference="mixed",
    gpu_preference="mixed",
    os_preference="windows"
)
```

## Test Results

From `test_database_variety.py` with 50 profiles:

```
📊 VARIETY ANALYSIS:
   Unique CPUs: 20 / 50 (40% uniqueness)
   Unique GPUs: 24 / 50 (48% uniqueness)
   Unique RAM configs: 9 / 50
   Unique resolutions: 8 / 50

✅ REALISTIC COMBINATION VALIDATION:
   ✅ All 50 combinations are realistic!

🎮 WEBGL VALIDATION:
   ✅ 48/50 WebGL renderer strings match GPU models!

🔤 FONT VALIDATION:
   ✅ All 50 font lists match their OS!
```

## Database Details

### CPUs (31 models)

**Intel (16 models)**:
- i3: 10100, 10105, 12100
- i5: 10400, 11400, 12400, 12600K, 13400
- i7: 10700, 11700, 12700, 13700
- i9: 10900, 11900, 12900, 13900

**AMD (15 models)**:
- Ryzen 3: 3100, 3300X
- Ryzen 5: 3600, 5600, 5600X, 7600
- Ryzen 7: 5700X, 5800X, 7700, 7700X
- Ryzen 9: 3900X, 5900X, 7900X, 7950X, 9900X

### GPUs (38 models)

**NVIDIA (15 models)**: GTX 1050, 1050 Ti, 1650, 1660 Ti, RTX 2060, 2070, 3060, 3060 Ti, 3070, 3080, 4060, 4060 Ti, 4070, 4080, 4090

**AMD (12 models)**: RX 560, 580, 5500 XT, 5600 XT, 5700 XT, 6600, 6600 XT, 6700 XT, 6800, 7600, 7700 XT, 7800 XT

**Intel (8 models)**: UHD 620, 630, 730, 770, Iris Xe, Arc A380, A580, A750

### RAM (9 configs)

4GB, 6GB, 8GB, 12GB, 16GB, 24GB, 32GB, 64GB, 128GB (DDR3/DDR4/DDR5)

### Monitors (12 resolutions)

1280x720 (HD), 1366x768 (HD), 1600x900 (HD+), 1536x864 (HD+), 1920x1080 (Full HD), 1920x1200 (WUXGA), 2560x1440 (QHD), 2560x1600 (WQXGA), 3440x1440 (UW-QHD), 3840x2160 (4K UHD), 2560x1080 (UW-FHD), 1680x1050 (WSXGA+)

## Advantages vs. v1.0

| Feature | v1.0 (Hardcoded) | v2.0 (Database) |
|---------|------------------|-----------------|
| CPU variety | 6 generic configs | 31 real CPU models |
| GPU variety | 8 models | 38 models with exact WebGL strings |
| RAM variety | 6 configs | 9 configs with performance tiers |
| Hardware combinations | 6 × 8 × 6 = **288** | 31 × 38 × 9 × 12 = **123,552** |
| Realistic matching | ❌ No validation | ✅ Performance tier matching |
| Market share | ❌ Uniform distribution | ✅ Weighted by real market share |
| WebGL accuracy | ⚠️ Generic strings | ✅ Exact ANGLE renderer strings |
| OS-specific fonts | ⚠️ Mixed list | ✅ OS-specific (220+ fonts) |
| Easy updates | ❌ Requires code changes | ✅ Just edit JSON files |

## Adding New Hardware

Simply edit the JSON files:

```json
// hardware_db/cpus.json
{
  "intel_cpus": [
    {
      "model": "Intel Core i5-14600K",  // New CPU
      "cores": 14,
      "threads": 20,
      "base_clock": "3.5 GHz",
      "max_clock": "5.3 GHz",
      "generation": "14th Gen",
      "tdp": "125W",
      "market_share": 5.0,
      "performance_tier": "high"
    }
  ]
}
```

No code changes needed! The DatabaseManager automatically loads updated data.

## Performance

- **Database loading**: ~50ms (cached after first load)
- **Fingerprint generation**: ~5ms per profile
- **Memory usage**: ~2MB for all databases

## Best Practices

1. **Use `seed` for reproducibility**: Same profile name = same fingerprint
2. **Match timezone with proxy location**: Use geographic preferences
3. **Test combinations**: Run `test_database_variety.py` after updates
4. **Update market share**: Adjust probabilities as hardware popularity changes
5. **Add new releases**: Update JSON files when new CPUs/GPUs launch

## Troubleshooting

**Issue**: "ImportError: attempted relative import"  
**Solution**: Import handles both module and direct execution automatically

**Issue**: "Database file not found"  
**Solution**: Ensure `hardware_db/` and `software_db/` directories exist

**Issue**: "Unrealistic combinations"  
**Solution**: Check `performance_tier` and `min_cpu_tier` in JSON files

## Future Enhancements

- [ ] Add more exotic hardware (Threadripper, Xeon, Quadro)
- [ ] Mobile device fingerprints (Android, iOS)
- [ ] More language packs (Africa, South America regions)
- [ ] Audio codec fingerprinting
- [ ] Canvas/WebGL fingerprint noise patterns
- [ ] Browser extension detection evasion

## References

- [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
- [ANGLE Renderer Strings](https://chromium.googlesource.com/angle/angle)
- [Navigator Compatibility Data](https://developer.mozilla.org/en-US/docs/Web/API/Navigator)
- [Steam Hardware Survey](https://store.steampowered.com/hwsurvey/) (for market share data)
