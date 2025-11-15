"""
Proxy Manager Module
Quản lý cấu hình proxy cho ứng dụng
"""
import os
import csv
import json
from typing import List, Dict, Optional, Tuple
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QInputDialog,
    QGroupBox, QTextEdit, QTabWidget, QCheckBox, QFileDialog,
    QLineEdit, QFormLayout, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from logger_config import LoggerConfig

# Initialize logger
logger = LoggerConfig.get_logger('proxy_manager')


class ProxyData:
    """
    Class to represent a proxy configuration
    """
    def __init__(self, 
                 host: str = "", 
                 port: str = "", 
                 username: str = "", 
                 password: str = "",
                 protocol: str = "http"):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.protocol = protocol  # http, https, socks4, socks5
    
    def to_dict(self) -> Dict:
        """Convert proxy data to dictionary"""
        return {
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'protocol': self.protocol
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProxyData':
        """Create proxy data from dictionary"""
        return cls(
            host=data.get('host', ''),
            port=data.get('port', ''),
            username=data.get('username', ''),
            password=data.get('password', ''),
            protocol=data.get('protocol', 'http')
        )
    
    def get_proxy_url(self) -> str:
        """Get proxy URL in format protocol://username:password@host:port"""
        if not self.host or not self.port:
            return ""
            
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        else:
            return f"{self.protocol}://{self.host}:{self.port}"
    
    def is_valid(self) -> bool:
        """Check if proxy configuration is valid"""
        return bool(self.host and self.port)


class ProxyManager:
    """Manager class for proxy configurations"""
    
    def __init__(self, proxy_file_path: str = None):
        """Initialize proxy manager"""
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.proxy_file_path = proxy_file_path or os.path.join(self.current_dir, 'proxy_list.json')
        self.proxies: List[ProxyData] = []
        self.load_proxies()
    
    def load_proxies(self) -> None:
        """Load proxies from file"""
        if os.path.exists(self.proxy_file_path):
            try:
                with open(self.proxy_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.proxies = [ProxyData.from_dict(item) for item in data]
                logger.info(f"Loaded {len(self.proxies)} proxies from {self.proxy_file_path}")
            except Exception as e:
                logger.error(f"Error loading proxies: {e}")
                self.proxies = []
        else:
            self.proxies = []
            logger.info(f"No proxy file found at {self.proxy_file_path}")
    
    def save_proxies(self) -> None:
        """Save proxies to file"""
        try:
            with open(self.proxy_file_path, 'w', encoding='utf-8') as f:
                json.dump([proxy.to_dict() for proxy in self.proxies], f, indent=2)
            logger.info(f"Saved {len(self.proxies)} proxies to {self.proxy_file_path}")
        except Exception as e:
            logger.error(f"Error saving proxies: {e}")
    
    def add_proxy(self, proxy: ProxyData) -> None:
        """Add a new proxy"""
        self.proxies.append(proxy)
        self.save_proxies()
    
    def remove_proxy(self, index: int) -> None:
        """Remove a proxy by index"""
        if 0 <= index < len(self.proxies):
            del self.proxies[index]
            self.save_proxies()
    
    def update_proxy(self, index: int, proxy: ProxyData) -> None:
        """Update a proxy by index"""
        if 0 <= index < len(self.proxies):
            self.proxies[index] = proxy
            self.save_proxies()
    
    def import_from_csv(self, file_path: str) -> Tuple[int, int]:
        """
        Import proxies from CSV file
        Expected format: host,port,username,password,protocol
        
        Returns:
            Tuple[int, int]: (success_count, error_count)
        """
        success_count = 0
        error_count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    try:
                        if len(row) >= 2:  # At minimum we need host,port
                            host = row[0].strip()
                            port = row[1].strip()
                            username = row[2].strip() if len(row) > 2 else ""
                            password = row[3].strip() if len(row) > 3 else ""
                            protocol = row[4].strip() if len(row) > 4 else "http"
                            
                            # Validate protocol
                            if protocol not in ["http", "https", "socks4", "socks5"]:
                                protocol = "http"
                                
                            proxy = ProxyData(host, port, username, password, protocol)
                            if proxy.is_valid():
                                self.proxies.append(proxy)
                                success_count += 1
                            else:
                                error_count += 1
                        else:
                            error_count += 1
                    except Exception:
                        error_count += 1
                        
            # Save after import
            self.save_proxies()
            return success_count, error_count
        except Exception as e:
            logger.error(f"Error importing proxies from CSV: {e}")
            return 0, 0
    
    def export_to_csv(self, file_path: str) -> bool:
        """Export proxies to CSV file"""
        try:
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                for proxy in self.proxies:
                    writer.writerow([
                        proxy.host,
                        proxy.port,
                        proxy.username,
                        proxy.password,
                        proxy.protocol
                    ])
            return True
        except Exception as e:
            logger.error(f"Error exporting proxies to CSV: {e}")
            return False
    
    def get_proxy(self, index: int) -> Optional[ProxyData]:
        """Get proxy by index"""
        if 0 <= index < len(self.proxies):
            return self.proxies[index]
        return None

    def get_random_proxy(self) -> Optional[ProxyData]:
        """
        Get a random proxy from the list

        Returns:
            Optional[ProxyData]: Random proxy or None if list is empty
        """
        import random

        if not self.proxies:
            logger.warning("No proxies available for random selection")
            return None

        # Filter out invalid proxies
        valid_proxies = [p for p in self.proxies if p.is_valid()]

        if not valid_proxies:
            logger.warning("No valid proxies available")
            return None

        selected = random.choice(valid_proxies)
        logger.info(f"Randomly selected proxy: {selected.host}:{selected.port}")
        return selected

    def get_proxy_count(self) -> int:
        """Get total number of proxies"""
        return len(self.proxies)


class ProxyManagerDialog(QDialog):
    """Dialog for managing proxies"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.proxy_manager = ProxyManager()
        self.selected_index = -1
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        self.setWindowTitle('🌐 Quản Lý Proxy')
        self.setModal(True)
        self.resize(800, 500)
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel('<h2>🌐 Quản Lý Proxy</h2>')
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Description
        desc = QLabel('Quản lý danh sách proxy cho kết nối')
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        # Main content
        content = QHBoxLayout()
        
        # Left side - Proxy list
        left_group = QGroupBox("Danh Sách Proxy")
        left_layout = QVBoxLayout()
        
        # Proxy table
        self.proxy_table = QTableWidget()
        self.proxy_table.setColumnCount(5)
        self.proxy_table.setHorizontalHeaderLabels(['Host', 'Port', 'Username', 'Password', 'Protocol'])
        self.proxy_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.proxy_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.proxy_table.setSelectionMode(QTableWidget.SingleSelection)
        self.proxy_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.proxy_table.clicked.connect(self.on_proxy_selected)
        left_layout.addWidget(self.proxy_table)
        
        # Buttons for the list
        list_buttons = QHBoxLayout()
        self.btn_add = QPushButton("Thêm")
        self.btn_remove = QPushButton("Xóa")
        self.btn_import = QPushButton("Nhập CSV")
        self.btn_export = QPushButton("Xuất CSV")
        
        self.btn_add.clicked.connect(self.add_new_proxy)
        self.btn_remove.clicked.connect(self.remove_selected_proxy)
        self.btn_import.clicked.connect(self.import_from_csv)
        self.btn_export.clicked.connect(self.export_to_csv)
        
        list_buttons.addWidget(self.btn_add)
        list_buttons.addWidget(self.btn_remove)
        list_buttons.addWidget(self.btn_import)
        list_buttons.addWidget(self.btn_export)
        
        left_layout.addLayout(list_buttons)
        left_group.setLayout(left_layout)
        
        # Right side - Edit proxy
        right_group = QGroupBox("Thông Tin Proxy")
        right_layout = QFormLayout()
        
        self.txt_host = QLineEdit()
        self.txt_port = QLineEdit()
        self.txt_username = QLineEdit()
        self.txt_password = QLineEdit()
        self.cmb_protocol = QComboBox()
        
        self.cmb_protocol.addItems(["http", "https", "socks4", "socks5"])
        
        right_layout.addRow("Host:", self.txt_host)
        right_layout.addRow("Port:", self.txt_port)
        right_layout.addRow("Username:", self.txt_username)
        right_layout.addRow("Password:", self.txt_password)
        right_layout.addRow("Protocol:", self.cmb_protocol)
        
        # Save button
        self.btn_save = QPushButton("Lưu Proxy")
        self.btn_save.clicked.connect(self.save_proxy)
        right_layout.addRow("", self.btn_save)
        
        right_group.setLayout(right_layout)
        
        # Add to content
        content.addWidget(left_group, 3)
        content.addWidget(right_group, 2)
        
        layout.addLayout(content)
        
        # Bottom buttons
        buttons = QHBoxLayout()
        self.btn_close = QPushButton("Đóng")
        self.btn_close.clicked.connect(self.accept)
        buttons.addStretch()
        buttons.addWidget(self.btn_close)
        
        layout.addLayout(buttons)
        
        self.setLayout(layout)
        
        # Load data
        self.load_proxy_list()
    
    def load_proxy_list(self):
        """Load proxy list to table"""
        self.proxy_table.setRowCount(len(self.proxy_manager.proxies))
        
        for row, proxy in enumerate(self.proxy_manager.proxies):
            self.proxy_table.setItem(row, 0, QTableWidgetItem(proxy.host))
            self.proxy_table.setItem(row, 1, QTableWidgetItem(proxy.port))
            self.proxy_table.setItem(row, 2, QTableWidgetItem(proxy.username))
            self.proxy_table.setItem(row, 3, QTableWidgetItem('*' * len(proxy.password) if proxy.password else ''))
            self.proxy_table.setItem(row, 4, QTableWidgetItem(proxy.protocol))
    
    def on_proxy_selected(self):
        """Handle proxy selection"""
        selected_rows = self.proxy_table.selectionModel().selectedRows()
        if selected_rows:
            self.selected_index = selected_rows[0].row()
            proxy = self.proxy_manager.get_proxy(self.selected_index)
            if proxy:
                self.txt_host.setText(proxy.host)
                self.txt_port.setText(proxy.port)
                self.txt_username.setText(proxy.username)
                self.txt_password.setText(proxy.password)
                self.cmb_protocol.setCurrentText(proxy.protocol)
    
    def add_new_proxy(self):
        """Add a new proxy"""
        self.selected_index = -1
        self.txt_host.setText("")
        self.txt_port.setText("")
        self.txt_username.setText("")
        self.txt_password.setText("")
        self.cmb_protocol.setCurrentText("http")
    
    def save_proxy(self):
        """Save current proxy"""
        host = self.txt_host.text().strip()
        port = self.txt_port.text().strip()
        
        if not host or not port:
            QMessageBox.warning(self, "Lỗi", "Host và Port là bắt buộc!")
            return
        
        proxy = ProxyData(
            host=host,
            port=port,
            username=self.txt_username.text().strip(),
            password=self.txt_password.text().strip(),
            protocol=self.cmb_protocol.currentText()
        )
        
        if self.selected_index >= 0:
            # Update existing
            self.proxy_manager.update_proxy(self.selected_index, proxy)
        else:
            # Add new
            self.proxy_manager.add_proxy(proxy)
        
        # Reload list
        self.load_proxy_list()
        QMessageBox.information(self, "Thông báo", "Đã lưu proxy thành công!")
    
    def remove_selected_proxy(self):
        """Remove selected proxy"""
        if self.selected_index >= 0:
            reply = QMessageBox.question(
                self, 'Xác nhận', 'Bạn có chắc chắn muốn xóa proxy này?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.proxy_manager.remove_proxy(self.selected_index)
                self.load_proxy_list()
                self.selected_index = -1
                self.add_new_proxy()  # Clear form
        else:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một proxy để xóa!")
    
    def import_from_csv(self):
        """Import proxies from CSV"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file CSV", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            success, errors = self.proxy_manager.import_from_csv(file_path)
            self.load_proxy_list()
            QMessageBox.information(
                self, "Kết quả nhập", 
                f"Đã nhập thành công {success} proxy\n"
                f"Có {errors} lỗi trong quá trình nhập"
            )
    
    def export_to_csv(self):
        """Export proxies to CSV"""
        if not self.proxy_manager.proxies:
            QMessageBox.warning(self, "Lỗi", "Không có proxy nào để xuất!")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Lưu file CSV", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            if self.proxy_manager.export_to_csv(file_path):
                QMessageBox.information(
                    self, "Thông báo", "Đã xuất proxies thành công!"
                )
            else:
                QMessageBox.warning(
                    self, "Lỗi", "Có lỗi xảy ra khi xuất file!"
                )