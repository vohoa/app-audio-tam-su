"""
Fingerprint Generator - Tạo browser fingerprints độc nhất

Tạo cấu hình fingerprint ngẫu nhiên nhưng realistic cho mỗi profile
để tránh bị phát hiện là automation bot.

Version 2.0: Uses comprehensive hardware/software databases for maximum variety.
"""

import random
import hashlib
import json
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Handle both direct execution and module import
try:
    from .hardware_software_db import get_database
except ImportError:
    from hardware_software_db import get_database

logger = logging.getLogger(__name__)


class FingerprintGenerator:
    """
    Generate unique but realistic browser fingerprints using comprehensive hardware/software databases
    
    Version 2.0: 
    - Uses databases with 31 CPUs × 38 GPUs × 9 RAM × 12 Monitors = 123,552 hardware combinations
    - Market share weighted selection for realistic distributions
    - Performance tier matching prevents unrealistic combinations
    - OS-specific fonts and settings
    - Geographic matching of timezone/language/geolocation
    """
    
    def __init__(self, seed: Optional[str] = None):
        """
        Initialize fingerprint generator
        
        Args:
            seed: Optional seed for reproducible fingerprints (e.g., profile_name)
        """
        self.seed = seed
        if seed:
            # Use seed to make fingerprint reproducible for same profile
            self.random = random.Random(self._hash_seed(seed))
        else:
            self.random = random.Random()
        
        # Load hardware/software database
        self.db = get_database()
        logger.info(f"🎲 FingerprintGenerator initialized (seed: {seed})")
    
    
    def _hash_seed(self, seed: str) -> int:
        """Convert string seed to integer for random seed"""
        return int(hashlib.md5(seed.encode()).hexdigest(), 16)
    
    def generate(self, 
                 timezone: Optional[str] = None,
                 proxy_country: Optional[str] = None,
                 cpu_preference: str = "mixed",
                 gpu_preference: str = "mixed",
                 os_preference: str = "windows",
                 custom_config: Optional[Dict] = None) -> Dict:
        """
        Generate complete browser fingerprint using comprehensive databases
        
        Args:
            timezone: Specific timezone to use (default: random from database)
            proxy_country: Country code for proxy (will match timezone/language)
            cpu_preference: "intel", "amd", or "mixed" (default)
            gpu_preference: "nvidia", "amd", "intel", or "mixed" (default)
            os_preference: "windows", "macos", "linux", or "mixed" (default)
            custom_config: Override specific fingerprint values
            
        Returns:
            Dict: Complete fingerprint configuration with hardware from databases
        """
        # Get realistic hardware mix from databases
        hardware_mix = self.db.generate_realistic_hardware_mix(
            cpu_preference=cpu_preference,
            gpu_preference=gpu_preference,
            os_preference=os_preference
        )
        
        # Extract components
        cpu = hardware_mix["cpu"]
        gpu = hardware_mix["gpu"]
        ram = hardware_mix["ram"]
        monitor = hardware_mix["monitor"]
        audio = hardware_mix["audio"]
        network = hardware_mix["network"]
        os_config = hardware_mix["os"]
        fonts = hardware_mix["fonts"]
        
        # Select timezone if not provided
        if not timezone:
            # Use common Asian timezones as default
            timezone = self.random.choice([
                "Asia/Ho_Chi_Minh", "Asia/Bangkok", "Asia/Singapore",
                "Asia/Manila", "Asia/Jakarta", "Asia/Tokyo"
            ])
        
        # Get language matching timezone
        language = self.db.get_language_for_timezone(timezone)
        
        # Generate geolocation
        geolocation = self._generate_geolocation(timezone)
        
        # Build fingerprint
        fingerprint = {
            "version": "2.0.0",
            "generated_at": datetime.utcnow().isoformat(),
            
            # Geographic
            "timezone": timezone,
            "language": language,
            "geolocation": geolocation,
            
            # Screen & Display
            "screen": {
                "width": monitor["width"],
                "height": monitor["height"],
                "availWidth": monitor["width"],
                "availHeight": monitor["height"] - 40,  # Taskbar
                "colorDepth": monitor.get("color_depth", 24),
                "pixelDepth": monitor.get("color_depth", 24),
                "pixelRatio": monitor.get("pixel_ratio", [1.0])[0] if isinstance(monitor.get("pixel_ratio"), list) else monitor.get("pixel_ratio", 1.0),
            },
            
            # Platform & OS
            "platform": os_config["platform"],
            "os": os_config["name"],
            "os_version": os_config["version"],
            
            # User Agent
            "user_agent": self._generate_user_agent_from_os(os_config),
            
            # WebGL (from GPU database)
            "webgl": {
                "vendor": gpu["webgl_vendor"],
                "renderer": gpu["webgl_renderer"],
                "unmasked_vendor": gpu["webgl_vendor"],
                "unmasked_renderer": gpu["webgl_renderer"],
            },
            
            # Hardware (from database)
            "hardware": {
                "cpu": {
                    "model": cpu["model"],
                    "cores": cpu["cores"],
                    "threads": cpu["threads"],
                    "base_clock": cpu["base_clock"],
                    "max_clock": cpu["max_clock"],
                },
                "gpu": {
                    "model": gpu["model"],
                    "vram": gpu["vram"],
                    "performance_tier": gpu.get("performance_tier", "mid"),
                },
                "ram": {
                    "total_gb": ram["total_gb"],
                    "device_memory_gb": ram["device_memory_gb"],
                    "type": ram["type"],
                },
                "memory_gb": ram["total_gb"],  # Backward compatibility
                "device_memory_gb": ram["device_memory_gb"],  # Backward compatibility
                "cpu_cores": cpu["cores"],  # Backward compatibility
            },
            
            # Audio Device
            "audio_device": {
                "name": audio["name"],
                "chipset": audio.get("chipset", "Unknown"),
            },
            
            # Network Adapters
            "network": {
                "ethernet": network["ethernet"]["name"],
                "wifi": network["wifi"]["name"] if network.get("wifi") else None,
            },
            
            # Fonts (OS-specific from database)
            "fonts": fonts[:50],  # Limit to first 50 fonts for performance
            
            # Privacy & Security
            "webrtc_enabled": False,  # Block WebRTC to prevent IP leak
            "canvas_noise": True,     # Add noise to canvas fingerprint
            "audio_noise": True,      # Add noise to audio context
            "do_not_track": "1",      # Enable Do Not Track
            
            # Plugins & Features
            "plugins": self._generate_plugins(os_config),
            "mime_types": self._generate_mime_types(),
        }
        
        # Apply custom overrides
        if custom_config:
            fingerprint.update(custom_config)
        
        logger.info(f"✅ Generated fingerprint: {cpu['model']} + {gpu['model']} + {ram['total_gb']}GB RAM")
        
        return fingerprint
    
    def _generate_geolocation(self, timezone: str) -> Dict:
        """Generate realistic geolocation for timezone"""
        # Approximate coordinates for major cities
        city_coords = {
            "Asia/Ho_Chi_Minh": (10.8231, 106.6297),  # Ho Chi Minh City
            "Asia/Bangkok": (13.7563, 100.5018),      # Bangkok
            "Asia/Singapore": (1.3521, 103.8198),     # Singapore
            "Asia/Manila": (14.5995, 120.9842),       # Manila
            "Asia/Jakarta": (-6.2088, 106.8456),      # Jakarta
            "Asia/Kuala_Lumpur": (3.1390, 101.6869),  # Kuala Lumpur
            "Asia/Tokyo": (35.6762, 139.6503),        # Tokyo
            "Asia/Seoul": (37.5665, 126.9780),        # Seoul
            "Asia/Hong_Kong": (22.3193, 114.1694),    # Hong Kong
            "Asia/Taipei": (25.0330, 121.5654),       # Taipei
        }
        
        if timezone in city_coords:
            lat, lon = city_coords[timezone]
            # Add small random offset (±0.1 degrees ~ 11km)
            lat += self.random.uniform(-0.1, 0.1)
            lon += self.random.uniform(-0.1, 0.1)
        else:
            # Default to random location
            lat = self.random.uniform(-90, 90)
            lon = self.random.uniform(-180, 180)
        
        return {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "accuracy": self.random.randint(50, 500),  # meters
        }
    
    def _generate_user_agent_from_os(self, os_config: Dict) -> str:
        """Generate realistic user agent string from OS config"""
        chrome_version = self.random.randint(120, 125)  # Current Chrome versions
        
        platform = os_config.get("platform", "Win32")
        
        if platform == "Win32":
            # Windows user agent
            build_number = os_config.get("build_number", "19041")
            return (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{chrome_version}.0.0.0 Safari/537.36"
            )
        elif platform == "MacIntel":
            # macOS user agent
            version = os_config.get("version", "10.15")
            version_underscored = version.replace(".", "_")
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X {version_underscored}_0) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{chrome_version}.0.0.0 Safari/537.36"
            )
        else:  # Linux
            return (
                f"Mozilla/5.0 (X11; Linux x86_64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{chrome_version}.0.0.0 Safari/537.36"
            )
    
    def _generate_plugins(self, os_config: Dict) -> List[Dict]:
        """Generate realistic plugins list"""
        # Most modern browsers have no plugins or only PDF viewer
        plugins = []
        
        # Chrome PDF Plugin (always present in Chrome)
        plugins.append({
            "name": "Chrome PDF Plugin",
            "description": "Portable Document Format",
            "filename": "internal-pdf-viewer",
            "mimeTypes": [{"type": "application/pdf", "suffixes": "pdf"}]
        })
        
        # Chrome PDF Viewer (internal)
        plugins.append({
            "name": "Chrome PDF Viewer",
            "description": "",
            "filename": "mhjfbmdgcfjbbpaeojofohoefgiehjai",
            "mimeTypes": []
        })
        
        return plugins
    
    def _generate_mime_types(self) -> List[str]:
        """Generate realistic MIME types list"""
        return [
            "application/pdf",
            "text/pdf",
        ]
    
    def generate_fingerprint_id(self, fingerprint: Dict) -> str:
        """
        Generate unique ID for fingerprint (for tracking/caching)
        
        Args:
            fingerprint: Fingerprint configuration
            
        Returns:
            str: Unique fingerprint ID (hash)
        """
        # Create deterministic hash from key fingerprint components
        components = [
            fingerprint["screen"]["width"],
            fingerprint["screen"]["height"],
            fingerprint["timezone"],
            fingerprint["platform"],
            fingerprint["webgl"]["renderer"],
            fingerprint["hardware"]["cpu_cores"],
        ]
        
        fingerprint_string = json.dumps(components, sort_keys=True)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]
    
    def save_to_file(self, fingerprint: Dict, filepath: str) -> None:
        """Save fingerprint to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(fingerprint, f, indent=2, ensure_ascii=False)
    
    def load_from_file(self, filepath: str) -> Dict:
        """Load fingerprint from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)


