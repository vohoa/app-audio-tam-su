"""
Profile Fingerprint Manager

Quản lý fingerprints cho từng profile và apply vào Chrome driver.
"""

import os
import json
import logging
from typing import Dict, Optional
from pathlib import Path

from .fingerprint_generator import FingerprintGenerator

logger = logging.getLogger(__name__)


class ProfileFingerprintManager:
    """
    Manage browser fingerprints for profiles
    """
    
    def __init__(self, profiles_dir: str = "chrome_profiles", 
                 configs_dir: str = "profile_configs"):
        """
        Initialize fingerprint manager
        
        Args:
            profiles_dir: Directory containing Chrome profiles
            configs_dir: Directory to store fingerprint configs
        """
        self.profiles_dir = Path(profiles_dir)
        self.configs_dir = Path(configs_dir)
        
        # Ensure configs directory exists
        self.configs_dir.mkdir(parents=True, exist_ok=True)
        
        # Load stealth JavaScript
        self.stealth_js = self._load_stealth_js()
        
        logger.info(f"📁 ProfileFingerprintManager initialized")
        logger.info(f"   Profiles dir: {self.profiles_dir}")
        logger.info(f"   Configs dir: {self.configs_dir}")
    
    def _load_stealth_js(self) -> str:
        """Load stealth JavaScript from file"""
        js_file = Path(__file__).parent / "stealth_scripts.js"
        
        if not js_file.exists():
            logger.warning(f"⚠️ Stealth JS not found: {js_file}")
            return ""
        
        try:
            with open(js_file, 'r', encoding='utf-8') as f:
                js_content = f.read()
            logger.info(f"✅ Loaded stealth JS: {len(js_content)} bytes")
            return js_content
        except Exception as e:
            logger.error(f"❌ Failed to load stealth JS: {e}")
            return ""
    
    def get_or_create_fingerprint(self, profile_name: str, 
                                   timezone: Optional[str] = None,
                                   cpu_preference: str = "mixed",
                                   gpu_preference: str = "mixed",
                                   os_preference: str = "windows",
                                   custom_config: Optional[Dict] = None) -> Dict:
        """
        Get existing fingerprint or create new one for profile (v2.0 with database support)
        
        Args:
            profile_name: Name of the profile
            timezone: Timezone to use (default: Asia/Ho_Chi_Minh)
            cpu_preference: "intel", "amd", or "mixed" (default)
            gpu_preference: "nvidia", "amd", "intel", or "mixed" (default)
            os_preference: "windows", "macos", "linux", or "mixed" (default)
            custom_config: Custom fingerprint overrides
            
        Returns:
            Dict: Fingerprint configuration (v1.0 or v2.0 depending on generator version)
        """
        config_file = self.configs_dir / f"{profile_name}_fingerprint.json"
        
        # Load existing fingerprint if available
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    fingerprint = json.load(f)
                logger.info(f"📄 Loaded existing fingerprint for '{profile_name}'")
                logger.debug(f"   Timezone: {fingerprint.get('timezone')}")
                logger.debug(f"   Screen: {fingerprint.get('screen', {}).get('width')}x{fingerprint.get('screen', {}).get('height')}")
                return fingerprint
            except Exception as e:
                logger.warning(f"⚠️ Failed to load fingerprint for '{profile_name}': {e}")
        
        # Generate new fingerprint
        logger.info(f"🆕 Generating new fingerprint for '{profile_name}'...")
        
        generator = FingerprintGenerator(seed=profile_name)
        
        # v2.0: Generate with database preferences
        fingerprint = generator.generate(
            timezone=timezone or "Asia/Ho_Chi_Minh",
            cpu_preference=cpu_preference,
            gpu_preference=gpu_preference,
            os_preference=os_preference,
            custom_config=custom_config
        )
        
        # Log generated fingerprint details
        version = fingerprint.get('version', '1.0.0')
        logger.info(f"   Version: {version}")
        
        if version.startswith("2."):
            # v2.0 with detailed hardware info
            cpu_info = fingerprint.get('hardware', {}).get('cpu', {})
            gpu_info = fingerprint.get('hardware', {}).get('gpu', {})
            ram_info = fingerprint.get('hardware', {}).get('ram', {})
            
            if cpu_info:
                logger.info(f"   CPU: {cpu_info.get('model', 'Unknown')} ({cpu_info.get('cores', 0)} cores)")
            if gpu_info:
                logger.info(f"   GPU: {gpu_info.get('model', 'Unknown')} ({gpu_info.get('vram', 'Unknown')})")
            if ram_info:
                logger.info(f"   RAM: {ram_info.get('total_gb', 0)}GB {ram_info.get('type', 'DDR4')}")
        else:
            # v1.0 with basic hardware info
            hardware = fingerprint.get('hardware', {})
            logger.info(f"   CPU cores: {hardware.get('cpu_cores', 0)}")
            logger.info(f"   RAM: {hardware.get('memory_gb', 0)}GB")
        
        # Save to file
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(fingerprint, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Saved fingerprint to: {config_file}")
        except Exception as e:
            logger.error(f"❌ Failed to save fingerprint: {e}")
        
        return fingerprint
    
    def apply_fingerprint_to_driver(self, driver, fingerprint: Dict) -> bool:
        """
        Apply fingerprint configuration to Chrome driver
        
        Args:
            driver: Selenium WebDriver instance
            fingerprint: Fingerprint configuration
            
        Returns:
            bool: True if successful
        """
        try:
            logger.info("🔧 Applying fingerprint to driver...")
            
            # STEP 1: Inject stealth JavaScript
            if self.stealth_js:
                try:
                    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                        'source': self.stealth_js
                    })
                    logger.info("✅ Injected stealth JavaScript")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to inject stealth JS: {e}")
            
            # STEP 2: Initialize stealth mode with fingerprint config
            init_script = f"""
                if (window.initStealthMode) {{
                    window.fingerprintConfig = {json.dumps(fingerprint)};
                    window.initStealthMode(window.fingerprintConfig);
                }}
            """
            
            try:
                driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': init_script
                })
                logger.info("✅ Initialized stealth mode with fingerprint")
            except Exception as e:
                logger.warning(f"⚠️ Failed to init stealth mode: {e}")
            
            # STEP 3: Set geolocation via CDP
            if fingerprint.get('geolocation'):
                try:
                    geo = fingerprint['geolocation']
                    driver.execute_cdp_cmd('Emulation.setGeolocationOverride', {
                        'latitude': geo['latitude'],
                        'longitude': geo['longitude'],
                        'accuracy': geo['accuracy']
                    })
                    logger.info(f"📍 Set geolocation: {geo['latitude']}, {geo['longitude']}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to set geolocation: {e}")
            
            # STEP 4: Set timezone via CDP
            if fingerprint.get('timezone'):
                try:
                    driver.execute_cdp_cmd('Emulation.setTimezoneOverride', {
                        'timezoneId': fingerprint['timezone']
                    })
                    logger.info(f"🌍 Set timezone: {fingerprint['timezone']}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to set timezone: {e}")
            
            # STEP 5: Set user agent via CDP (if needed)
            if fingerprint.get('user_agent'):
                try:
                    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                        'userAgent': fingerprint['user_agent'],
                        'platform': fingerprint.get('platform', 'Win32'),
                        'acceptLanguage': fingerprint.get('language', 'en-US,en;q=0.9')
                    })
                    logger.info(f"🌐 Set user agent: {fingerprint['user_agent'][:50]}...")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to set user agent: {e}")
            
            # STEP 6: Set locale/language
            if fingerprint.get('language'):
                try:
                    languages = fingerprint['language'].split(',')
                    languages = [l.split(';')[0].strip() for l in languages]
                    
                    driver.execute_cdp_cmd('Emulation.setLocaleOverride', {
                        'locale': languages[0] if languages else 'en-US'
                    })
                    logger.info(f"🗣️ Set locale: {languages[0] if languages else 'en-US'}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to set locale: {e}")
            
            logger.info("✅ Fingerprint applied successfully")
            logger.info(f"   🔑 Fingerprint ID: {self._get_fingerprint_summary(fingerprint)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to apply fingerprint: {e}")
            return False
    
    def _get_fingerprint_summary(self, fingerprint: Dict) -> str:
        """Get short summary of fingerprint for logging"""
        screen = fingerprint.get('screen', {})
        tz = fingerprint.get('timezone', 'Unknown')
        platform = fingerprint.get('platform', 'Unknown')
        
        return f"{screen.get('width', '?')}x{screen.get('height', '?')} | {tz} | {platform}"
    
    def delete_fingerprint(self, profile_name: str) -> bool:
        """
        Delete fingerprint configuration for profile
        
        Args:
            profile_name: Name of the profile
            
        Returns:
            bool: True if deleted successfully
        """
        config_file = self.configs_dir / f"{profile_name}_fingerprint.json"
        
        if not config_file.exists():
            logger.warning(f"⚠️ Fingerprint not found for '{profile_name}'")
            return False
        
        try:
            config_file.unlink()
            logger.info(f"🗑️ Deleted fingerprint for '{profile_name}'")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete fingerprint: {e}")
            return False
    
    def list_fingerprints(self) -> list:
        """
        List all fingerprint configurations
        
        Returns:
            list: List of profile names with fingerprints
        """
        fingerprints = []
        
        for config_file in self.configs_dir.glob("*_fingerprint.json"):
            profile_name = config_file.stem.replace("_fingerprint", "")
            
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    fingerprint = json.load(f)
                
                fingerprints.append({
                    'profile_name': profile_name,
                    'config_file': str(config_file),
                    'timezone': fingerprint.get('timezone'),
                    'screen': f"{fingerprint.get('screen', {}).get('width', '?')}x{fingerprint.get('screen', {}).get('height', '?')}",
                    'platform': fingerprint.get('platform'),
                    'created_at': fingerprint.get('generated_at'),
                })
            except Exception as e:
                logger.warning(f"⚠️ Failed to read {config_file}: {e}")
        
        return fingerprints
    
    def regenerate_fingerprint(self, profile_name: str, 
                               timezone: Optional[str] = None,
                               custom_config: Optional[Dict] = None) -> Dict:
        """
        Force regenerate fingerprint for profile (delete old + create new)
        
        Args:
            profile_name: Name of the profile
            timezone: Timezone to use
            custom_config: Custom fingerprint overrides
            
        Returns:
            Dict: New fingerprint configuration
        """
        logger.info(f"🔄 Regenerating fingerprint for '{profile_name}'...")
        
        # Delete old fingerprint
        self.delete_fingerprint(profile_name)
        
        # Generate new fingerprint
        return self.get_or_create_fingerprint(profile_name, timezone, custom_config)


# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create manager
    manager = ProfileFingerprintManager()
    
    # Generate fingerprint for a profile
    fingerprint = manager.get_or_create_fingerprint(
        profile_name="test_profile",
        timezone="Asia/Ho_Chi_Minh"
    )
    
    print("\n" + "="*60)
    print("GENERATED FINGERPRINT")
    print("="*60)
    print(json.dumps(fingerprint, indent=2, ensure_ascii=False))
    
    # List all fingerprints
    print("\n" + "="*60)
    print("ALL FINGERPRINTS")
    print("="*60)
    for fp in manager.list_fingerprints():
        print(f"📋 {fp['profile_name']}")
        print(f"   Screen: {fp['screen']}")
        print(f"   Timezone: {fp['timezone']}")
        print(f"   Platform: {fp['platform']}")
        print()
