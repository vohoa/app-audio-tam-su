"""
Script to add story and chapter management UI to main.py
"""

# Read the file
with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find where to add imports
import_index = -1
for i, line in enumerate(lines):
    if 'from selenium_audio_generator import' in line:
        import_index = i + 1
        break

if import_index > 0:
    lines.insert(import_index, 'from story_manager_dialog import StoryEditorDialog\n')
    lines.insert(import_index + 1, 'from chapter_manager_dialog import ChapterEditorDialog\n')

# Find where to add story management buttons (after refresh button in left panel)
for i, line in enumerate(lines):
    if 'refresh_button.clicked.connect(self.load_stories)' in line:
        # Add buttons after refresh button
        insert_lines = [
            '        left_layout.addWidget(refresh_button)\n',
            '        \n',
            '        # Story management buttons\n',
            '        add_story_button = QPushButton(\'➕ Thêm truyện\')\n',
            '        add_story_button.clicked.connect(self.add_story)\n',
            '        left_layout.addWidget(add_story_button)\n',
            '        \n',
            '        edit_story_button = QPushButton(\'✏️ Sửa truyện\')\n',
            '        edit_story_button.clicked.connect(self.edit_story)\n',
            '        left_layout.addWidget(edit_story_button)\n',
            '        \n',
            '        delete_story_button = QPushButton(\'🗑️ Xóa truyện\')\n',
            '        delete_story_button.clicked.connect(self.delete_story)\n',
            '        left_layout.addWidget(delete_story_button)\n',
        ]
        # Remove the old refresh button line
        lines[i + 1] = ''  # Remove "left_layout.addWidget(refresh_button)"
        # Insert new lines
        for j, new_line in enumerate(insert_lines):
            lines.insert(i + 1 + j, new_line)
        break

# Find where to add chapter management buttons (after story info label in right panel)
for i, line in enumerate(lines):
    if 'self.story_info_label.setFont(QFont' in line:
        insert_lines = [
            '        right_layout.addWidget(self.story_info_label)\n',
            '        \n',
            '        # Chapter management buttons\n',
            '        chapter_mgmt_layout = QHBoxLayout()\n',
            '        \n',
            '        add_chapter_button = QPushButton(\'➕ Thêm chương\')\n',
            '        add_chapter_button.clicked.connect(self.add_chapter)\n',
            '        self.add_chapter_button = add_chapter_button\n',
            '        self.add_chapter_button.setEnabled(False)\n',
            '        chapter_mgmt_layout.addWidget(add_chapter_button)\n',
            '        \n',
            '        edit_chapter_button = QPushButton(\'✏️ Sửa chương\')\n',
            '        edit_chapter_button.clicked.connect(self.edit_selected_chapter)\n',
            '        self.edit_chapter_button = edit_chapter_button\n',
            '        self.edit_chapter_button.setEnabled(False)\n',
            '        chapter_mgmt_layout.addWidget(edit_chapter_button)\n',
            '        \n',
            '        delete_chapter_button = QPushButton(\'🗑️ Xóa chương\')\n',
            '        delete_chapter_button.clicked.connect(self.delete_selected_chapter)\n',
            '        self.delete_chapter_button = delete_chapter_button\n',
            '        self.delete_chapter_button.setEnabled(False)\n',
            '        chapter_mgmt_layout.addWidget(delete_chapter_button)\n',
            '        \n',
            '        right_layout.addLayout(chapter_mgmt_layout)\n',
        ]
        # Remove old line
        lines[i + 1] = ''
        # Insert new lines
        for j, new_line in enumerate(insert_lines):
            lines.insert(i + 1 + j, new_line)
        break

