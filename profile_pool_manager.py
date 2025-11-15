"""
Profile Pool Manager Module
Quản lý pool của nhiều Chrome profiles để luân phiên tránh antibot
"""
import os
import json
import random
from typing import List, Optional, Dict
from datetime import datetime
from logger_config import LoggerConfig

# Initialize logger
logger = LoggerConfig.get_logger('profile_pool_manager')


class ProfilePoolManager:
    """
    Quản lý pool của nhiều Chrome profiles để luân phiên sử dụng
    
    Features:
    - Lưu danh sách profiles trong file JSON
    - Random selection từ pool
    - Track usage count và last used time
    - Active/Inactive profile management
    """
    
    def __init__(self, pool_file: Optional[str] = None):
        """
        Khởi tạo Profile Pool Manager
        
        Args:
            pool_file: Đường dẫn đến file JSON lưu profile pool
                       (default: chrome_profiles/profile_pool.json)
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        if pool_file is None:
            self.pool_file = os.path.join(current_dir, 'chrome_profiles', 'profile_pool.json')
        else:
            self.pool_file = pool_file
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.pool_file), exist_ok=True)
        
        # Load pool data
        self.pool_data = self._load_pool()
        
        logger.info(f"📦 ProfilePoolManager initialized with {len(self.get_active_profiles())} active profiles")
    
    # ============================================
    # Data Persistence Methods
    # ============================================
    
    def _load_pool(self) -> Dict:
        """
        Load profile pool data from JSON file
        
        Returns:
            Dict với structure:
            {
                'profiles': [
                    {
                        'name': str,
                        'active': bool,
                        'usage_count': int,
                        'last_used': str (ISO format),
                        'added_date': str (ISO format),
                        'notes': str
                    }
                ]
            }
        """
        try:
            if os.path.exists(self.pool_file):
                with open(self.pool_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"✅ Loaded profile pool from: {self.pool_file}")
                return data
            else:
                logger.info(f"⚠️ Profile pool file not found, creating new: {self.pool_file}")
                # Create default pool with existing profiles if any
                default_pool = {'profiles': []}
                
                # Auto-discover existing profiles in chrome_profiles directory
                chrome_profiles_dir = os.path.dirname(self.pool_file)
                if os.path.exists(chrome_profiles_dir):
                    for item in os.listdir(chrome_profiles_dir):
                        item_path = os.path.join(chrome_profiles_dir, item)
                        if os.path.isdir(item_path) and item not in ['profile_pool.json']:
                            # Add to default pool
                            default_pool['profiles'].append({
                                'name': item,
                                'active': True,
                                'usage_count': 0,
                                'last_used': None,
                                'added_date': datetime.now().isoformat(),
                                'notes': 'Auto-discovered'
                            })
                            logger.info(f"🔍 Auto-discovered profile: {item}")
                
                # Save default pool
                self._save_pool(default_pool)
                return default_pool
                
        except Exception as e:
            logger.error(f"❌ Failed to load profile pool: {e}", exc_info=True)
            return {'profiles': []}
    
    def _save_pool(self, data: Optional[Dict] = None):
        """
        Save profile pool data to JSON file
        
        Args:
            data: Pool data to save (if None, use self.pool_data)
        """
        try:
            data_to_save = data if data is not None else self.pool_data
            
            with open(self.pool_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Saved profile pool to: {self.pool_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save profile pool: {e}", exc_info=True)
    
    # ============================================
    # Profile Management Methods
    # ============================================
    
    def add_profile(self, profile_name: str, active: bool = True, notes: str = '') -> bool:
        """
        Add a new profile to the pool
        
        Args:
            profile_name: Tên profile
            active: Profile có active hay không (default: True)
            notes: Ghi chú về profile
            
        Returns:
            True nếu thêm thành công, False nếu profile đã tồn tại
        """
        # Check if profile already exists
        if self.profile_exists(profile_name):
            logger.warning(f"⚠️ Profile already exists in pool: {profile_name}")
            return False
        
        # Add profile
        new_profile = {
            'name': profile_name,
            'active': active,
            'usage_count': 0,
            'last_used': None,
            'added_date': datetime.now().isoformat(),
            'notes': notes
        }
        
        self.pool_data['profiles'].append(new_profile)
        self._save_pool()
        
        logger.info(f"✅ Added profile to pool: {profile_name} (active={active})")
        return True
    
    def remove_profile(self, profile_name: str) -> bool:
        """
        Remove a profile from the pool
        
        Args:
            profile_name: Tên profile cần xóa
            
        Returns:
            True nếu xóa thành công, False nếu không tìm thấy
        """
        profiles = self.pool_data['profiles']
        
        # Find and remove
        for i, profile in enumerate(profiles):
            if profile['name'] == profile_name:
                removed = profiles.pop(i)
                self._save_pool()
                logger.info(f"🗑️ Removed profile from pool: {profile_name}")
                return True
        
        logger.warning(f"⚠️ Profile not found in pool: {profile_name}")
        return False
    
    def update_profile(self, profile_name: str, **kwargs) -> bool:
        """
        Update profile properties
        
        Args:
            profile_name: Tên profile
            **kwargs: Properties to update (active, notes, etc.)
            
        Returns:
            True nếu update thành công
        """
        profile = self._get_profile_by_name(profile_name)
        
        if profile is None:
            logger.warning(f"⚠️ Profile not found: {profile_name}")
            return False
        
        # Update properties
        for key, value in kwargs.items():
            if key in profile:
                profile[key] = value
        
        self._save_pool()
        logger.info(f"✅ Updated profile: {profile_name}")
        return True
    
    def set_profile_active(self, profile_name: str, active: bool) -> bool:
        """
        Set profile active/inactive status
        
        Args:
            profile_name: Tên profile
            active: True = active, False = inactive
            
        Returns:
            True nếu thành công
        """
        return self.update_profile(profile_name, active=active)
    
    # ============================================
    # Profile Query Methods
    # ============================================
    
    def profile_exists(self, profile_name: str) -> bool:
        """Check if profile exists in pool"""
        return any(p['name'] == profile_name for p in self.pool_data['profiles'])
    
    def _get_profile_by_name(self, profile_name: str) -> Optional[Dict]:
        """Get profile data by name"""
        for profile in self.pool_data['profiles']:
            if profile['name'] == profile_name:
                return profile
        return None
    
    def get_all_profiles(self) -> List[Dict]:
        """Get all profiles in pool"""
        return self.pool_data['profiles']
    
    def get_active_profiles(self) -> List[Dict]:
        """Get only active profiles"""
        return [p for p in self.pool_data['profiles'] if p.get('active', True)]
    
    def get_inactive_profiles(self) -> List[Dict]:
        """Get only inactive profiles"""
        return [p for p in self.pool_data['profiles'] if not p.get('active', True)]
    
    def get_profile_count(self) -> Dict[str, int]:
        """
        Get profile counts
        
        Returns:
            Dict with counts: {'total': int, 'active': int, 'inactive': int}
        """
        all_profiles = self.get_all_profiles()
        active = self.get_active_profiles()
        
        return {
            'total': len(all_profiles),
            'active': len(active),
            'inactive': len(all_profiles) - len(active)
        }
    
    # ============================================
    # Random Selection Methods
    # ============================================
    
    def get_random_profile(self, only_active: bool = True) -> Optional[str]:
        """
        Get random profile from pool
        
        Args:
            only_active: Chỉ chọn từ active profiles (default: True)
            
        Returns:
            Profile name (str) hoặc None nếu pool rỗng
        """
        profiles = self.get_active_profiles() if only_active else self.get_all_profiles()
        
        if not profiles:
            logger.warning("⚠️ No profiles available for random selection")
            return None
        
        selected = random.choice(profiles)
        profile_name = selected['name']
        
        # Update usage statistics
        self._record_profile_usage(profile_name)
        
        logger.info(f"🎲 Randomly selected profile: {profile_name} (from {len(profiles)} profiles)")
        return profile_name
    
    def get_least_used_profile(self, only_active: bool = True) -> Optional[str]:
        """
        Get least used profile from pool (for load balancing)
        
        Args:
            only_active: Chỉ chọn từ active profiles (default: True)
            
        Returns:
            Profile name (str) hoặc None nếu pool rỗng
        """
        profiles = self.get_active_profiles() if only_active else self.get_all_profiles()
        
        if not profiles:
            logger.warning("⚠️ No profiles available for selection")
            return None
        
        # Sort by usage_count (ascending)
        sorted_profiles = sorted(profiles, key=lambda p: p.get('usage_count', 0))
        selected = sorted_profiles[0]
        profile_name = selected['name']
        
        # Update usage statistics
        self._record_profile_usage(profile_name)
        
        logger.info(f"⚖️ Selected least used profile: {profile_name} (usage: {selected.get('usage_count', 0)})")
        return profile_name
    
    def _record_profile_usage(self, profile_name: str):
        """
        Record profile usage (increment count, update timestamp)
        
        Args:
            profile_name: Tên profile
        """
        profile = self._get_profile_by_name(profile_name)
        
        if profile:
            profile['usage_count'] = profile.get('usage_count', 0) + 1
            profile['last_used'] = datetime.now().isoformat()
            self._save_pool()
    
    # ============================================
    # Utility Methods
    # ============================================
    
    def get_profile_stats(self, profile_name: str) -> Optional[Dict]:
        """
        Get statistics for a specific profile
        
        Args:
            profile_name: Tên profile
            
        Returns:
            Dict with stats hoặc None nếu không tìm thấy
        """
        profile = self._get_profile_by_name(profile_name)
        
        if profile is None:
            return None
        
        return {
            'name': profile['name'],
            'active': profile.get('active', True),
            'usage_count': profile.get('usage_count', 0),
            'last_used': profile.get('last_used'),
            'added_date': profile.get('added_date'),
            'notes': profile.get('notes', '')
        }
    
    def reset_usage_stats(self, profile_name: Optional[str] = None):
        """
        Reset usage statistics
        
        Args:
            profile_name: Tên profile cần reset (None = reset all)
        """
        if profile_name:
            profile = self._get_profile_by_name(profile_name)
            if profile:
                profile['usage_count'] = 0
                profile['last_used'] = None
                logger.info(f"🔄 Reset stats for profile: {profile_name}")
        else:
            for profile in self.pool_data['profiles']:
                profile['usage_count'] = 0
                profile['last_used'] = None
            logger.info("🔄 Reset stats for all profiles")
        
        self._save_pool()
    
    def export_pool(self, output_file: str):
        """
        Export profile pool to a JSON file
        
        Args:
            output_file: Đường dẫn file output
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.pool_data, f, ensure_ascii=False, indent=2)
            logger.info(f"📤 Exported profile pool to: {output_file}")
        except Exception as e:
            logger.error(f"❌ Failed to export pool: {e}", exc_info=True)
    
    def import_pool(self, input_file: str, merge: bool = False):
        """
        Import profile pool from a JSON file
        
        Args:
            input_file: Đường dẫn file input
            merge: True = merge với pool hiện tại, False = replace
        """
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            if merge:
                # Merge profiles
                existing_names = {p['name'] for p in self.pool_data['profiles']}
                for profile in imported_data.get('profiles', []):
                    if profile['name'] not in existing_names:
                        self.pool_data['profiles'].append(profile)
                logger.info(f"📥 Merged profile pool from: {input_file}")
            else:
                # Replace
                self.pool_data = imported_data
                logger.info(f"📥 Imported profile pool from: {input_file}")
            
            self._save_pool()
            
        except Exception as e:
            logger.error(f"❌ Failed to import pool: {e}", exc_info=True)


# ============================================
# Global instance for easy access
# ============================================

_global_pool_manager = None

def get_profile_pool_manager() -> ProfilePoolManager:
    """
    Get global ProfilePoolManager instance (singleton pattern)
    
    Returns:
        ProfilePoolManager instance
    """
    global _global_pool_manager
    
    if _global_pool_manager is None:
        _global_pool_manager = ProfilePoolManager()
    
    return _global_pool_manager
