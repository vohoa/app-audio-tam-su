"""
Channel Intro Manager
Quản lý danh sách lời giới thiệu kênh cho audio
"""
import json
import os
from typing import List, Dict, Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QTextEdit, QLineEdit, QMessageBox, QListWidgetItem
)
from PyQt5.QtCore import Qt


class ChannelIntroManager:
    """Manager class for channel introductions"""

    def __init__(self, config_file: str = "channel_intros.json"):
        """
        Initialize Channel Intro Manager

        Args:
            config_file: Path to JSON config file storing channel intros
        """
        self.config_file = config_file
        self.intros = self._load_intros()

    def _get_default_intros(self) -> List[Dict[str, str]]:
        """Get default channel introductions"""
        return [
            {
            "name": "Đơn Giản",
            "content": "Xin chào các bé! Hôm nay cô sẽ kể cho các bé nghe câu chuyện {story_name}, chương: {chapter_title}\n\n"
            },
            {
            "name": "Vui Vẻ",
            "content": "Chào các bạn nhỏ! Các bạn đã sẵn sàng chưa? Hôm nay chúng ta cùng nghe tiếp truyện {story_name}, chương: {chapter_title}\n\n"
            },
            {
            "name": "Ấm Áp",
            "content": "Con yêu ơi, đến giờ nghe chuyện rồi! Mẹ sẽ kể cho con nghe tiếp câu chuyện {story_name}, chương hôm nay là: {chapter_title}\n\n"
            },
            {
            "name": "Sinh Động",
            "content": "Ê các bạn ơi! Tụi mình lại tiếp tục với truyện {story_name} nào, hôm nay là chương: {chapter_title}\n\n"
            },
            {
            "name": "Nhẹ Nhàng",
            "content": "Các em thân mến, cô xin mời các em lắng nghe tiếp truyện {story_name}, chương: {chapter_title}\n\n"
            },
            {
            "name": "Chỉ Tên Truyện",
            "content": "Xin chào các bé! Hôm nay cô sẽ kể cho các bé nghe câu chuyện: {story_name}\n\n"
            },
            {
            "name": "Chỉ Tên Chương",
            "content": "Xin chào các bé! Hôm nay cô sẽ kể cho các bé nghe: {chapter_title}\n\n"
            }
        ]

    def _load_intros(self) -> List[Dict[str, str]]:
        """Load channel intros from config file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('intros', self._get_default_intros())
            except Exception as e:
                print(f"Error loading channel intros: {e}")
                return self._get_default_intros()
        else:
            # Create default config
            default_intros = self._get_default_intros()
            self._save_intros(default_intros)
            return default_intros

    def _save_intros(self, intros: List[Dict[str, str]]):
        """Save channel intros to config file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump({'intros': intros}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving channel intros: {e}")

    def get_all_intros(self) -> List[Dict[str, str]]:
        """Get all channel intros"""
        return self.intros

    def get_intro_names(self) -> List[str]:
        """Get list of intro names"""
        return [intro['name'] for intro in self.intros]

    def get_intro_by_name(self, name: str) -> Optional[str]:
        """
        Get intro content by name

        Args:
            name: Name of the intro

        Returns:
            Intro content string or None if not found
        """
        for intro in self.intros:
            if intro['name'] == name:
                return intro['content']
        return None

    def add_intro(self, name: str, content: str) -> bool:
        """
        Add new channel intro

        Args:
            name: Name of the intro
            content: Content of the intro

        Returns:
            True if successful, False if name already exists
        """
        # Check if name already exists
        if any(intro['name'] == name for intro in self.intros):
            return False

        self.intros.append({'name': name, 'content': content})
        self._save_intros(self.intros)
        return True

    def update_intro(self, old_name: str, new_name: str, content: str) -> bool:
        """
        Update existing channel intro

        Args:
            old_name: Current name of the intro
            new_name: New name for the intro
            content: New content

        Returns:
            True if successful, False otherwise
        """
        # Check if new name conflicts with another intro
        if old_name != new_name:
            if any(intro['name'] == new_name for intro in self.intros):
                return False

        for intro in self.intros:
            if intro['name'] == old_name:
                intro['name'] = new_name
                intro['content'] = content
                self._save_intros(self.intros)
                return True
        return False

    def delete_intro(self, name: str) -> bool:
        """
        Delete channel intro

        Args:
            name: Name of the intro to delete

        Returns:
            True if successful, False if not found
        """
        for i, intro in enumerate(self.intros):
            if intro['name'] == name:
                self.intros.pop(i)
                self._save_intros(self.intros)
                return True
        return False


class ChannelIntroDialog(QDialog):
    """Dialog for managing channel introductions"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = ChannelIntroManager()
        self.setup_ui()
        self.load_intros()

    def setup_ui(self):
        """Setup dialog UI"""
        self.setWindowTitle('Quản Lý Channel Intro')
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout()

        # Title
        title = QLabel('Quản Lý Lời Giới Thiệu Kênh')
        title.setStyleSheet('font-size: 16px; font-weight: bold; margin-bottom: 10px;')
        layout.addWidget(title)

        # Main content area
        content_layout = QHBoxLayout()

        # Left side - List of intros
        left_layout = QVBoxLayout()
        left_label = QLabel('Danh sách Intro:')
        left_layout.addWidget(left_label)

        self.intro_list = QListWidget()
        self.intro_list.currentItemChanged.connect(self.on_intro_selected)
        left_layout.addWidget(self.intro_list)

        # Buttons for list
        list_buttons = QHBoxLayout()
        self.add_button = QPushButton('➕ Thêm Mới')
        self.add_button.clicked.connect(self.add_intro)
        self.delete_button = QPushButton('🗑️ Xóa')
        self.delete_button.clicked.connect(self.delete_intro)
        list_buttons.addWidget(self.add_button)
        list_buttons.addWidget(self.delete_button)
        left_layout.addLayout(list_buttons)

        content_layout.addLayout(left_layout, 1)

        # Right side - Edit area
        right_layout = QVBoxLayout()

        # Name field
        name_label = QLabel('Tên Intro:')
        right_layout.addWidget(name_label)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText('Ví dụ: Đêm Khuya Sâu Lắng')
        right_layout.addWidget(self.name_input)

        # Content field
        content_label = QLabel('Nội dung Intro:')
        hint_label = QLabel('💡 Sử dụng {story_name} để chèn tên truyện, {chapter_title} để chèn tiêu đề chương')
        hint_label.setStyleSheet('color: #666; font-size: 11px; font-style: italic;')
        right_layout.addWidget(content_label)
        right_layout.addWidget(hint_label)

        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText(
            'Nhập nội dung lời giới thiệu...\n\n'
            'Tip: Sử dụng {story_name} để tự động thêm tên truyện\n'
            '     Sử dụng {chapter_title} để tự động thêm tiêu đề chương'
        )
        right_layout.addWidget(self.content_input)

        # Save button
        self.save_button = QPushButton('💾 Lưu Thay Đổi')
        self.save_button.clicked.connect(self.save_intro)
        self.save_button.setStyleSheet('background-color: #28a745; color: white; padding: 8px;')
        right_layout.addWidget(self.save_button)

        content_layout.addLayout(right_layout, 2)

        layout.addLayout(content_layout)

        # Close button
        close_button = QPushButton('Đóng')
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def load_intros(self):
        """Load intros into list widget"""
        self.intro_list.clear()
        for intro in self.manager.get_all_intros():
            self.intro_list.addItem(intro['name'])

    def on_intro_selected(self, current, previous):
        """Handle intro selection"""
        if current is None:
            return

        intro_name = current.text()
        intro_content = self.manager.get_intro_by_name(intro_name)

        if intro_content is not None:
            self.name_input.setText(intro_name)
            self.content_input.setText(intro_content)

    def add_intro(self):
        """Add new intro"""
        # Clear inputs for new intro
        self.name_input.clear()
        self.content_input.clear()
        self.name_input.setFocus()

    def save_intro(self):
        """Save current intro"""
        name = self.name_input.text().strip()
        content = self.content_input.toPlainText()

        if not name:
            QMessageBox.warning(self, 'Lỗi', 'Vui lòng nhập tên cho intro!')
            return

        # Check if this is an update or new intro
        current_item = self.intro_list.currentItem()
        if current_item:
            old_name = current_item.text()
            if self.manager.update_intro(old_name, name, content):
                QMessageBox.information(self, 'Thành công', f'Đã cập nhật intro "{name}"')
                self.load_intros()
            else:
                QMessageBox.warning(self, 'Lỗi', f'Tên intro "{name}" đã tồn tại!')
        else:
            # New intro
            if self.manager.add_intro(name, content):
                QMessageBox.information(self, 'Thành công', f'Đã thêm intro "{name}"')
                self.load_intros()
            else:
                QMessageBox.warning(self, 'Lỗi', f'Tên intro "{name}" đã tồn tại!')

    def delete_intro(self):
        """Delete selected intro"""
        current_item = self.intro_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Lỗi', 'Vui lòng chọn intro để xóa!')
            return

        intro_name = current_item.text()
        reply = QMessageBox.question(
            self,
            'Xác nhận',
            f'Bạn có chắc muốn xóa intro "{intro_name}"?',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.manager.delete_intro(intro_name):
                QMessageBox.information(self, 'Thành công', f'Đã xóa intro "{intro_name}"')
                self.load_intros()
                self.name_input.clear()
                self.content_input.clear()
            else:
                QMessageBox.warning(self, 'Lỗi', f'Không thể xóa intro "{intro_name}"')
