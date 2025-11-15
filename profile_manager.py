"""
Chrome Profile Manager Module
Quản lý Chrome profiles cho ứng dụng
"""
import os
import sys
import subprocess
import time
import json
from typing import List, Optional, Dict
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QInputDialog,
    QGroupBox, QTextEdit, QTabWidget, QCheckBox, QFileDialog,
    QComboBox, QFormLayout, QLineEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from logger_config import LoggerConfig
from profile_pool_manager import get_profile_pool_manager
from proxy_manager import ProxyManagerDialog, ProxyManager, ProxyData
import config  # Import config module for Chrome paths

# Import undetected_chromedriver
try:
    import undetected_chromedriver as uc
    UC_AVAILABLE = True
except ImportError:
    UC_AVAILABLE = False
    logger = LoggerConfig.get_logger('profile_manager')
    logger.warning("⚠️ undetected_chromedriver not available, will use subprocess fallback")

# Initialize logger
logger = LoggerConfig.get_logger('profile_manager')


class ChromeProfileLauncher(QThread):
    """Worker thread to launch Chrome with a specific profile using undetected_chromedriver"""
    
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, chrome_binary_path: str, profile_path: str, profile_name: str, 
                 chromedriver_path: Optional[str] = None, download_path: Optional[str] = None):
        super().__init__()
        # Use config paths if provided paths are empty/None
        self.chrome_binary_path = chrome_binary_path or config.get_chrome_binary_path()
        self.profile_path = profile_path
        self.profile_name = profile_name
        self.chromedriver_path = chromedriver_path or config.get_chrome_driver_path()
        self.download_path = download_path or config.get_audio_download_path()
        self.driver = None
        
        # Log detected paths
        logger.info(f"📋 Chrome Configuration:")
        logger.info(f"   Binary: {self.chrome_binary_path}")
        logger.info(f"   Driver: {self.chromedriver_path or 'Auto-managed'}")
        logger.info(f"   Profile: {self.profile_path}")
        
        # Ensure download path exists
        os.makedirs(self.download_path, exist_ok=True)
        
    def run(self):
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"🚀 Launching Chrome with profile: {self.profile_name} (Attempt {retry_count + 1}/{max_retries})")
                logger.info(f"   Binary: {self.chrome_binary_path}")
                logger.info(f"   Profile: {self.profile_path}")
                
                # Check if Chrome binary exists
                if not os.path.exists(self.chrome_binary_path):
                    error_msg = f"Chrome binary not found: {self.chrome_binary_path}"
                    logger.error(error_msg)
                    self.finished.emit(False, error_msg)
                    return
                
                # ALWAYS clean up before each attempt (not just retries)
                logger.info("🧹 Pre-launch cleanup...")
                try:
                    # 1. Kill all zombie chromedriver processes
                    subprocess.run(
                        ["pkill", "-9", "-f", "chromedriver.*defunct"],
                        capture_output=True,
                        timeout=5
                    )
                    
                    # 2. Remove profile lock files
                    lock_patterns = ["SingletonLock", "SingletonSocket", "SingletonCookie"]
                    for pattern in lock_patterns:
                        lock_file = os.path.join(self.profile_path, pattern)
                        if os.path.exists(lock_file):
                            try:
                                os.remove(lock_file)
                                logger.debug(f"   Removed {pattern}")
                            except:
                                pass
                    
                    # 3. Wait for cleanup to take effect
                    if retry_count > 0:
                        time.sleep(2)
                    
                    logger.info("✅ Cleanup complete")
                except Exception as cleanup_error:
                    logger.debug(f"Cleanup error (non-critical): {cleanup_error}")
                
                # Method 1: Try using undetected_chromedriver (preferred)
                if UC_AVAILABLE:
                    try:
                        logger.info("🔧 Using undetected_chromedriver (stealth mode)...")
                        
                        # Setup Chrome options
                        options = uc.ChromeOptions()
                        
                        # Set Chrome binary path
                        # options.binary_location = self.chrome_binary_path
                        
                        # Set user data directory (profile path)
                        options.add_argument(f"--user-data-dir={self.profile_path}")
                        
                        # Additional options (matching test_stealth.py for WebGL support)
                        options.add_argument('--no-sandbox')
                        options.add_argument('--disable-dev-shm-usage')
                        options.add_argument('--start-maximized')
                        # NOTE: DO NOT use --disable-gpu as it breaks WebGL!
                        
                        # Add timeout arguments to fail faster
                        options.add_argument('--connect-timeout=30')
                        options.add_argument('--timeout=30')
                        
                        # Preferences
                        prefs = {
                            'profile.default_content_setting_values.notifications': 2,
                            'download.default_directory': self.download_path,
                            'download.prompt_for_download': False,
                            'profile.default_content_settings.popups': 0,
                            'credentials_enable_service': False,
                            'profile.password_manager_enabled': False,
                        }
                        options.add_experimental_option('prefs', prefs)
                        
                        # Chrome binary path - Use from config if available
                        # Force use Chrome-for-Testing to match ChromeDriver version
                        if self.chrome_binary_path and os.path.exists(self.chrome_binary_path):
                            options.binary_location = self.chrome_binary_path
                            logger.info(f"🌐 Using Chrome binary: {self.chrome_binary_path}")
                            # Get and log Chrome version
                            chrome_version = config.get_chrome_version(self.chrome_binary_path)
                            logger.info(f"📊 Chrome version: {chrome_version}")
                        else:
                            logger.warning("⚠️ Chrome binary not found, will use auto-detect")
                    
                        # Initialize undetected Chrome driver
                        logger.info("⏳ Starting Chrome driver (timeout: 30s)...")
                        
                        driver_args = {
                            'options': options,
                            'use_subprocess': True,
                            'version_main': 141  # Chỉ định version Chrome để tải đúng ChromeDriver
                        }
                        
                        # Use ChromeDriver from config if available
                        if self.chromedriver_path and os.path.exists(self.chromedriver_path):
                            driver_args['driver_executable_path'] = self.chromedriver_path
                            logger.info(f"🔧 Using ChromeDriver: {self.chromedriver_path}")
                        else:
                            logger.info("🔧 Using auto-managed ChromeDriver")
                        
                        self.driver = uc.Chrome(**driver_args)
                        
                        logger.info("✅ undetected_chromedriver initialized successfully")
                        logger.info("🔒 Bot detection bypass: ACTIVE (auto-patched ChromeDriver)")
                        
                        # Additional manual overrides (optional, undetected_chromedriver handles most)
                        try:
                            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                                'source': '''
                                    // Additional stealth (undetected_chromedriver already handles most)
                                    Object.defineProperty(navigator, 'languages', {
                                        get: () => ['en-US', 'en', 'vi-VN', 'vi']
                                    });
                                    
                                    // Ensure window.chrome exists
                                    if (!window.chrome) {
                                        window.chrome = { runtime: {} };
                                    }
                                '''
                            })
                            logger.info("✅ Additional stealth overrides applied")
                        except Exception as override_error:
                            logger.debug(f"Minor: Additional overrides failed: {override_error}")
                        
                        # Navigate to Google AI Studio
                        logger.info("🌐 Navigating to Google AI Studio...")
                        self.driver.get("https://aistudio.google.com/")
                        
                        # Keep browser open - don't close driver
                        logger.info("✅ Chrome launched successfully with undetected_chromedriver")
                        self.finished.emit(True, f"Đã mở Chrome với profile: {self.profile_name}")
                        
                        # IMPORTANT: Keep thread alive and driver active
                        # Don't return immediately or driver will be garbage collected
                        # Sleep indefinitely until user closes browser manually
                        logger.info("💤 Thread staying alive to maintain browser session...")
                        logger.info("   Close the browser window when done to release resources")
                        
                        # Keep thread alive - wait until driver session ends
                        try:
                            while True:
                                time.sleep(5)
                                # Check if browser is still alive
                                try:
                                    # Try to get current URL - will fail if browser closed
                                    _ = self.driver.current_url
                                except:
                                    # Browser was closed
                                    logger.info("🔚 Browser closed by user")
                                    break
                        except Exception as sleep_error:
                            logger.debug(f"Sleep interrupted: {sleep_error}")
                        
                        # Cleanup
                        try:
                            self.driver.quit()
                        except:
                            pass
                        
                        # Success - exit retry loop
                        return
                        
                    except Exception as uc_error:
                        logger.warning(f"⚠️ undetected_chromedriver failed (attempt {retry_count + 1}): {uc_error}")
                        
                        # Cleanup failed driver
                        if self.driver:
                            try:
                                self.driver.quit()
                            except:
                                pass
                            self.driver = None
                        
                        # Increment retry counter
                        retry_count += 1
                        
                        if retry_count < max_retries:
                            logger.info(f"🔄 Retrying in 1 second... ({retry_count}/{max_retries})")
                            time.sleep(1)  # Shorter delay - cleanup already done at start of loop
                            continue  # Retry
                        else:
                            # Max retries reached
                            error_msg = f"Failed to launch Chrome after {max_retries} attempts: {str(uc_error)}"
                            logger.error(error_msg)
                            self.finished.emit(False, error_msg)
                            return
                            
            except Exception as outer_error:
                error_msg = f"Lỗi khi mở Chrome: {str(outer_error)}"
                logger.error(error_msg, exc_info=True)
                self.finished.emit(False, error_msg)
            finally:
                # Cleanup driver reference but don't quit (keep browser open if successful)
                pass


