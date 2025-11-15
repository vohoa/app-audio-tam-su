"""
Chapter Manager Dialog - Add, Edit, Delete Chapters
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QTextEdit, QMessageBox, QGroupBox, QFormLayout,
    QSpinBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from database_service import DatabaseService
from logger_config import LoggerConfig

logger = LoggerConfig.get_logger('chapter_manager')


class ChapterEditorDialog(QDialog):
    """Dialog for adding or editing a chapter"""

    def __init__(self, parent, db_service: DatabaseService, story_id: int, chapter: dict = None):
        super().__init__(parent)
        self.db_service = db_service
        self.story_id = story_id
        self.chapter = chapter  # None for new chapter, dict for editing
        self.result_data = None

        self.init_ui()

    def init_ui(self):
        if self.chapter:
            self.setWindowTitle('✏️ Chỉnh sửa chương')
        else:
            self.setWindowTitle('➕ Thêm chương mới')

        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        layout = QVBoxLayout()

        # Form layout
        form_group = QGroupBox('Thông tin chương')
        form_layout = QFormLayout()

        # Chapter number
        self.chapter_number_input = QSpinBox()
        self.chapter_number_input.setMinimum(1)
        self.chapter_number_input.setMaximum(9999)
        if self.chapter:
            self.chapter_number_input.setValue(self.chapter.get('chapter_number', 1))
        else:
            # Auto-set to next chapter number
            chapters_result = self.db_service.get_chapters_by_story(self.story_id)
            next_number = len(chapters_result.get('results', [])) + 1
            self.chapter_number_input.setValue(next_number)
        form_layout.addRow('Số chương:', self.chapter_number_input)

        # Chapter title
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText('Nhập tiêu đề chương...')
        if self.chapter:
            self.title_input.setText(self.chapter.get('title', ''))
        form_layout.addRow('Tiêu đề *:', self.title_input)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Content
        content_group = QGroupBox('Nội dung chương *')
        content_layout = QVBoxLayout()

        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText('Nhập nội dung chương...')
        if self.chapter:
            self.content_input.setPlainText(self.chapter.get('content', ''))
        content_layout.addWidget(self.content_input)

        content_group.setLayout(content_layout)
        layout.addWidget(content_group)

        # Buttons
        button_layout = QHBoxLayout()

        save_button = QPushButton('💾 Lưu')
        save_button.clicked.connect(self.save_chapter)
        button_layout.addWidget(save_button)

        cancel_button = QPushButton('❌ Hủy')
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def save_chapter(self):
        """Save or update chapter"""
        title = self.title_input.text().strip()
        content = self.content_input.toPlainText().strip()
        chapter_number = self.chapter_number_input.value()

        if not title:
            QMessageBox.warning(self, 'Lỗi', 'Vui lòng nhập tiêu đề chương!')
            return

        if not content:
            QMessageBox.warning(self, 'Lỗi', 'Vui lòng nhập nội dung chương!')
            return

        try:
            if self.chapter:
                # Update existing chapter
                self.result_data = self.db_service.update_chapter(
                    chapter_id=self.chapter['id'],
                    title=title,
                    content=content,
                    chapter_number=chapter_number
                )
                QMessageBox.information(self, 'Thành công', 'Đã cập nhật chương!')
            else:
                # Create new chapter
                self.result_data = self.db_service.create_chapter(
                    story_id=self.story_id,
                    title=title,
                    content=content,
                    chapter_number=chapter_number
                )
                QMessageBox.information(self, 'Thành công', 'Đã thêm chương mới!')

            self.accept()

        except Exception as e:
            logger.error(f"Failed to save chapter: {e}")
            QMessageBox.critical(self, 'Lỗi', f'Không thể lưu chương: {str(e)}')