# Add methods at the end of MainWindow class (before if __name__ == '__main__')
method_code = '''
    # ============================================
    # Story Management Methods
    # ============================================

    def add_story(self):
        """Add a new story"""
        dialog = StoryEditorDialog(self, self.db_service)
        if dialog.exec_() == QDialog.Accepted:
            self.load_stories()

    def edit_story(self):
        """Edit selected story"""
        current_item = self.story_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Lỗi', 'Vui lòng chọn một truyện để chỉnh sửa!')
            return

        story_id = current_item.data(Qt.UserRole)
        try:
            story = self.db_service.get_story(story_id)
            dialog = StoryEditorDialog(self, self.db_service, story)
            if dialog.exec_() == QDialog.Accepted:
                self.load_stories()
                # Reload current story if it was the one edited
                if self.current_story and self.current_story['id'] == story_id:
                    self.load_chapters(story_id)
        except Exception as e:
            QMessageBox.critical(self, 'Lỗi', f'Không thể tải thông tin truyện: {str(e)}')

    def delete_story(self):
        """Delete selected story"""
        current_item = self.story_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Lỗi', 'Vui lòng chọn một truyện để xóa!')
            return

        story_id = current_item.data(Qt.UserRole)
        story_name = current_item.text()

        reply = QMessageBox.question(
            self, 'Xác nhận xóa',
            f'Bạn có chắc chắn muốn xóa truyện "{story_name}"?\\n\\nTất cả các chương sẽ bị xóa theo!',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.db_service.delete_story(story_id)
                QMessageBox.information(self, 'Thành công', 'Đã xóa truyện!')
                self.load_stories()
                # Clear current story if it was deleted
                if self.current_story and self.current_story['id'] == story_id:
                    self.current_story = None
                    self.chapters_data = None
                    self.story_info_label.setText('Chọn một truyện để xem chi tiết')
            except Exception as e:
                QMessageBox.critical(self, 'Lỗi', f'Không thể xóa truyện: {str(e)}')

    # ============================================
    # Chapter Management Methods
    # ============================================

    def add_chapter(self):
        """Add a new chapter to current story"""
        if not self.current_story:
            QMessageBox.warning(self, 'Lỗi', 'Vui lòng chọn một truyện trước!')
            return

        dialog = ChapterEditorDialog(self, self.db_service, self.current_story['id'])
        if dialog.exec_() == QDialog.Accepted:
            self.load_chapters(self.current_story['id'])

    def edit_selected_chapter(self):
        """Edit a selected chapter"""
        if not self.current_story:
            QMessageBox.warning(self, 'Lỗi', 'Vui lòng chọn một truyện trước!')
            return

        # Find selected chapter from widgets
        selected_chapter = None
        for widget in self.chapter_widgets:
            if hasattr(widget, 'checkbox') and widget.checkbox.isChecked():
                selected_chapter = widget.chapter_data
                break

        if not selected_chapter:
            QMessageBox.warning(self, 'Lỗi', 'Vui lòng chọn một chương để chỉnh sửa!')
            return

        dialog = ChapterEditorDialog(self, self.db_service, self.current_story['id'], selected_chapter)
        if dialog.exec_() == QDialog.Accepted:
            self.load_chapters(self.current_story['id'])

    def delete_selected_chapter(self):
        """Delete selected chapters"""
        if not self.current_story:
            QMessageBox.warning(self, 'Lỗi', 'Vui lòng chọn một truyện trước!')
            return

        # Find selected chapters from widgets
        selected_chapters = []
        for widget in self.chapter_widgets:
            if hasattr(widget, 'checkbox') and widget.checkbox.isChecked():
                selected_chapters.append(widget.chapter_data)

        if not selected_chapters:
            QMessageBox.warning(self, 'Lỗi', 'Vui lòng chọn ít nhất một chương để xóa!')
            return

        reply = QMessageBox.question(
            self, 'Xác nhận xóa',
            f'Bạn có chắc chắn muốn xóa {len(selected_chapters)} chương đã chọn?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                for chapter in selected_chapters:
                    self.db_service.delete_chapter(chapter['id'])
                QMessageBox.information(self, 'Thành công', f'Đã xóa {len(selected_chapters)} chương!')
                self.load_chapters(self.current_story['id'])
            except Exception as e:
                QMessageBox.critical(self, 'Lỗi', f'Không thể xóa chương: {str(e)}')

'''

# Find where to insert methods (before if __name__ == '__main__')
for i in range(len(lines) - 1, -1, -1):
    if 'if __name__ ==' in lines[i]:
        lines.insert(i, method_code)
        break

# Write the modified file
with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ Successfully added management UI to main.py!")
print("\nAdded features:")
print("1. Import story_manager_dialog and chapter_manager_dialog")
print("2. Added story management buttons (Add/Edit/Delete)")
print("3. Added chapter management buttons (Add/Edit/Delete)")
print("4. Added all management methods")