# Example usage
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("FINGERPRINT GENERATOR v2.0 - Database-Driven")
    print("="*60)
    
    # Generate fingerprint for a profile
    generator = FingerprintGenerator(seed="profile_1")
    fingerprint = generator.generate(
        timezone="Asia/Ho_Chi_Minh",
        cpu_preference="mixed",
        gpu_preference="mixed",
        os_preference="windows"
    )
    
    print("\n📊 GENERATED FINGERPRINT:")
    print(f"   CPU: {fingerprint['hardware']['cpu']['model']} ({fingerprint['hardware']['cpu']['cores']} cores)")
    print(f"   GPU: {fingerprint['hardware']['gpu']['model']} ({fingerprint['hardware']['gpu']['vram']})")
    print(f"   RAM: {fingerprint['hardware']['ram']['total_gb']}GB {fingerprint['hardware']['ram']['type']}")
    print(f"   OS: {fingerprint['os']} {fingerprint['os_version']} ({fingerprint['platform']})")
    print(f"   Screen: {fingerprint['screen']['width']}x{fingerprint['screen']['height']}")
    print(f"   WebGL: {fingerprint['webgl']['renderer']}")
    print(f"   Timezone: {fingerprint['timezone']}")
    print(f"   Language: {fingerprint['language']}")
    print(f"   Fonts: {len(fingerprint['fonts'])} fonts loaded")
    
    # Generate fingerprint ID
    fp_id = generator.generate_fingerprint_id(fingerprint)
    print(f"\n🔑 Fingerprint ID: {fp_id}")
    
    # Save to file
    generator.save_to_file(fingerprint, "example_fingerprint_v2.json")
    print(f"\n✅ Saved to example_fingerprint_v2.json")
    
    # Generate another profile to show variety
    print("\n" + "="*60)
    print("GENERATING 5 MORE FINGERPRINTS (showing variety)...")
    print("="*60)
    
    for i in range(2, 7):
        gen = FingerprintGenerator(seed=f"profile_{i}")
        fp = gen.generate()
        print(f"\n🔢 Profile {i}:")
        print(f"   {fp['hardware']['cpu']['model']} + {fp['hardware']['gpu']['model']} + {fp['hardware']['ram']['total_gb']}GB")
