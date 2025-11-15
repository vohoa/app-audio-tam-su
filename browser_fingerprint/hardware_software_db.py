"""
Hardware & Software Database Manager

Load và cache databases, cung cấp API để query hardware/software specs.
"""

import json
import os
import random
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class HardwareSoftwareDatabase:
    """
    Manager for hardware and software databases
    """
    
    def __init__(self):
        """Initialize database manager"""
        self.base_path = Path(__file__).parent
        self.hardware_db_path = self.base_path / "hardware_db"
        self.software_db_path = self.base_path / "software_db"
        
        # Cache for loaded databases
        self._cache = {}
        
        logger.info("🗄️ Hardware/Software Database Manager initialized")
    
    def _load_json(self, filepath: Path) -> Dict:
        """Load JSON file with caching"""
        cache_key = str(filepath)
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._cache[cache_key] = data
            logger.debug(f"📂 Loaded: {filepath.name}")
            return data
        except Exception as e:
            logger.error(f"❌ Failed to load {filepath}: {e}")
            return {}
    
    # ==================== CPU ====================
    
    def get_random_cpu(self, preference: str = "mixed") -> Dict:
        """
        Get random CPU based on preference
        
        Args:
            preference: "intel", "amd", or "mixed" (default)
            
        Returns:
            Dict: CPU specifications
        """
        cpus_data = self._load_json(self.hardware_db_path / "cpus.json")
        
        if preference == "intel":
            cpu_pool = cpus_data.get("intel_cpus", [])
        elif preference == "amd":
            cpu_pool = cpus_data.get("amd_cpus", [])
        else:  # mixed
            intel_cpus = cpus_data.get("intel_cpus", [])
            amd_cpus = cpus_data.get("amd_cpus", [])
            cpu_pool = intel_cpus + amd_cpus
        
        if not cpu_pool:
            return self._get_fallback_cpu()
        
        # Weighted random choice based on market_share
        weights = [cpu.get("market_share", 1) for cpu in cpu_pool]
        return random.choices(cpu_pool, weights=weights, k=1)[0]
    
    def _get_fallback_cpu(self) -> Dict:
        """Fallback CPU if database load fails"""
        return {
            "model": "Intel Core i5-12400",
            "cores": 6,
            "threads": 12,
            "base_clock": "2.5 GHz",
            "max_clock": "4.4 GHz",
            "generation": "12th Gen",
            "tdp": "65W"
        }
    
    # ==================== GPU ====================
    
    def get_random_gpu(self, preference: str = "mixed", 
                       performance_tier: Optional[str] = None) -> Dict:
        """
        Get random GPU based on preference and performance tier
        
        Args:
            preference: "nvidia", "amd", "intel", or "mixed" (default)
            performance_tier: "integrated", "entry", "mid", "high", "enthusiast", or None
            
        Returns:
            Dict: GPU specifications
        """
        gpus_data = self._load_json(self.hardware_db_path / "gpus.json")
        
        # Build GPU pool
        if preference == "nvidia":
            gpu_pool = gpus_data.get("nvidia_gpus", [])
        elif preference == "amd":
            gpu_pool = gpus_data.get("amd_gpus", [])
        elif preference == "intel":
            gpu_pool = gpus_data.get("intel_gpus", [])
        else:  # mixed
            nvidia_gpus = gpus_data.get("nvidia_gpus", [])
            amd_gpus = gpus_data.get("amd_gpus", [])
            intel_gpus = gpus_data.get("intel_gpus", [])
            gpu_pool = nvidia_gpus + amd_gpus + intel_gpus
        
        # Filter by performance tier if specified
        if performance_tier:
            gpu_pool = [gpu for gpu in gpu_pool if gpu.get("performance_tier") == performance_tier]
        
        if not gpu_pool:
            return self._get_fallback_gpu()
        
        # Weighted random choice
        weights = [gpu.get("market_share", 1) for gpu in gpu_pool]
        return random.choices(gpu_pool, weights=weights, k=1)[0]
    
    def _get_fallback_gpu(self) -> Dict:
        """Fallback GPU if database load fails"""
        return {
            "model": "NVIDIA GeForce GTX 1660 Ti",
            "vram": "6GB",
            "webgl_vendor": "Google Inc. (NVIDIA)",
            "webgl_renderer": "ANGLE (NVIDIA GeForce GTX 1660 Ti Direct3D11 vs_5_0 ps_5_0)",
            "performance_tier": "mid"
        }
    
    # ==================== RAM ====================
    
    def get_random_ram(self, min_gb: Optional[int] = None,
                       max_gb: Optional[int] = None) -> Dict:
        """
        Get random RAM configuration
        
        Args:
            min_gb: Minimum RAM in GB
            max_gb: Maximum RAM in GB
            
        Returns:
            Dict: RAM specifications
        """
        ram_data = self._load_json(self.hardware_db_path / "ram.json")
        ram_pool = ram_data.get("ram_configs", [])
        
        # Filter by min/max if specified
        if min_gb:
            ram_pool = [ram for ram in ram_pool if ram.get("total_gb", 0) >= min_gb]
        if max_gb:
            ram_pool = [ram for ram in ram_pool if ram.get("total_gb", 999) <= max_gb]
        
        if not ram_pool:
            return self._get_fallback_ram()
        
        # Weighted random choice
        weights = [ram.get("market_share", 1) for ram in ram_pool]
        return random.choices(ram_pool, weights=weights, k=1)[0]
    
    def _get_fallback_ram(self) -> Dict:
        """Fallback RAM if database load fails"""
        return {
            "total_gb": 16,
            "device_memory_gb": 8,
            "type": "DDR4"
        }
    
    # ==================== Monitor ====================
    
    def get_random_monitor(self, min_width: Optional[int] = None,
                           max_width: Optional[int] = None) -> Dict:
        """
        Get random monitor configuration
        
        Args:
            min_width: Minimum resolution width
            max_width: Maximum resolution width
            
        Returns:
            Dict: Monitor specifications
        """
        monitor_data = self._load_json(self.hardware_db_path / "monitors.json")
        monitor_pool = monitor_data.get("monitors", [])
        
        # Filter by width if specified
        if min_width:
            monitor_pool = [m for m in monitor_pool if m.get("width", 0) >= min_width]
        if max_width:
            monitor_pool = [m for m in monitor_pool if m.get("width", 9999) <= max_width]
        
        if not monitor_pool:
            return self._get_fallback_monitor()
        
        # Weighted random choice
        weights = [m.get("market_share", 1) for m in monitor_pool]
        return random.choices(monitor_pool, weights=weights, k=1)[0]
    
    def _get_fallback_monitor(self) -> Dict:
        """Fallback monitor if database load fails"""
        return {
            "resolution": "1920x1080",
            "width": 1920,
            "height": 1080,
            "aspect_ratio": "16:9",
            "name": "Full HD",
            "color_depth": 24
        }
    
    # ==================== Audio Device ====================
    
    def get_random_audio_device(self, type: str = "integrated") -> Dict:
        """
        Get random audio device
        
        Args:
            type: "integrated" or "dedicated"
            
        Returns:
            Dict: Audio device specifications
        """
        audio_data = self._load_json(self.hardware_db_path / "audio_devices.json")
        
        if type == "dedicated":
            audio_pool = audio_data.get("dedicated_audio", [])
        else:
            audio_pool = audio_data.get("integrated_audio", [])
        
        if not audio_pool:
            return {"name": "Realtek High Definition Audio", "chipset": "ALC887"}
        
        weights = [a.get("market_share", 1) for a in audio_pool]
        return random.choices(audio_pool, weights=weights, k=1)[0]
    
    # ==================== Network Adapter ====================
    
    def get_random_network_adapter(self, type: str = "ethernet") -> Dict:
        """
        Get random network adapter
        
        Args:
            type: "ethernet" or "wifi"
            
        Returns:
            Dict: Network adapter specifications
        """
        network_data = self._load_json(self.hardware_db_path / "network_adapters.json")
        
        if type == "wifi":
            network_pool = network_data.get("wifi_adapters", [])
        else:
            network_pool = network_data.get("ethernet_adapters", [])
        
        if not network_pool:
            return {"name": "Realtek PCIe GbE Family Controller", "chipset": "RTL8111H"}
        
        weights = [n.get("market_share", 1) for n in network_pool]
        return random.choices(network_pool, weights=weights, k=1)[0]
    
    # ==================== Operating System ====================
    
    def get_random_os(self, preference: str = "windows") -> Dict:
        """
        Get random operating system
        
        Args:
            preference: "windows", "macos", "linux", or "mixed"
            
        Returns:
            Dict: OS specifications
        """
        os_data = self._load_json(self.software_db_path / "operating_systems.json")
        
        if preference == "windows":
            os_pool = os_data.get("windows", [])
        elif preference == "macos":
            os_pool = os_data.get("macos", [])
        elif preference == "linux":
            os_pool = os_data.get("linux", [])
        else:  # mixed
            windows = os_data.get("windows", [])
            macos = os_data.get("macos", [])
            linux = os_data.get("linux", [])
            os_pool = windows + macos + linux
        
        if not os_pool:
            return self._get_fallback_os()
        
        weights = [os.get("market_share", 1) for os in os_pool]
        return random.choices(os_pool, weights=weights, k=1)[0]
    
    def _get_fallback_os(self) -> Dict:
        """Fallback OS if database load fails"""
        return {
            "name": "Windows 10",
            "version": "10.0",
            "platform": "Win32",
            "user_agent_version": "10.0"
        }
    
    # ==================== Fonts ====================
    
    def get_fonts_for_os(self, platform: str) -> List[str]:
        """
        Get font list for operating system
        
        Args:
            platform: "Win32", "MacIntel", or "Linux x86_64"
            
        Returns:
            List[str]: List of font names
        """
        fonts_data = self._load_json(self.software_db_path / "fonts.json")
        
        if "Win32" in platform:
            return fonts_data.get("windows_fonts", fonts_data.get("common_fonts", []))
        elif "MacIntel" in platform:
            return fonts_data.get("macos_fonts", fonts_data.get("common_fonts", []))
        elif "Linux" in platform:
            return fonts_data.get("linux_fonts", fonts_data.get("common_fonts", []))
        else:
            return fonts_data.get("common_fonts", [])
    
    # ==================== Languages ====================
    
    def get_language_for_timezone(self, timezone: str) -> str:
        """
        Get appropriate language string for timezone
        
        Args:
            timezone: Timezone string (e.g., "Asia/Ho_Chi_Minh")
            
        Returns:
            str: Language string (e.g., "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7")
        """
        languages_data = self._load_json(self.software_db_path / "languages.json")
        language_packs = languages_data.get("language_packs", {})
        
        if timezone in language_packs:
            primary_langs = language_packs[timezone].get("primary", [])
            return random.choice(primary_langs) if primary_langs else "en-US,en;q=0.9"
        
        # Fallback to English
        return "en-US,en;q=0.9"
    
    # ==================== Realistic Hardware Mix ====================
    
    def generate_realistic_hardware_mix(self, 
                                        cpu_preference: str = "mixed",
                                        gpu_preference: str = "mixed",
                                        os_preference: str = "windows") -> Dict:
        """
        Generate realistic hardware combination based on market logic
        
        Args:
            cpu_preference: "intel", "amd", or "mixed"
            gpu_preference: "nvidia", "amd", "intel", or "mixed"
            os_preference: "windows", "macos", "linux", or "mixed"
            
        Returns:
            Dict: Complete hardware specifications
        """
        # Get CPU first (determines performance tier)
        cpu = self.get_random_cpu(cpu_preference)
        cpu_cores = cpu.get("cores", 6)
        
        # Determine GPU tier based on CPU cores
        if cpu_cores <= 4:
            gpu_tier = random.choice(["integrated", "entry"])
        elif cpu_cores <= 8:
            gpu_tier = random.choice(["entry", "mid"])
        elif cpu_cores <= 12:
            gpu_tier = random.choice(["mid", "high"])
        else:
            gpu_tier = random.choice(["high", "enthusiast"])
        
        gpu = self.get_random_gpu(gpu_preference, gpu_tier)
        
        # RAM based on CPU tier
        if cpu_cores <= 4:
            ram = self.get_random_ram(min_gb=4, max_gb=8)
        elif cpu_cores <= 8:
            ram = self.get_random_ram(min_gb=8, max_gb=16)
        elif cpu_cores <= 12:
            ram = self.get_random_ram(min_gb=16, max_gb=32)
        else:
            ram = self.get_random_ram(min_gb=32, max_gb=128)
        
        # Monitor (QHD/4K for high-end, FHD for others)
        if gpu_tier in ["high", "enthusiast"]:
            monitor = self.get_random_monitor(min_width=1920)
        else:
            monitor = self.get_random_monitor(max_width=1920)
        
        # Audio & Network
        audio = self.get_random_audio_device("integrated")
        network_eth = self.get_random_network_adapter("ethernet")
        network_wifi = self.get_random_network_adapter("wifi")
        
        # Operating System
        os = self.get_random_os(os_preference)
        
        # Fonts
        fonts = self.get_fonts_for_os(os.get("platform", "Win32"))
        
        return {
            "cpu": cpu,
            "gpu": gpu,
            "ram": ram,
            "monitor": monitor,
            "audio": audio,
            "network": {
                "ethernet": network_eth,
                "wifi": network_wifi
            },
            "os": os,
            "fonts": fonts
        }


