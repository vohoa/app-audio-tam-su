"""
Browser Fingerprint Anti-Detection System

Hệ thống tạo và quản lý browser fingerprints độc nhất cho mỗi profile
để tránh bị Google và các website phát hiện automation.

Components:
- FingerprintGenerator: Tạo fingerprint configurations độc nhất
- ProfileFingerprintManager: Quản lý fingerprints cho profiles
- Stealth Scripts: JavaScript injection để bypass detection
"""

from .fingerprint_generator import FingerprintGenerator
from .profile_fingerprint_manager import ProfileFingerprintManager

__version__ = "1.0.0"
__all__ = ["FingerprintGenerator", "ProfileFingerprintManager"]
