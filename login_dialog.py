"""
Login Dialog for Audio Generator Desktop App
Handles user authentication with Django REST API
"""
import os
import json
from typing import Optional, Dict
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QIcon

from logger_config import LoggerConfig

logger = LoggerConfig.get_logger('login')


class LoginWorker(QThread):
    """Worker thread for async login"""
    finished = pyqtSignal(bool, str, dict)  # success, message, user_data
    
    def __init__(self, api_service, username: str, password: str):
        super().__init__()
        self.api_service = api_service
        self.username = username
        self.password = password
    
    def run(self):
        """Perform login request"""
        try:
            result = self.api_service.login(self.username, self.password)
            
            if result.get('token') or result.get('access'):
                self.finished.emit(True, 'Đăng nhập thành công!', result)
            else:
                logger.warning(f"Login response missing token: {result}")
                self.finished.emit(False, 'Phản hồi không hợp lệ từ server', {})
                
        except Exception as e:
            logger.error(f"Login failed for user {self.username}: {str(e)}", exc_info=True)
            self.finished.emit(False, f'Đăng nhập thất bại: {str(e)}', {})


class LoginDialog(QDialog):
    """Login dialog for authentication"""
    
    # Signals
    login_successful = pyqtSignal(dict)  # Emit user data on success
    
    def __init__(self, api_service, parent=None):
        super().__init__(parent)
        self.api_service = api_service
        self.worker = None
        self.credentials_file = os.path.join(
            os.path.dirname(__file__), 
            '.credentials'
        )
        
        self.init_ui()
        self.load_saved_credentials()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle('🔐 Đăng Nhập - Audio Generator')
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel('🎵 Audio Generator Desktop')
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel('Vui lòng đăng nhập để tiếp tục')
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet('color: #666;')
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # Username field
        username_label = QLabel('Tên đăng nhập:')
        layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Nhập tên đăng nhập')
        self.username_input.setMinimumHeight(28)
        self.username_input.returnPressed.connect(self.on_login_clicked)
        layout.addWidget(self.username_input)
        
        # Password field
        password_label = QLabel('Mật khẩu:')
        layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Nhập mật khẩu')
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(28)
        self.password_input.returnPressed.connect(self.on_login_clicked)
        layout.addWidget(self.password_input)
        
        # Remember me checkbox
        self.remember_checkbox = QCheckBox('Ghi nhớ đăng nhập')
        self.remember_checkbox.setChecked(True)
        layout.addWidget(self.remember_checkbox)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        layout.addSpacing(10)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton('Hủy')
        self.cancel_button.setMinimumHeight(40)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.login_button = QPushButton('🔓 Đăng Nhập')
        self.login_button.setMinimumHeight(40)
        self.login_button.setDefault(True)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.login_button.clicked.connect(self.on_login_clicked)
        button_layout.addWidget(self.login_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Focus on username field
        self.username_input.setFocus()
    
    def load_saved_credentials(self):
        """Load saved credentials if remember me was checked"""
        try:
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file, 'r') as f:
                    data = json.load(f)
                    self.username_input.setText(data.get('username', ''))
                    self.password_input.setText(data.get('password', ''))
                    self.remember_checkbox.setChecked(True)
        except Exception as e:
            logger.warning(f"Failed to load saved credentials: {e}")
    
    def save_credentials(self):
        """Save credentials if remember me is checked"""
        try:
            if self.remember_checkbox.isChecked():
                data = {
                    'username': self.username_input.text(),
                    'password': self.password_input.text()
                }
                with open(self.credentials_file, 'w') as f:
                    json.dump(data, f)
                # Set file permissions to user-only
                os.chmod(self.credentials_file, 0o600)
            else:
                # Delete saved credentials if unchecked
                if os.path.exists(self.credentials_file):
                    os.remove(self.credentials_file)
        except Exception as e:
            logger.warning(f"Failed to save credentials: {e}")
    
    def on_login_clicked(self):
        """Handle login button click"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        # Validation
        if not username:
            logger.warning("Login attempt with empty username")
            QMessageBox.warning(self, 'Lỗi', 'Vui lòng nhập tên đăng nhập')
            self.username_input.setFocus()
            return
        
        if not password:
            logger.warning("Login attempt with empty password")
            QMessageBox.warning(self, 'Lỗi', 'Vui lòng nhập mật khẩu')
            self.password_input.setFocus()
            return
        
        
        # Disable inputs during login
        self.set_inputs_enabled(False)
        self.progress_bar.show()
        
        # Start login worker
        self.worker = LoginWorker(self.api_service, username, password)
        self.worker.finished.connect(self.on_login_finished)
        self.worker.start()
    
    def on_login_finished(self, success: bool, message: str, user_data: Dict):
        """Handle login completion"""
        self.progress_bar.hide()
        self.set_inputs_enabled(True)
        
        if success:
            # Save credentials if remember me is checked
            self.save_credentials()
            
            # Emit success signal
            self.login_successful.emit(user_data)
            
            # Close dialog
            self.accept()
        else:
            logger.error(f"Login failed: {message}")
            QMessageBox.critical(
                self, 
                'Đăng Nhập Thất Bại', 
                f'{message}\n\nVui lòng kiểm tra lại thông tin đăng nhập.'
            )
            self.password_input.clear()
            self.password_input.setFocus()
    
    def set_inputs_enabled(self, enabled: bool):
        """Enable or disable input fields"""
        self.username_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
        self.remember_checkbox.setEnabled(enabled)
        self.login_button.setEnabled(enabled)
        self.cancel_button.setEnabled(enabled)
    
    def closeEvent(self, event):
        """Handle dialog close"""
        if self.worker and self.worker.isRunning():
            logger.warning("Closing login dialog while login in progress")
            self.worker.terminate()
        super().closeEvent(event)