class ProfileManagerDialog(QDialog):
    """Dialog for managing Chrome profiles"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Paths - Use config for Chrome paths, fallback to project defaults
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.chrome_profiles_dir = os.path.join(current_dir, 'chrome_profiles')
        
        # Get Chrome paths from config (will auto-detect if not configured)
        self.chrome_binary_path = config.get_chrome_binary_path()
        self.chromedriver_path = config.get_chrome_driver_path()
        self.download_path = config.get_audio_download_path()
        
        # Fallback to project defaults if config returns empty
        if not self.chrome_binary_path:
            self.chrome_binary_path = os.path.join(current_dir, 'chrome-linux64', 'chrome')
        if not self.chromedriver_path:
            self.chromedriver_path = os.path.join(current_dir, 'chrome_driver', 'chromedriver')
        if not self.download_path:
            self.download_path = os.path.join(current_dir, 'audio_downloads')
        
        # Log configuration
        logger.info("📋 ProfileManager Configuration:")
        logger.info(f"   Chrome Binary: {self.chrome_binary_path}")
        logger.info(f"   ChromeDriver: {self.chromedriver_path or 'Auto-managed'}")
        logger.info(f"   Download Path: {self.download_path}")
        
        # Ensure directories exist
        os.makedirs(self.chrome_profiles_dir, exist_ok=True)
        os.makedirs(self.download_path, exist_ok=True)
        
        # Active launcher thread
        self.launcher_thread = None
        
        # Selected profile tracking
        self.selected_profile = None
        
        self.init_ui()
        self.load_profiles()
        
    def init_ui(self):
        """Initialize the UI"""
        self.setWindowTitle('🌐 Quản Lý Chrome Profiles')
        self.setModal(True)
        self.resize(800, 700)
        
        # Initialize proxy manager
        self.proxy_manager = ProxyManager()
        
        # Profile proxy configs dictionary
        self.profile_proxy_config_path = os.path.join(self.chrome_profiles_dir, 'profile_proxies.json')
        self.profile_proxy_configs = self.load_profile_proxy_configs()
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel('<h2>🌐 Quản Lý Chrome Profiles</h2>')
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Description
        desc = QLabel(
            'Quản lý Chrome profiles và Profile Pool để tránh antibot của Google'
        )
        desc.setStyleSheet('color: #666; padding: 5px;')
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Tab 1: Profile Management
        profile_tab = self._create_profile_management_tab()
        self.tab_widget.addTab(profile_tab, '📁 Quản Lý Profiles')
        
        # Tab 2: Profile Pool Management
        pool_tab = self._create_profile_pool_tab()
        self.tab_widget.addTab(pool_tab, '🎲 Profile Pool')
        
        layout.addWidget(self.tab_widget)
        
        # Status label
        self.status_label = QLabel('')
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet('padding: 5px;')
        layout.addWidget(self.status_label)
        
        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        
        close_button = QPushButton('❌ Đóng')
        close_button.clicked.connect(self.accept)
        close_layout.addWidget(close_button)
        
        layout.addLayout(close_layout)
        
        self.setLayout(layout)
        
        # Initialize pool manager
        self.pool_manager = get_profile_pool_manager()
        
        # Load initial data
        self.refresh_pool_list()
    
    # ============================================
    # Profile Pool Management Methods
    # ============================================
    
    def refresh_pool_list(self):
        """Refresh profile pool list display"""
        try:
            self.pool_list.clear()
            
            # Get all profiles from pool
            profiles = self.pool_manager.get_all_profiles()
            
            # Update statistics
            counts = self.pool_manager.get_profile_count()
            stats_text = (
                f"📊 Tổng: {counts['total']} profiles | "
                f"✅ Active: {counts['active']} | "
                f"⏸️ Inactive: {counts['inactive']}"
            )
            self.pool_stats_label.setText(stats_text)
            
            # Add to list
            for profile in profiles:
                name = profile['name']
                active = profile.get('active', True)
                usage_count = profile.get('usage_count', 0)
                last_used = profile.get('last_used', 'Never')
                
                # Format last used
                if last_used and last_used != 'Never':
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(last_used)
                        last_used = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        pass
                
                # Create display text
                status_icon = '✅' if active else '⏸️'
                display_text = f"{status_icon} {name} | Sử dụng: {usage_count} | Lần cuối: {last_used}"
                
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, name)
                
                # Color code
                if active:
                    item.setForeground(Qt.darkGreen)
                else:
                    item.setForeground(Qt.gray)
                
                self.pool_list.addItem(item)
            
            logger.info(f"Refreshed pool list: {counts['total']} profiles")
            
        except Exception as e:
            logger.error(f"Failed to refresh pool list: {e}", exc_info=True)
            self.status_label.setText(f'❌ Lỗi: {str(e)}')
            self.status_label.setStyleSheet('color: #dc3545; padding: 5px;')
    
    def on_pool_item_selected(self, item: QListWidgetItem):
        """Handle pool item selection"""
        self.pool_remove_button.setEnabled(True)
        self.pool_toggle_button.setEnabled(True)
        
        profile_name = item.data(Qt.UserRole)
        
        # Get stats
        stats = self.pool_manager.get_profile_stats(profile_name)
        if stats:
            status_text = (
                f"Profile: {profile_name} | "
                f"{'Active' if stats['active'] else 'Inactive'} | "
                f"Đã dùng: {stats['usage_count']} lần"
            )
            self.status_label.setText(status_text)
            self.status_label.setStyleSheet('color: #0066cc; padding: 5px;')
    
    def add_profile_to_pool(self):
        """Add a profile to the pool"""
        # Get list of available profiles
        available_profiles = []
        if os.path.exists(self.chrome_profiles_dir):
            for item in os.listdir(self.chrome_profiles_dir):
                item_path = os.path.join(self.chrome_profiles_dir, item)
                if os.path.isdir(item_path):
                    # Check if already in pool
                    if not self.pool_manager.profile_exists(item):
                        available_profiles.append(item)
        
        if not available_profiles:
            QMessageBox.information(
                self,
                'Thông Báo',
                'Không có profile nào để thêm vào pool.\n\n'
                'Tất cả profiles hiện tại đã có trong pool, hoặc bạn cần tạo profile mới trước.'
            )
            return
        
        # Let user choose
        profile_name, ok = QInputDialog.getItem(
            self,
            'Thêm Profile vào Pool',
            'Chọn profile để thêm vào pool:',
            available_profiles,
            0,
            False
        )
        
        if not ok or not profile_name:
            return
        
        # Ask for notes
        notes, ok = QInputDialog.getText(
            self,
            'Ghi Chú',
            f'Ghi chú cho profile "{profile_name}":\n(Tùy chọn, ví dụ: Account 1, Test account, etc.)',
            text=''
        )
        
        if not ok:
            notes = ''
        
        try:
            # Add to pool
            success = self.pool_manager.add_profile(
                profile_name=profile_name,
                active=True,
                notes=notes
            )
            
            if success:
                QMessageBox.information(
                    self,
                    'Thành Công',
                    f'Đã thêm profile "{profile_name}" vào pool.\n\n'
                    f'Profile này sẽ được sử dụng trong random selection khi generate audio.'
                )
                self.refresh_pool_list()
            else:
                QMessageBox.warning(
                    self,
                    'Cảnh Báo',
                    f'Profile "{profile_name}" đã tồn tại trong pool!'
                )
            
        except Exception as e:
            error_msg = f'Lỗi khi thêm vào pool: {str(e)}'
            QMessageBox.critical(self, 'Lỗi', error_msg)
            logger.error(error_msg, exc_info=True)
    
    def remove_profile_from_pool(self):
        """Remove selected profile from pool"""
        current_item = self.pool_list.currentItem()
        if not current_item:
            return
        
        profile_name = current_item.data(Qt.UserRole)
        
        # Confirm
        reply = QMessageBox.question(
            self,
            'Xác Nhận',
            f'Xóa profile "{profile_name}" khỏi pool?\n\n'
            f'⚠️ Lưu ý: Profile folder sẽ KHÔNG bị xóa, chỉ xóa khỏi danh sách pool.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            success = self.pool_manager.remove_profile(profile_name)
            
            if success:
                QMessageBox.information(
                    self,
                    'Thành Công',
                    f'Đã xóa "{profile_name}" khỏi pool.'
                )
                self.refresh_pool_list()
                self.pool_remove_button.setEnabled(False)
                self.pool_toggle_button.setEnabled(False)
            
        except Exception as e:
            error_msg = f'Lỗi khi xóa khỏi pool: {str(e)}'
            QMessageBox.critical(self, 'Lỗi', error_msg)
            logger.error(error_msg, exc_info=True)
    
    def toggle_pool_profile_active(self):
        """Toggle active/inactive status of selected profile"""
        current_item = self.pool_list.currentItem()
        if not current_item:
            return
        
        profile_name = current_item.data(Qt.UserRole)
        
        # Get current status
        stats = self.pool_manager.get_profile_stats(profile_name)
        if not stats:
            return
        
        current_active = stats['active']
        new_active = not current_active
        
        try:
            success = self.pool_manager.set_profile_active(profile_name, new_active)
            
            if success:
                status_text = 'Active' if new_active else 'Inactive'
                self.status_label.setText(f'✅ Đã chuyển "{profile_name}" sang {status_text}')
                self.status_label.setStyleSheet('color: #28a745; padding: 5px;')
                self.refresh_pool_list()
            
        except Exception as e:
            error_msg = f'Lỗi khi toggle active: {str(e)}'
            QMessageBox.critical(self, 'Lỗi', error_msg)
            logger.error(error_msg, exc_info=True)
    
    def reset_pool_stats(self):
        """Reset usage statistics for all profiles"""
        reply = QMessageBox.question(
            self,
            'Xác Nhận Reset',
            'Reset thống kê sử dụng cho TẤT CẢ profiles trong pool?\n\n'
            'Usage count và last used time sẽ được reset về 0.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            self.pool_manager.reset_usage_stats()
            QMessageBox.information(
                self,
                'Thành Công',
                'Đã reset thống kê cho tất cả profiles trong pool.'
            )
            self.refresh_pool_list()
            
        except Exception as e:
            error_msg = f'Lỗi khi reset stats: {str(e)}'
            QMessageBox.critical(self, 'Lỗi', error_msg)
            logger.error(error_msg, exc_info=True)
    
    def test_random_selection(self):
        """Test random profile selection"""
        try:
            # Get random profile
            profile_name = self.pool_manager.get_random_profile(only_active=True)
            
            if profile_name:
                # Get stats
                stats = self.pool_manager.get_profile_stats(profile_name)
                
                msg = f'🎲 Random selection result:\n\n'
                msg += f'Profile: {profile_name}\n'
                msg += f'Usage count: {stats["usage_count"]} (đã +1)\n\n'
                msg += 'Lưu ý: Usage count đã được tăng lên vì đây là lựa chọn thực tế.'
                
                QMessageBox.information(self, 'Test Random Selection', msg)
                self.refresh_pool_list()
            else:
                QMessageBox.warning(
                    self,
                    'Cảnh Báo',
                    'Không có profile nào active trong pool để random!'
                )
            
        except Exception as e:
            error_msg = f'Lỗi khi test random: {str(e)}'
            QMessageBox.critical(self, 'Lỗi', error_msg)
            logger.error(error_msg, exc_info=True)
    
    def export_pool(self):
        """Export profile pool to JSON file"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                'Export Profile Pool',
                os.path.join(os.path.expanduser('~'), 'profile_pool_export.json'),
                'JSON Files (*.json)'
            )
            
            if not filename:
                return
            
            self.pool_manager.export_pool(filename)
            
            QMessageBox.information(
                self,
                'Thành Công',
                f'Đã export profile pool ra:\n{filename}'
            )
            
        except Exception as e:
            error_msg = f'Lỗi khi export: {str(e)}'
            QMessageBox.critical(self, 'Lỗi', error_msg)
            logger.error(error_msg, exc_info=True)
    
    def import_pool(self):
        """Import profile pool from JSON file"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                'Import Profile Pool',
                os.path.expanduser('~'),
                'JSON Files (*.json)'
            )
            
            if not filename:
                return
            
            # Ask merge or replace
            reply = QMessageBox.question(
                self,
                'Import Mode',
                'Bạn muốn:\n\n'
                '• YES: Merge với pool hiện tại (thêm profiles mới, giữ lại profiles cũ)\n'
                '• NO: Replace toàn bộ pool (xóa hết pool cũ, thay bằng pool mới)',
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Cancel:
                return
            
            merge = (reply == QMessageBox.Yes)
            
            self.pool_manager.import_pool(filename, merge=merge)
            
            mode_text = 'merged' if merge else 'replaced'
            QMessageBox.information(
                self,
                'Thành Công',
                f'Đã import profile pool ({mode_text}) từ:\n{filename}'
            )
            
            self.refresh_pool_list()
            
        except Exception as e:
            error_msg = f'Lỗi khi import: {str(e)}'
            QMessageBox.critical(self, 'Lỗi', error_msg)
            logger.error(error_msg, exc_info=True)
    
    def _create_profile_management_tab(self):
        """Create profile management tab"""
        from PyQt5.QtWidgets import QWidget
        
        tab_widget = QWidget()
        tab_layout = QVBoxLayout()
        
        # Profile list group
        list_group = QGroupBox('📋 Danh sách Profiles')
        list_layout = QVBoxLayout()
        
        self.profile_list = QListWidget()
        self.profile_list.itemClicked.connect(self.on_profile_selected)
        self.profile_list.itemDoubleClicked.connect(self.launch_selected_profile)
        list_layout.addWidget(self.profile_list)
        
        # Profile list buttons
        list_button_layout = QHBoxLayout()
        
        self.add_button = QPushButton('➕ Thêm Profile Mới')
        self.add_button.clicked.connect(self.add_profile)
        list_button_layout.addWidget(self.add_button)
        
        self.delete_button = QPushButton('🗑️ Xóa Profile')
        self.delete_button.clicked.connect(self.delete_profile)
        self.delete_button.setEnabled(False)
        list_button_layout.addWidget(self.delete_button)
        
        self.refresh_button = QPushButton('🔄 Làm Mới')
        self.refresh_button.clicked.connect(self.load_profiles)
        list_button_layout.addWidget(self.refresh_button)
        
        # Proxy manager button
        self.proxy_manager_button = QPushButton('🌐 Quản Lý Proxy')
        self.proxy_manager_button.clicked.connect(self.open_proxy_manager)
        list_button_layout.addWidget(self.proxy_manager_button)
        
        list_layout.addLayout(list_button_layout)
        list_group.setLayout(list_layout)
        tab_layout.addWidget(list_group)
        
        # Selected profile actions
        action_group = QGroupBox('⚡ Thao Tác')
        action_layout = QVBoxLayout()
        
        self.launch_button = QPushButton('🚀 Mở Chrome với Profile này')
        self.launch_button.clicked.connect(self.launch_selected_profile)
        self.launch_button.setEnabled(False)
        self.launch_button.setStyleSheet(
            'QPushButton { background-color: #28a745; color: white; '
            'padding: 10px; font-size: 14px; font-weight: bold; }'
            'QPushButton:hover { background-color: #218838; }'
            'QPushButton:disabled { background-color: #6c757d; }'
        )
        action_layout.addWidget(self.launch_button)
        
        self.set_default_button = QPushButton('⭐ Đặt làm Profile Mặc Định')
        self.set_default_button.clicked.connect(self.set_as_default)
        self.set_default_button.setEnabled(False)
        action_layout.addWidget(self.set_default_button)
        
        # Proxy configuration group
        proxy_group = QGroupBox('🌐 Cấu Hình Proxy')
        proxy_layout = QFormLayout()
        
        # Proxy selection
        self.proxy_enabled = QCheckBox("Sử dụng proxy cho profile này")
        self.proxy_enabled.setChecked(False)
        self.proxy_enabled.toggled.connect(self.on_proxy_toggle)
        proxy_layout.addRow(self.proxy_enabled)
        
        # Proxy selector (dropdown)
        self.proxy_combo = QComboBox()
        self.proxy_combo.setEnabled(False)
        proxy_layout.addRow("Chọn proxy:", self.proxy_combo)
        
        # Manual proxy input
        self.proxy_manual = QCheckBox("Nhập proxy thủ công")
        self.proxy_manual.setChecked(False)
        self.proxy_manual.toggled.connect(self.on_manual_proxy_toggle)
        proxy_layout.addRow(self.proxy_manual)
        
        # Proxy form
        self.proxy_host = QLineEdit()
        self.proxy_port = QLineEdit()
        self.proxy_username = QLineEdit()
        self.proxy_password = QLineEdit()
        self.proxy_password.setEchoMode(QLineEdit.Password)
        self.proxy_protocol = QComboBox()
        self.proxy_protocol.addItems(["http", "https", "socks4", "socks5"])
        
        # Disable all proxy inputs by default
        self.proxy_host.setEnabled(False)
        self.proxy_port.setEnabled(False)
        self.proxy_username.setEnabled(False)
        self.proxy_password.setEnabled(False)
        self.proxy_protocol.setEnabled(False)
        
        proxy_layout.addRow("Host:", self.proxy_host)
        proxy_layout.addRow("Port:", self.proxy_port)
        proxy_layout.addRow("Username:", self.proxy_username)
        proxy_layout.addRow("Password:", self.proxy_password)
        proxy_layout.addRow("Protocol:", self.proxy_protocol)
        
        # Save proxy button
        self.save_proxy_button = QPushButton("💾 Lưu Cấu Hình Proxy")
        self.save_proxy_button.clicked.connect(self.save_proxy_config)
        self.save_proxy_button.setEnabled(False)
        proxy_layout.addRow("", self.save_proxy_button)
        
        proxy_group.setLayout(proxy_layout)
        action_layout.addWidget(proxy_group)
        
        action_group.setLayout(action_layout)
        tab_layout.addWidget(action_group)
        
        # Info panel
        info_group = QGroupBox('ℹ️ Thông Tin')
        info_layout = QVBoxLayout()
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(100)
        info_message = '💡 Mẹo:\n'
        info_message += '• Double-click vào profile để mở Chrome\n'
        info_message += '• Mỗi profile có thể đăng nhập 1 tài khoản Google riêng\n'
        info_message += '• Profile mặc định sẽ được sử dụng khi không có Profile Pool\n'
        if UC_AVAILABLE:
            info_message += '• ✅ Sử dụng undetected_chromedriver (stealth mode)\n'
        else:
            info_message += '• ⚠️ undetected_chromedriver không khả dụng\n'
        self.info_text.setPlainText(info_message)
        info_layout.addWidget(self.info_text)
        
        info_group.setLayout(info_layout)
        tab_layout.addWidget(info_group)
        
        # Set layout to widget
        tab_widget.setLayout(tab_layout)
        
        return tab_widget
    
    def _create_profile_pool_tab(self):
        """Create profile pool management tab"""
        from PyQt5.QtWidgets import QWidget
        
        tab_widget = QWidget()
        tab_layout = QVBoxLayout()
        
        # Pool info
        info_group = QGroupBox('ℹ️ Profile Pool - Luân Phiên Tránh Antibot')
        info_layout = QVBoxLayout()
        
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(80)
        info_msg = (
            '🎲 Profile Pool cho phép random chọn profile mỗi lần tạo audio để tránh antibot của Google.\n'
            '• Thêm nhiều profiles vào pool (profiles phải đã đăng nhập Google AI Studio)\n'
            '• Hệ thống sẽ tự động random chọn profile khi generate audio\n'
            '• Chỉ những profile được đánh dấu "Active" mới được sử dụng'
        )
        info_text.setPlainText(info_msg)
        info_layout.addWidget(info_text)
        info_group.setLayout(info_layout)
        tab_layout.addWidget(info_group)
        
        # Pool statistics
        stats_group = QGroupBox('📊 Thống Kê Pool')
        stats_layout = QHBoxLayout()
        
        self.pool_stats_label = QLabel()
        self.pool_stats_label.setStyleSheet('font-size: 13px; padding: 10px;')
        stats_layout.addWidget(self.pool_stats_label)
        
        stats_group.setLayout(stats_layout)
        tab_layout.addWidget(stats_group)
        
        # Pool list group
        pool_list_group = QGroupBox('🎲 Danh Sách Profile Pool')
        pool_list_layout = QVBoxLayout()
        
        self.pool_list = QListWidget()
        self.pool_list.itemClicked.connect(self.on_pool_item_selected)
        pool_list_layout.addWidget(self.pool_list)
        
        # Pool buttons
        pool_button_layout1 = QHBoxLayout()
        
        self.pool_add_button = QPushButton('➕ Thêm Profile vào Pool')
        self.pool_add_button.clicked.connect(self.add_profile_to_pool)
        pool_button_layout1.addWidget(self.pool_add_button)
        
        self.pool_remove_button = QPushButton('➖ Xóa khỏi Pool')
        self.pool_remove_button.clicked.connect(self.remove_profile_from_pool)
        self.pool_remove_button.setEnabled(False)
        pool_button_layout1.addWidget(self.pool_remove_button)
        
        self.pool_refresh_button = QPushButton('🔄 Làm Mới')
        self.pool_refresh_button.clicked.connect(self.refresh_pool_list)
        pool_button_layout1.addWidget(self.pool_refresh_button)
        
        pool_list_layout.addLayout(pool_button_layout1)
        
        pool_button_layout2 = QHBoxLayout()
        
        self.pool_toggle_button = QPushButton('🔄 Active/Inactive')
        self.pool_toggle_button.clicked.connect(self.toggle_pool_profile_active)
        self.pool_toggle_button.setEnabled(False)
        pool_button_layout2.addWidget(self.pool_toggle_button)
        
        self.pool_reset_stats_button = QPushButton('🔄 Reset Stats')
        self.pool_reset_stats_button.clicked.connect(self.reset_pool_stats)
        pool_button_layout2.addWidget(self.pool_reset_stats_button)
        
        self.pool_test_random_button = QPushButton('🎲 Test Random')
        self.pool_test_random_button.clicked.connect(self.test_random_selection)
        pool_button_layout2.addWidget(self.pool_test_random_button)
        
        pool_list_layout.addLayout(pool_button_layout2)
        
        pool_list_group.setLayout(pool_list_layout)
        tab_layout.addWidget(pool_list_group)
        
        # Export/Import buttons
        import_export_layout = QHBoxLayout()
        
        export_button = QPushButton('📤 Export Pool')
        export_button.clicked.connect(self.export_pool)
        import_export_layout.addWidget(export_button)
        
        import_button = QPushButton('📥 Import Pool')
        import_button.clicked.connect(self.import_pool)
        import_export_layout.addWidget(import_button)
        
        import_export_layout.addStretch()
        tab_layout.addLayout(import_export_layout)
        
        tab_widget.setLayout(tab_layout)
        return tab_widget
        
    def load_profiles(self):
        """Load list of Chrome profiles"""
        try:
            self.status_label.setText('⏳ Đang tải danh sách profiles...')
            self.status_label.setStyleSheet('color: #0066cc; padding: 5px;')
            
            self.profile_list.clear()
            
            # Get all subdirectories in chrome_profiles
            if not os.path.exists(self.chrome_profiles_dir):
                os.makedirs(self.chrome_profiles_dir, exist_ok=True)
            
            profiles = []
            for item in os.listdir(self.chrome_profiles_dir):
                item_path = os.path.join(self.chrome_profiles_dir, item)
                if os.path.isdir(item_path):
                    profiles.append(item)
            
            profiles.sort()
            
            # Load default profile setting
            default_profile = self.get_default_profile()
            
            # Add to list
            for profile_name in profiles:
                display_text = f"📁 {profile_name}"
                if profile_name == default_profile:
                    display_text += " ⭐ (Mặc định)"
                
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, profile_name)
                self.profile_list.addItem(item)
            
            count = len(profiles)
            self.status_label.setText(f'✅ Đã tải {count} profile(s)')
            self.status_label.setStyleSheet('color: #28a745; padding: 5px;')
            
            logger.info(f"Loaded {count} Chrome profiles")
            
        except Exception as e:
            error_msg = f'❌ Lỗi khi tải profiles: {str(e)}'
            self.status_label.setText(error_msg)
            self.status_label.setStyleSheet('color: #dc3545; padding: 5px;')
            logger.error(error_msg, exc_info=True)
    
    def on_profile_selected(self, item: QListWidgetItem):
        """Handle profile selection"""
        self.launch_button.setEnabled(True)
        self.set_default_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        
        profile_name = item.data(Qt.UserRole)
        self.selected_profile = profile_name
        self.status_label.setText(f'Đã chọn profile: {profile_name}')
        self.status_label.setStyleSheet('color: #0066cc; padding: 5px;')
        
        # Load proxy configuration for this profile
        self.save_proxy_button.setEnabled(True)
        self.load_proxy_config_for_profile(profile_name)
    
    def add_profile(self):
        """Add a new Chrome profile"""
        profile_name, ok = QInputDialog.getText(
            self,
            'Thêm Profile Mới',
            'Nhập tên profile mới:\n(Chỉ dùng chữ, số, dấu gạch dưới)',
            text='profile_1'
        )
        
        if not ok or not profile_name:
            return
        
        # Validate profile name
        profile_name = profile_name.strip()
        if not profile_name:
            QMessageBox.warning(self, 'Cảnh báo', 'Tên profile không được để trống!')
            return
        
        # Check for invalid characters
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', profile_name):
            QMessageBox.warning(
                self,
                'Cảnh báo',
                'Tên profile chỉ được chứa chữ cái, số và dấu gạch dưới!'
            )
            return
        
        # Check if profile already exists
        profile_path = os.path.join(self.chrome_profiles_dir, profile_name)
        if os.path.exists(profile_path):
            QMessageBox.warning(
                self,
                'Cảnh báo',
                f'Profile "{profile_name}" đã tồn tại!'
            )
            return
        
        try:
            # Create profile directory
            os.makedirs(profile_path, exist_ok=True)
            
            logger.info(f"Created new profile: {profile_name}")
            
            QMessageBox.information(
                self,
                'Thành công',
                f'Đã tạo profile mới: {profile_name}\n\n'
                f'Bạn có thể mở Chrome với profile này để đăng nhập tài khoản Google.'
            )
            
            # Reload list
            self.load_profiles()
            
        except Exception as e:
            error_msg = f'Lỗi khi tạo profile: {str(e)}'
            QMessageBox.critical(self, 'Lỗi', error_msg)
            logger.error(error_msg, exc_info=True)
    
    def delete_profile(self):
        """Delete selected Chrome profile"""
        current_item = self.profile_list.currentItem()
        if not current_item:
            return
        
        profile_name = current_item.data(Qt.UserRole)
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            'Xác Nhận Xóa',
            f'Bạn có chắc muốn xóa profile "{profile_name}"?\n\n'
            f'⚠️ Cảnh báo: Tất cả dữ liệu đăng nhập trong profile này sẽ bị xóa!',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            profile_path = os.path.join(self.chrome_profiles_dir, profile_name)
            
            # Delete profile directory
            import shutil
            if os.path.exists(profile_path):
                shutil.rmtree(profile_path)
            
            logger.info(f"Deleted profile: {profile_name}")
            
            QMessageBox.information(
                self,
                'Thành công',
                f'Đã xóa profile: {profile_name}'
            )
            
            # Reload list
            self.load_profiles()
            
            # Disable buttons
            self.launch_button.setEnabled(False)
            self.set_default_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            
        except Exception as e:
            error_msg = f'Lỗi khi xóa profile: {str(e)}'
            QMessageBox.critical(self, 'Lỗi', error_msg)
            logger.error(error_msg, exc_info=True)
    
    def launch_selected_profile(self):
        """Launch Chrome with selected profile"""
        current_item = self.profile_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Cảnh báo', 'Vui lòng chọn một profile!')
            return
        
        profile_name = current_item.data(Qt.UserRole)
        profile_path = os.path.join(self.chrome_profiles_dir, profile_name)
        
        # Check if already launching
        if self.launcher_thread and self.launcher_thread.isRunning():
            QMessageBox.warning(
                self,
                'Cảnh báo',
                'Đang mở Chrome, vui lòng đợi...'
            )
            return
        
        # Update status
        method_name = "undetected_chromedriver" if UC_AVAILABLE else "subprocess"
        self.status_label.setText(
            f'⏳ Đang mở Chrome với profile: {profile_name} ({method_name})...'
        )
        self.status_label.setStyleSheet('color: #0066cc; padding: 5px;')
        
        # Disable launch button
        self.launch_button.setEnabled(False)
        
        # Launch Chrome in worker thread
        self.launcher_thread = ChromeProfileLauncher(
            self.chrome_binary_path,
            profile_path,
            profile_name,
            self.chromedriver_path,
            self.download_path
        )
        self.launcher_thread.finished.connect(self.on_launch_finished)
        self.launcher_thread.start()
    
    def on_launch_finished(self, success: bool, message: str):
        """Handle Chrome launch completion"""
        self.launch_button.setEnabled(True)
        
        if success:
            self.status_label.setText(f'✅ {message}')
            self.status_label.setStyleSheet('color: #28a745; padding: 5px;')
            
            QMessageBox.information(
                self,
                'Thành công',
                f'{message}\n\n'
                f'💡 Bạn có thể đăng nhập tài khoản Google trong cửa sổ Chrome vừa mở.\n'
                f'Sau khi đăng nhập, profile sẽ được lưu tự động.'
            )
        else:
            self.status_label.setText(f'❌ {message}')
            self.status_label.setStyleSheet('color: #dc3545; padding: 5px;')
            QMessageBox.critical(self, 'Lỗi', message)
    
    def set_as_default(self):
        """Set selected profile as default"""
        current_item = self.profile_list.currentItem()
        if not current_item:
            return
        
        profile_name = current_item.data(Qt.UserRole)
        
        try:
            # Save to config file
            config_file = os.path.join(self.chrome_profiles_dir, '.default_profile')
            with open(config_file, 'w') as f:
                f.write(profile_name)
            
            logger.info(f"Set default profile: {profile_name}")
            
            QMessageBox.information(
                self,
                'Thành công',
                f'Đã đặt "{profile_name}" làm profile mặc định.\n\n'
                f'Profile này sẽ được sử dụng khi tạo audio.'
            )
            
            # Reload to show default badge
            self.load_profiles()
            
        except Exception as e:
            error_msg = f'Lỗi khi đặt profile mặc định: {str(e)}'
            QMessageBox.critical(self, 'Lỗi', error_msg)
            logger.error(error_msg, exc_info=True)
    
    def get_default_profile(self) -> Optional[str]:
        """Get default profile name"""
        try:
            config_file = os.path.join(self.chrome_profiles_dir, '.default_profile')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            logger.warning(f"Failed to read default profile: {e}")
        
        return None
    
    @staticmethod
    def get_default_profile_name() -> str:
        """Get default profile name (static method for external use)"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            chrome_profiles_dir = os.path.join(current_dir, 'chrome_profiles')
            config_file = os.path.join(chrome_profiles_dir, '.default_profile')
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    profile_name = f.read().strip()
                    if profile_name:
                        return profile_name
        except Exception as e:
            logger.warning(f"Failed to read default profile: {e}")
        
        # Return fallback default
        return "desktop_app"

    def load_profile_proxy_configs(self):
        """Load profile proxy configurations from file"""
        configs = {}
        if os.path.exists(self.profile_proxy_config_path):
            try:
                with open(self.profile_proxy_config_path, 'r', encoding='utf-8') as f:
                    configs = json.load(f)
                logger.info(f"Loaded proxy configs for {len(configs)} profiles")
            except Exception as e:
                logger.error(f"Error loading proxy configs: {e}")
        return configs
    
    def save_profile_proxy_configs(self):
        """Save profile proxy configurations to file"""
        try:
            with open(self.profile_proxy_config_path, 'w', encoding='utf-8') as f:
                json.dump(self.profile_proxy_configs, f, indent=2)
            logger.info(f"Saved proxy configs for {len(self.profile_proxy_configs)} profiles")
        except Exception as e:
            logger.error(f"Error saving proxy configs: {e}")
            
    def open_proxy_manager(self):
        """Open proxy manager dialog"""
        dialog = ProxyManagerDialog(self)
        dialog.exec_()
        # Refresh proxy list after dialog closes
        self.update_proxy_list()
        
    def update_proxy_list(self):
        """Update proxy selector dropdown"""
        # Clear current items
        self.proxy_combo.clear()
        
        # Add "None" option
        self.proxy_combo.addItem("Không dùng proxy", None)
        
        # Add all proxies from proxy manager
        for i, proxy in enumerate(self.proxy_manager.proxies):
            display_text = f"{proxy.host}:{proxy.port}"
            if proxy.username:
                display_text = f"{proxy.username}@{display_text}"
            self.proxy_combo.addItem(display_text, i)
    
    def on_proxy_toggle(self, enabled):
        """Handle proxy enabled/disabled"""
        self.proxy_combo.setEnabled(enabled and not self.proxy_manual.isChecked())
        self.proxy_manual.setEnabled(enabled)
        self.save_proxy_button.setEnabled(enabled)
        
        # If proxy is enabled but manual is disabled, enable dropdown
        if enabled and not self.proxy_manual.isChecked():
            self.proxy_combo.setEnabled(True)
        
        # If proxy is disabled, disable all manual fields
        if not enabled:
            self.proxy_host.setEnabled(False)
            self.proxy_port.setEnabled(False)
            self.proxy_username.setEnabled(False)
            self.proxy_password.setEnabled(False)
            self.proxy_protocol.setEnabled(False)
            self.proxy_manual.setChecked(False)
    
    def on_manual_proxy_toggle(self, enabled):
        """Handle manual proxy input toggle"""
        self.proxy_host.setEnabled(enabled)
        self.proxy_port.setEnabled(enabled)
        self.proxy_username.setEnabled(enabled)
        self.proxy_password.setEnabled(enabled)
        self.proxy_protocol.setEnabled(enabled)
        self.proxy_combo.setEnabled(not enabled and self.proxy_enabled.isChecked())
    
    def save_proxy_config(self):
        """Save proxy configuration for current profile"""
        if not self.selected_profile:
            QMessageBox.warning(self, "Cảnh Báo", "Vui lòng chọn một profile trước!")
            return
        
        profile_name = self.selected_profile
        
        # Initialize config entry if it doesn't exist
        if profile_name not in self.profile_proxy_configs:
            self.profile_proxy_configs[profile_name] = {}
        
        # Save enabled state
        self.profile_proxy_configs[profile_name]["enabled"] = self.proxy_enabled.isChecked()
        
        # Save proxy configuration based on selection method
        if self.proxy_enabled.isChecked():
            if self.proxy_manual.isChecked():
                # Manual configuration
                self.profile_proxy_configs[profile_name]["manual"] = True
                self.profile_proxy_configs[profile_name]["config"] = {
                    "host": self.proxy_host.text().strip(),
                    "port": self.proxy_port.text().strip(),
                    "username": self.proxy_username.text().strip(),
                    "password": self.proxy_password.text().strip(),
                    "protocol": self.proxy_protocol.currentText()
                }
            else:
                # Selected proxy from list
                self.profile_proxy_configs[profile_name]["manual"] = False
                proxy_index = self.proxy_combo.currentData()
                self.profile_proxy_configs[profile_name]["proxy_index"] = proxy_index
        
        # Save configurations to file
        self.save_profile_proxy_configs()
        
        QMessageBox.information(
            self, 
            "Thành Công", 
            f"Đã lưu cấu hình proxy cho profile: {profile_name}"
        )
    
    def load_proxy_config_for_profile(self, profile_name):
        """Load proxy configuration for a profile"""
        # Reset UI first
        self.proxy_enabled.setChecked(False)
        self.proxy_manual.setChecked(False)
        self.proxy_host.setText("")
        self.proxy_port.setText("")
        self.proxy_username.setText("")
        self.proxy_password.setText("")
        self.proxy_protocol.setCurrentIndex(0)
        self.proxy_combo.setCurrentIndex(0)
        
        # Update available proxies
        self.update_proxy_list()
        
        # Check if profile has proxy config
        if profile_name in self.profile_proxy_configs:
            config = self.profile_proxy_configs[profile_name]
            
            # Set enabled state
            self.proxy_enabled.setChecked(config.get("enabled", False))
            
            if config.get("enabled", False):
                if config.get("manual", False):
                    # Manual configuration
                    self.proxy_manual.setChecked(True)
                    proxy_config = config.get("config", {})
                    self.proxy_host.setText(proxy_config.get("host", ""))
                    self.proxy_port.setText(proxy_config.get("port", ""))
                    self.proxy_username.setText(proxy_config.get("username", ""))
                    self.proxy_password.setText(proxy_config.get("password", ""))
                    
                    # Set protocol
                    protocol = proxy_config.get("protocol", "http")
                    index = self.proxy_protocol.findText(protocol)
                    if index >= 0:
                        self.proxy_protocol.setCurrentIndex(index)
                else:
                    # Selected proxy from list
                    proxy_index = config.get("proxy_index", None)
                    if proxy_index is not None:
                        index = self.proxy_combo.findData(proxy_index)
                        if index >= 0:
                            self.proxy_combo.setCurrentIndex(index)
    
    def get_proxy_for_profile(self, profile_name):
        """Get proxy configuration for a profile as ProxyData object"""
        if profile_name not in self.profile_proxy_configs:
            return None
            
        config = self.profile_proxy_configs[profile_name]
        
        if not config.get("enabled", False):
            return None
            
        if config.get("manual", False):
            # Manual configuration
            proxy_config = config.get("config", {})
            return ProxyData(
                host=proxy_config.get("host", ""),
                port=proxy_config.get("port", ""),
                username=proxy_config.get("username", ""),
                password=proxy_config.get("password", ""),
                protocol=proxy_config.get("protocol", "http")
            )
        else:
            # Selected proxy from list
            proxy_index = config.get("proxy_index", None)
            if proxy_index is not None and 0 <= proxy_index < len(self.proxy_manager.proxies):
                return self.proxy_manager.proxies[proxy_index]
        
        return None


if __name__ == '__main__':
    """Test the profile manager dialog"""
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    dialog = ProfileManagerDialog()
    dialog.exec_()
