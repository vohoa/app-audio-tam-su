"""
Test Database Variety - Validate realistic hardware combinations

Generate nhiều fingerprints và kiểm tra:
1. Variety (không trùng lặp)
2. Realistic combinations (CPU tier matches RAM/GPU)
3. WebGL strings accuracy
4. OS-specific fonts
"""

import json
from collections import Counter
from fingerprint_generator import FingerprintGenerator


def test_variety_and_realism(num_profiles=20):
    """Generate multiple fingerprints and validate variety & realism"""
    
    print("\n" + "="*80)
    print(f"TESTING DATABASE VARIETY - Generating {num_profiles} fingerprints")
    print("="*80)
    
    fingerprints = []
    
    # Generate fingerprints
    for i in range(1, num_profiles + 1):
        generator = FingerprintGenerator(seed=f"test_profile_{i}")
        fp = generator.generate()
        fingerprints.append(fp)
    
    # Extract components
    cpus = [fp['hardware']['cpu']['model'] for fp in fingerprints]
    gpus = [fp['hardware']['gpu']['model'] for fp in fingerprints]
    rams = [f"{fp['hardware']['ram']['total_gb']}GB {fp['hardware']['ram']['type']}" for fp in fingerprints]
    resolutions = [f"{fp['screen']['width']}x{fp['screen']['height']}" for fp in fingerprints]
    os_list = [fp['os'] for fp in fingerprints]
    
    # Count unique components
    print(f"\n📊 VARIETY ANALYSIS:")
    print(f"   Unique CPUs: {len(set(cpus))} / {len(cpus)}")
    print(f"   Unique GPUs: {len(set(gpus))} / {len(gpus)}")
    print(f"   Unique RAM configs: {len(set(rams))} / {len(rams)}")
    print(f"   Unique resolutions: {len(set(resolutions))} / {len(resolutions)}")
    print(f"   Unique OS: {len(set(os_list))} / {len(os_list)}")
    
    # Show most common components
    print(f"\n🔝 MOST COMMON COMPONENTS (Top 5):")
    print(f"\n   CPUs:")
    for cpu, count in Counter(cpus).most_common(5):
        print(f"      {cpu}: {count} times")
    
    print(f"\n   GPUs:")
    for gpu, count in Counter(gpus).most_common(5):
        print(f"      {gpu}: {count} times")
    
    print(f"\n   RAM:")
    for ram, count in Counter(rams).most_common(5):
        print(f"      {ram}: {count} times")
    
    # Validate realistic combinations
    print(f"\n✅ REALISTIC COMBINATION VALIDATION:")
    unrealistic = 0
    
    for i, fp in enumerate(fingerprints, 1):
        cpu_cores = fp['hardware']['cpu']['cores']
        ram_gb = fp['hardware']['ram']['total_gb']
        gpu_tier = fp['hardware']['gpu']['performance_tier']
        
        # Check for unrealistic combinations
        issues = []
        
        # Low-end CPU (4 cores) shouldn't have high-end GPU or massive RAM
        if cpu_cores <= 4 and (gpu_tier in ['high', 'enthusiast'] or ram_gb > 16):
            issues.append(f"4-core CPU with {gpu_tier} GPU and {ram_gb}GB RAM")
        
        # High-end CPU (16+ cores) shouldn't have entry GPU
        if cpu_cores >= 16 and gpu_tier == 'entry':
            issues.append(f"16+ core CPU with entry-level GPU")
        
        # Entry GPU shouldn't have 64GB+ RAM
        if gpu_tier == 'entry' and ram_gb >= 64:
            issues.append(f"Entry GPU with {ram_gb}GB RAM")
        
        if issues:
            unrealistic += 1
            print(f"   ⚠️ Profile {i}: {', '.join(issues)}")
            print(f"      {fp['hardware']['cpu']['model']} + {fp['hardware']['gpu']['model']} + {ram_gb}GB")
    
    if unrealistic == 0:
        print(f"   ✅ All {num_profiles} combinations are realistic!")
    else:
        print(f"   ⚠️ Found {unrealistic}/{num_profiles} potentially unrealistic combinations")
    
    # Validate WebGL strings
    print(f"\n🎮 WEBGL VALIDATION:")
    invalid_webgl = 0
    for i, fp in enumerate(fingerprints, 1):
        renderer = fp['webgl']['renderer']
        gpu_model = fp['hardware']['gpu']['model']
        
        # Check if GPU model appears in renderer string
        if gpu_model not in renderer:
            invalid_webgl += 1
            print(f"   ⚠️ Profile {i}: GPU model mismatch")
            print(f"      GPU: {gpu_model}")
            print(f"      WebGL: {renderer}")
    
    if invalid_webgl == 0:
        print(f"   ✅ All {num_profiles} WebGL renderer strings match GPU models!")
    else:
        print(f"   ⚠️ Found {invalid_webgl}/{num_profiles} WebGL mismatches")
    
    # Validate OS-specific fonts
    print(f"\n🔤 FONT VALIDATION:")
    font_issues = 0
    for i, fp in enumerate(fingerprints, 1):
        platform = fp['platform']
        fonts = fp['fonts']
        
        # Check for OS-specific font anomalies
        issues = []
        
        if "Win32" in platform:
            # Windows should have Segoe UI, Calibri, etc.
            if "Segoe UI" not in fonts and "Calibri" not in fonts:
                issues.append("Missing common Windows fonts")
        elif "MacIntel" in platform:
            # macOS should have San Francisco, Helvetica Neue
            if "Helvetica Neue" not in fonts and ".SF NS" not in fonts:
                issues.append("Missing common macOS fonts")
        elif "Linux" in platform:
            # Linux should have DejaVu, Ubuntu, Noto
            if "DejaVu Sans" not in fonts and "Ubuntu" not in fonts:
                issues.append("Missing common Linux fonts")
        
        if issues:
            font_issues += 1
            print(f"   ⚠️ Profile {i} ({platform}): {', '.join(issues)}")
    
    if font_issues == 0:
        print(f"   ✅ All {num_profiles} font lists match their OS!")
    else:
        print(f"   ⚠️ Found {font_issues}/{num_profiles} font mismatches")
    
    # Show sample fingerprints
    print(f"\n📋 SAMPLE FINGERPRINTS (First 3):")
    for i in range(min(3, num_profiles)):
        fp = fingerprints[i]
        print(f"\n   Profile {i+1}:")
        print(f"      CPU: {fp['hardware']['cpu']['model']} ({fp['hardware']['cpu']['cores']} cores)")
        print(f"      GPU: {fp['hardware']['gpu']['model']} ({fp['hardware']['gpu']['vram']})")
        print(f"      RAM: {fp['hardware']['ram']['total_gb']}GB {fp['hardware']['ram']['type']}")
        print(f"      OS: {fp['os']} ({fp['platform']})")
        print(f"      Screen: {fp['screen']['width']}x{fp['screen']['height']}")
        print(f"      WebGL: {fp['webgl']['renderer'][:80]}...")
        print(f"      Timezone: {fp['timezone']}")
        print(f"      Language: {fp['language']}")
    
    # Calculate total possible combinations
    print(f"\n🔢 THEORETICAL VARIETY:")
    print(f"   Database specs: 31 CPUs × 38 GPUs × 9 RAM × 12 Monitors = 123,552 combinations")
    print(f"   Tested: {num_profiles} profiles")
    print(f"   Uniqueness rate: {len(set(cpus))/len(cpus)*100:.1f}% CPUs, {len(set(gpus))/len(gpus)*100:.1f}% GPUs")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    test_variety_and_realism(num_profiles=50)
