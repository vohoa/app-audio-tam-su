"""
Settings Manager Module
Quản lý cấu hình ứng dụng (GEMINI_API_KEY, download_path, etc.)
"""
import os
from typing import Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QGroupBox, QFileDialog, QMessageBox, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from logger_config import LoggerConfig

# Initialize logger
logger = LoggerConfig.get_logger('settings_manager')


class SettingsManagerDialog(QDialog):
    """Dialog for managing application settings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Paths
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.env_file_path = os.path.join(self.current_dir, '.env')
        
        # Settings
        self.settings = self.load_settings()
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        self.setWindowTitle('⚙️ Quản Lý Cài Đặt')
        self.setModal(True)
        self.resize(700, 400)
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel('<h2>⚙️ Cài Đặt Ứng Dụng</h2>')
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Description
        desc = QLabel(
            'Cấu hình các thông số quan trọng của ứng dụng'
        )
        desc.setStyleSheet('color: #666; padding: 5px;')
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        # ============================================
        # GEMINI API KEY Section
        # ============================================
        api_group = QGroupBox('🔑 Gemini API Key')
        api_layout = QVBoxLayout()
        
        api_desc = QLabel(
            'API Key để sử dụng Google Gemini AI Studio.\n'
            'Lấy tại: https://aistudio.google.com/app/apikey'
        )
        api_desc.setStyleSheet('color: #666; font-size: 11px;')
        api_desc.setWordWrap(True)
        api_layout.addWidget(api_desc)
        
        # API Key input
        api_input_layout = QHBoxLayout()
        
        api_label = QLabel('API Key:')
        api_label.setMinimumWidth(100)
        api_input_layout.addWidget(api_label)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText('Nhập Gemini API Key của bạn...')
        self.api_key_input.setText(self.settings.get('GEMINI_API_KEY', ''))
        self.api_key_input.setEchoMode(QLineEdit.Password)  # Hide API key
        api_input_layout.addWidget(self.api_key_input)
        
        # Show/Hide button
        self.show_api_key_button = QPushButton('👁️ Hiện')
        self.show_api_key_button.setMaximumWidth(80)
        self.show_api_key_button.clicked.connect(self.toggle_api_key_visibility)
        api_input_layout.addWidget(self.show_api_key_button)
        
        api_layout.addLayout(api_input_layout)
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # ============================================
        # Download Path Section
        # ============================================
        download_group = QGroupBox('📁 Đường Dẫn Lưu Audio')
        download_layout = QVBoxLayout()
        
        download_desc = QLabel(
            'Thư mục để lưu các file audio đã tải xuống'
        )
        download_desc.setStyleSheet('color: #666; font-size: 11px;')
        download_layout.addWidget(download_desc)
        
        # Download path input
        path_input_layout = QHBoxLayout()
        
        path_label = QLabel('Đường dẫn:')
        path_label.setMinimumWidth(100)
        path_input_layout.addWidget(path_label)
        
        self.download_path_input = QLineEdit()
        self.download_path_input.setPlaceholderText('Chọn thư mục lưu audio...')
        current_path = self.settings.get('AUDIO_DOWNLOAD_PATH', '')
        if not current_path:
            current_path = os.path.join(self.current_dir, 'audio_downloads')
        self.download_path_input.setText(current_path)
        self.download_path_input.setReadOnly(True)
        path_input_layout.addWidget(self.download_path_input)
        
        # Browse button
        browse_button = QPushButton('📂 Chọn')
        browse_button.setMaximumWidth(80)
        browse_button.clicked.connect(self.browse_download_path)
        path_input_layout.addWidget(browse_button)
        
        download_layout.addLayout(path_input_layout)
        download_group.setLayout(download_layout)
        layout.addWidget(download_group)
        
        # ============================================
        # Chrome Configuration Section
        # ============================================
        chrome_group = QGroupBox('🌐 Cấu Hình Chrome')
        chrome_layout = QVBoxLayout()
        
        chrome_desc = QLabel(
            'Cấu hình đường dẫn Chrome binary và ChromeDriver.\n'
            'Để trống để tự động phát hiện (khuyến nghị).'
        )
        chrome_desc.setStyleSheet('color: #666; font-size: 11px;')
        chrome_desc.setWordWrap(True)
        chrome_layout.addWidget(chrome_desc)
        
        # Chrome Binary Path
        chrome_binary_layout = QHBoxLayout()
        
        chrome_binary_label = QLabel('Chrome Binary:')
        chrome_binary_label.setMinimumWidth(100)
        chrome_binary_layout.addWidget(chrome_binary_label)
        
        self.chrome_binary_input = QLineEdit()
        self.chrome_binary_input.setPlaceholderText('Auto-detect (để trống hoặc nhập đường dẫn)')
        current_chrome_binary = self.settings.get('CHROME_BINARY_PATH', '')
        self.chrome_binary_input.setText(current_chrome_binary)
        chrome_binary_layout.addWidget(self.chrome_binary_input)
        
        # Browse button for Chrome binary
        browse_chrome_button = QPushButton('📂 Chọn')
        browse_chrome_button.setMaximumWidth(80)
        browse_chrome_button.clicked.connect(self.browse_chrome_binary)
        chrome_binary_layout.addWidget(browse_chrome_button)
        
        # Detect button
        detect_chrome_button = QPushButton('🔍 Tự động')
        detect_chrome_button.setMaximumWidth(80)
        detect_chrome_button.clicked.connect(self.detect_chrome_binary)
        chrome_binary_layout.addWidget(detect_chrome_button)
        
        chrome_layout.addLayout(chrome_binary_layout)
        
        # ChromeDriver Path
        chromedriver_layout = QHBoxLayout()
        
        chromedriver_label = QLabel('ChromeDriver:')
        chromedriver_label.setMinimumWidth(100)
        chromedriver_layout.addWidget(chromedriver_label)
        
        self.chromedriver_input = QLineEdit()
        self.chromedriver_input.setPlaceholderText('Auto-manage (để trống để tự động quản lý)')
        current_chromedriver = self.settings.get('CHROME_DRIVER_PATH', '')
        self.chromedriver_input.setText(current_chromedriver)
        chromedriver_layout.addWidget(self.chromedriver_input)
        
        # Browse button for ChromeDriver
        browse_driver_button = QPushButton('📂 Chọn')
        browse_driver_button.setMaximumWidth(80)
        browse_driver_button.clicked.connect(self.browse_chromedriver)
        chromedriver_layout.addWidget(browse_driver_button)
        
        # Detect button
        detect_driver_button = QPushButton('🔍 Tự động')
        detect_driver_button.setMaximumWidth(80)
        detect_driver_button.clicked.connect(self.detect_chromedriver)
        chromedriver_layout.addWidget(detect_driver_button)
        
        chrome_layout.addLayout(chromedriver_layout)
        
        # Chrome info display
        chrome_info = QLabel()
        chrome_info.setStyleSheet(
            'background-color: #f8f9fa; '
            'padding: 8px; '
            'border-left: 3px solid #007bff; '
            'border-radius: 3px; '
            'font-size: 11px;'
        )
        chrome_info.setWordWrap(True)
        self.chrome_info_label = chrome_info
        self.update_chrome_info()
        chrome_layout.addWidget(chrome_info)
        
        # Info about Chrome configuration
        chrome_help = QLabel(
            '<b>💡 Lưu ý:</b><br>'
            '• <b>Để trống</b>: Tự động phát hiện Chrome và quản lý ChromeDriver (khuyến nghị)<br>'
            '• <b>Chrome Binary</b>: Đường dẫn tới chrome/chromium executable<br>'
            '• <b>ChromeDriver</b>: Để trống để undetected_chromedriver tự quản lý<br>'
            '• <b>Version matching</b>: ChromeDriver phải khớp với Chrome version<br><br>'
            '<b>🔧 Priority:</b><br>'
            '1. Config từ .env (nếu có)<br>'
            '2. Chrome-for-Testing trong project<br>'
            '3. System Chrome (/usr/bin/google-chrome)<br>'
            '4. Auto-managed ChromeDriver'
        )
        chrome_help.setStyleSheet('color: #666; font-size: 10px;')
        chrome_help.setWordWrap(True)
        chrome_layout.addWidget(chrome_help)
        
        chrome_group.setLayout(chrome_layout)
        layout.addWidget(chrome_group)
        
        # ============================================
        # Conversation JSON Generation Section
        # ============================================
        json_group = QGroupBox('💬 Tạo JSON Hội Thoại Bằng AI')
        json_layout = QVBoxLayout()
        
        json_desc = QLabel(
            'Nhập URL trang AI (Grok, ChatGPT, etc.) để tự động lấy JSON hội thoại.\n'
            'Selenium sẽ truy cập trang này, lấy JSON được AI tạo ra và lưu về máy.'
        )
        json_desc.setStyleSheet('color: #666; font-size: 11px;')
        json_desc.setWordWrap(True)
        json_layout.addWidget(json_desc)
        
        # URL input for JSON generation
        url_input_layout = QHBoxLayout()
        
        url_label = QLabel('URL trang AI:')
        url_label.setMinimumWidth(100)
        url_input_layout.addWidget(url_label)
        
        self.conversation_json_url_input = QLineEdit()
        self.conversation_json_url_input.setPlaceholderText('https://grok.com/project/xxx?tab=conversations')
        current_url = self.settings.get('CONVERSATION_JSON_URL', '')
        self.conversation_json_url_input.setText(current_url)
        url_input_layout.addWidget(self.conversation_json_url_input)
        
        json_layout.addLayout(url_input_layout)
        
        # Info about supported platforms
        json_info = QLabel(
            '<b>💡 Hỗ trợ:</b><br>'
            '• <b>Grok</b>: https://grok.com/project/[project-id]?tab=conversations<br>'
            '• <b>ChatGPT</b>: https://chat.openai.com/c/[conversation-id]<br>'
            '• <b>Claude</b>: https://claude.ai/chat/[chat-id]<br><br>'
            '<b>🔧 Cách sử dụng:</b><br>'
            '1. Mở trang AI và tạo hội thoại về truyện<br>'
            '2. Copy URL của trang đó<br>'
            '3. Dán vào ô trên và lưu cài đặt<br>'
            '4. Selenium sẽ tự động lấy JSON khi xử lý'
        )
        json_info.setStyleSheet(
            'background-color: #f8f9fa; '
            'padding: 8px; '
            'border-left: 3px solid #28a745; '
            'border-radius: 3px; '
            'font-size: 11px;'
        )
        json_info.setWordWrap(True)
        json_layout.addWidget(json_info)
        
        json_group.setLayout(json_layout)
        layout.addWidget(json_group)
        
        # ============================================
        # Buttons
        # ============================================
        layout.addStretch()
        
        button_layout = QHBoxLayout()
        
        # Save button
        save_button = QPushButton('💾 Lưu Cài Đặt')
        save_button.clicked.connect(self.save_settings)
        save_button.setStyleSheet('''
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        ''')
        button_layout.addWidget(save_button)
        
        # Cancel button
        cancel_button = QPushButton('❌ Hủy')
        cancel_button.clicked.connect(self.close)
        cancel_button.setStyleSheet('''
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        ''')
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_settings(self) -> dict:
        """Load settings from .env file"""
        settings = {}
        
        try:
            if os.path.exists(self.env_file_path):
                with open(self.env_file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            settings[key.strip()] = value.strip()
                
                logger.info(f"✅ Loaded settings from {self.env_file_path}")
            else:
                logger.warning(f"⚠️ .env file not found: {self.env_file_path}")
        except Exception as e:
            logger.error(f"❌ Failed to load settings: {e}", exc_info=True)
        
        return settings
    
    def save_settings(self):
        """Save settings to .env file"""
        try:
            # Get values from inputs
            new_api_key = self.api_key_input.text().strip()
            new_download_path = self.download_path_input.text().strip()
            new_conversation_url = self.conversation_json_url_input.text().strip()
            new_chrome_binary = self.chrome_binary_input.text().strip()
            new_chromedriver = self.chromedriver_input.text().strip()
            
            # Validate
            if not new_api_key:
                QMessageBox.warning(
                    self,
                    'Cảnh báo',
                    'Vui lòng nhập Gemini API Key!'
                )
                return
            
            if not new_download_path:
                QMessageBox.warning(
                    self,
                    'Cảnh báo',
                    'Vui lòng chọn đường dẫn lưu audio!'
                )
                return
            
            # Validate Chrome binary if provided
            if new_chrome_binary and not os.path.exists(new_chrome_binary):
                reply = QMessageBox.question(
                    self,
                    'Cảnh báo',
                    f'Chrome binary không tồn tại:\n{new_chrome_binary}\n\n'
                    'Bạn có muốn tiếp tục lưu (sẽ dùng auto-detect)?',
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
                new_chrome_binary = ''  # Clear invalid path
            
            # Validate ChromeDriver if provided
            if new_chromedriver and not os.path.exists(new_chromedriver):
                reply = QMessageBox.question(
                    self,
                    'Cảnh báo',
                    f'ChromeDriver không tồn tại:\n{new_chromedriver}\n\n'
                    'Bạn có muốn tiếp tục lưu (sẽ dùng auto-manage)?',
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
                new_chromedriver = ''  # Clear invalid path
            
            # Create download path if not exists
            if not os.path.exists(new_download_path):
                try:
                    os.makedirs(new_download_path, exist_ok=True)
                    logger.info(f"✅ Created download directory: {new_download_path}")
                except Exception as mkdir_error:
                    QMessageBox.critical(
                        self,
                        'Lỗi',
                        f'Không thể tạo thư mục: {mkdir_error}'
                    )
                    return
            
            # Update settings dict
            self.settings['GEMINI_API_KEY'] = new_api_key
            self.settings['AUDIO_DOWNLOAD_PATH'] = new_download_path
            self.settings['CONVERSATION_JSON_URL'] = new_conversation_url
            self.settings['CHROME_BINARY_PATH'] = new_chrome_binary
            self.settings['CHROME_DRIVER_PATH'] = new_chromedriver
            
            # Read existing .env file to preserve comments and structure
            env_lines = []
            if os.path.exists(self.env_file_path):
                with open(self.env_file_path, 'r', encoding='utf-8') as f:
                    env_lines = f.readlines()
            
            # Update or add settings
            updated_keys = set()
            new_lines = []
            
            for line in env_lines:
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and '=' in stripped:
                    key = stripped.split('=', 1)[0].strip()
                    if key in self.settings:
                        new_lines.append(f"{key}={self.settings[key]}\n")
                        updated_keys.add(key)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            
            # Add new keys that weren't in the file
            for key, value in self.settings.items():
                if key not in updated_keys:
                    new_lines.append(f"{key}={value}\n")
            
            # Write back to .env file
            with open(self.env_file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            logger.info(f"✅ Settings saved to {self.env_file_path}")
            
            QMessageBox.information(
                self,
                'Thành công',
                'Đã lưu cài đặt thành công!\n\n'
                'Lưu ý: Một số thay đổi có thể cần khởi động lại ứng dụng để có hiệu lực.'
            )
            
            self.accept()  # Close dialog with success status
            
        except Exception as e:
            error_msg = f'Lỗi khi lưu cài đặt: {str(e)}'
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, 'Lỗi', error_msg)
    
    def browse_download_path(self):
        """Open file dialog to select download directory"""
        current_path = self.download_path_input.text() or self.current_dir
        
        directory = QFileDialog.getExistingDirectory(
            self,
            'Chọn thư mục lưu audio',
            current_path,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if directory:
            self.download_path_input.setText(directory)
            logger.info(f"Selected download path: {directory}")
    
    def toggle_api_key_visibility(self):
        """Toggle API key visibility"""
        if self.api_key_input.echoMode() == QLineEdit.Password:
            self.api_key_input.setEchoMode(QLineEdit.Normal)
            self.show_api_key_button.setText('🙈 Ẩn')
        else:
            self.api_key_input.setEchoMode(QLineEdit.Password)
            self.show_api_key_button.setText('👁️ Hiện')
    
    def browse_chrome_binary(self):
        """Open file dialog to select Chrome binary"""
        current_path = self.chrome_binary_input.text() or '/usr/bin'
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Chọn Chrome Binary',
            current_path,
            'Executables (chrome chromium google-chrome*);;All Files (*)'
        )
        
        if file_path:
            self.chrome_binary_input.setText(file_path)
            self.update_chrome_info()
            logger.info(f"Selected Chrome binary: {file_path}")
    
    def browse_chromedriver(self):
        """Open file dialog to select ChromeDriver"""
        current_path = self.chromedriver_input.text() or self.current_dir
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Chọn ChromeDriver',
            current_path,
            'Executables (chromedriver*);;All Files (*)'
        )
        
        if file_path:
            self.chromedriver_input.setText(file_path)
            self.update_chrome_info()
            logger.info(f"Selected ChromeDriver: {file_path}")
    
    def detect_chrome_binary(self):
        """Auto-detect Chrome binary"""
        import config
        
        # Try to detect Chrome
        detected_path = config.get_chrome_binary_path()
        
        if detected_path:
            self.chrome_binary_input.setText(detected_path)
            self.update_chrome_info()
            QMessageBox.information(
                self,
                'Thành công',
                f'Đã tự động phát hiện Chrome:\n{detected_path}'
            )
            logger.info(f"Auto-detected Chrome: {detected_path}")
        else:
            QMessageBox.warning(
                self,
                'Không tìm thấy',
                'Không thể tự động phát hiện Chrome.\n'
                'Vui lòng chọn thủ công bằng nút "Chọn".'
            )
    
    def detect_chromedriver(self):
        """Auto-detect ChromeDriver"""
        import config
        
        # Try to detect ChromeDriver
        detected_path = config.get_chrome_driver_path()
        
        if detected_path:
            self.chromedriver_input.setText(detected_path)
            self.update_chrome_info()
            QMessageBox.information(
                self,
                'Thành công',
                f'Đã tự động phát hiện ChromeDriver:\n{detected_path}'
            )
            logger.info(f"Auto-detected ChromeDriver: {detected_path}")
        else:
            QMessageBox.information(
                self,
                'Auto-manage',
                'ChromeDriver sẽ được tự động quản lý bởi undetected_chromedriver.\n'
                'Để trống để sử dụng chế độ auto-manage (khuyến nghị).'
            )
    
    def update_chrome_info(self):
        """Update Chrome version info display"""
        import config
        
        chrome_path = self.chrome_binary_input.text().strip()
        if not chrome_path:
            chrome_path = config.get_chrome_binary_path()
        
        driver_path = self.chromedriver_input.text().strip()
        if not driver_path:
            driver_path = config.get_chrome_driver_path()
        
        # Get Chrome version
        chrome_version = "Not detected"
        if chrome_path and os.path.exists(chrome_path):
            chrome_version = config.get_chrome_version(chrome_path)
        
        # Get ChromeDriver version
        driver_version = "Auto-managed"
        if driver_path and os.path.exists(driver_path):
            try:
                import subprocess
                result = subprocess.run(
                    [driver_path, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                # Output: "ChromeDriver 140.0.7339.207 (xxxxx)"
                version_output = result.stdout.strip()
                parts = version_output.split()
                if len(parts) >= 2:
                    driver_version = parts[1]
            except:
                driver_version = "Unknown"
        
        # Display info
        info_text = (
            f'<b>📊 Thông tin hiện tại:</b><br>'
            f'• Chrome: {chrome_version}<br>'
            f'• ChromeDriver: {driver_version}<br><br>'
        )
        
        # Check version matching
        if chrome_version != "Not detected" and driver_version not in ["Auto-managed", "Unknown"]:
            chrome_major = chrome_version.split('.')[0] if '.' in chrome_version else chrome_version
            driver_major = driver_version.split('.')[0] if '.' in driver_version else driver_version
            
            if chrome_major == driver_major:
                info_text += '<b style="color: green;">✅ Versions match!</b>'
            else:
                info_text += (
                    f'<b style="color: red;">⚠️ Version mismatch!</b><br>'
                    f'Chrome major: {chrome_major}, Driver major: {driver_major}<br>'
                    f'Khuyến nghị để trống để auto-manage.'
                )
        elif driver_version == "Auto-managed":
            info_text += '<b style="color: blue;">💡 ChromeDriver sẽ tự động khớp với Chrome</b>'
        
        self.chrome_info_label.setText(info_text)
