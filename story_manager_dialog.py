"""
Story Manager Dialog - Add, Edit, Delete Stories
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QTextEdit, QMessageBox, QGroupBox, QFormLayout, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from database_service import DatabaseService
from logger_config import LoggerConfig
from config import get_supported_languages, get_default_language

logger = LoggerConfig.get_logger('story_manager')


class StoryEditorDialog(QDialog):
    """Dialog for adding or editing a story"""

    def __init__(self, parent, db_service: DatabaseService, story: dict = None):
        super().__init__(parent)
        self.db_service = db_service
        self.story = story  # None for new story, dict for editing
        self.result_data = None

        self.init_ui()

    def init_ui(self):
        if self.story:
            self.setWindowTitle('✏️ Chỉnh sửa truyện')
        else:
            self.setWindowTitle('➕ Thêm truyện mới')

        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        layout = QVBoxLayout()

        # Form layout
        form_group = QGroupBox('Thông tin truyện')
        form_layout = QFormLayout()

        # Story name with language selector
        name_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText('Nhập tên truyện...')
        if self.story:
            self.name_input.setText(self.story.get('name', ''))
        name_layout.addWidget(self.name_input, 1)  # Stretch factor 1

        # Language dropdown
        self.language_combo = QComboBox()
        self.language_combo.setMinimumWidth(120)
        languages = get_supported_languages()
        for lang in languages:
            self.language_combo.addItem(f"{lang['name']}", lang['code'])

        # Set current language
        if self.story:
            current_lang = self.story.get('language', get_default_language())
        else:
            current_lang = get_default_language()

        # Find and set index for current language
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == current_lang:
                self.language_combo.setCurrentIndex(i)
                break

        name_layout.addWidget(self.language_combo)

        form_layout.addRow('Tên truyện *:', name_layout)

        # Author
        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText('Nhập tên tác giả...')
        if self.story:
            self.author_input.setText(self.story.get('author', ''))
        form_layout.addRow('Tác giả:', self.author_input)

        # Category
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText('VD: Cổ tích, Truyện cười...')
        if self.story:
            self.category_input.setText(self.story.get('category', ''))
        form_layout.addRow('Thể loại:', self.category_input)

        # Description
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText('Nhập mô tả truyện...')
        self.description_input.setMaximumHeight(120)
        if self.story:
            self.description_input.setPlainText(self.story.get('description', ''))
        form_layout.addRow('Mô tả:', self.description_input)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Buttons
        button_layout = QHBoxLayout()

        save_button = QPushButton('💾 Lưu')
        save_button.clicked.connect(self.save_story)
        button_layout.addWidget(save_button)

        cancel_button = QPushButton('❌ Hủy')
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def save_story(self):
        """Save or update story"""
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(self, 'Lỗi', 'Vui lòng nhập tên truyện!')
            return

        author = self.author_input.text().strip()
        category = self.category_input.text().strip()
        description = self.description_input.toPlainText().strip()
        language = self.language_combo.currentData()

        try:
            if self.story:
                # Update existing story
                self.result_data = self.db_service.update_story(
                    story_id=self.story['id'],
                    name=name,
                    author=author,
                    category=category,
                    description=description,
                    language=language
                )
                QMessageBox.information(self, 'Thành công', 'Đã cập nhật truyện!')
            else:
                # Create new story
                self.result_data = self.db_service.create_story(
                    name=name,
                    author=author,
                    category=category,
                    description=description,
                    language=language
                )
                QMessageBox.information(self, 'Thành công', 'Đã thêm truyện mới!')

            self.accept()

        except Exception as e:
            logger.error(f"Failed to save story: {e}")
            QMessageBox.critical(self, 'Lỗi', f'Không thể lưu truyện: {str(e)}')


class StoryManagerDialog(QDialog):
    """Main dialog for managing stories - not needed as we'll add buttons to main window"""
    pass