# Global instance
_db_instance = None

def get_database() -> HardwareSoftwareDatabase:
    """Get global database instance (singleton)"""
    global _db_instance
    if _db_instance is None:
        _db_instance = HardwareSoftwareDatabase()
    return _db_instance


# Example usage
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    db = get_database()
    
    print("\n" + "="*60)
    print("REALISTIC HARDWARE MIX")
    print("="*60)
    
    hardware = db.generate_realistic_hardware_mix(
        cpu_preference="mixed",
        gpu_preference="mixed",
        os_preference="windows"
    )
    
    print(f"\n🖥️ CPU: {hardware['cpu']['model']} ({hardware['cpu']['cores']} cores)")
    print(f"🎮 GPU: {hardware['gpu']['model']} ({hardware['gpu'].get('vram', 'N/A')})")
    print(f"💾 RAM: {hardware['ram']['total_gb']}GB {hardware['ram']['type']}")
    print(f"🖥️ Monitor: {hardware['monitor']['resolution']} ({hardware['monitor']['name']})")
    print(f"🔊 Audio: {hardware['audio']['name']}")
    print(f"🌐 Network: {hardware['network']['ethernet']['name']}")
    print(f"💻 OS: {hardware['os']['name']}")
    print(f"🔤 Fonts: {len(hardware['fonts'])} fonts")
