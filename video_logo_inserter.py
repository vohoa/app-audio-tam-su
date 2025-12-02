"""
Video Logo Inserter
A standalone tool for inserting animated or static logos into videos using MoviePy
"""

import os
import math
import random
from typing import Tuple, Callable, Optional

# MoviePy 2.x imports
try:
    from moviepy import VideoFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
except ImportError:
    # Fallback for MoviePy 1.x
    from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QGroupBox, QRadioButton, QButtonGroup, QSpinBox,
    QProgressBar, QMessageBox, QComboBox, QDoubleSpinBox, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from logger_config import LoggerConfig

logger = LoggerConfig.get_logger('video_logo_inserter')


class VideoLogoWorker(QThread):
    """Worker thread for processing video with logo insertion"""
    progress = pyqtSignal(str)  # Status message
    progress_percent = pyqtSignal(int)  # Progress percentage
    finished = pyqtSignal(bool, str)  # Success, message

    def __init__(self, video_path: str, logo_path: str, output_path: str,
                 logo_mode: str, logo_size: int, position: str,
                 motion_speed: float = 1.0, opacity: float = 0.8,
                 add_intro: bool = True):
        super().__init__()
        self.video_path = video_path
        self.logo_path = logo_path
        self.output_path = output_path
        self.logo_mode = logo_mode
        self.logo_size = logo_size
        self.position = position
        self.motion_speed = motion_speed
        self.opacity = opacity
        self.add_intro = add_intro
        self.should_stop = False

        # Check for intro video
        self.intro_path = os.path.join(os.path.dirname(__file__), 'assets', 'intro.mp4')

    def run(self):
        intro_clip = None
        try:
            self.progress.emit('Đang tải video...')
            self.progress_percent.emit(10)

            # Load main video
            main_video = VideoFileClip(self.video_path)
            video_w, video_h = main_video.size

            if self.should_stop:
                main_video.close()
                self.finished.emit(False, 'Đã hủy')
                return

            # Load intro if enabled and exists
            video = main_video
            if self.add_intro and os.path.exists(self.intro_path):
                self.progress.emit('Đang tải intro video...')
                self.progress_percent.emit(15)
                try:
                    intro_clip = VideoFileClip(self.intro_path)

                    # Resize intro to match main video size if needed
                    if intro_clip.size != (video_w, video_h):
                        if hasattr(intro_clip, 'resized'):
                            intro_clip = intro_clip.resized(newsize=(video_w, video_h))
                        else:
                            intro_clip = intro_clip.resize(newsize=(video_w, video_h))

                    # Concatenate intro + main video
                    video = concatenate_videoclips([intro_clip, main_video])
                    logger.info(f"Intro added: {self.intro_path}")
                    self.progress.emit(f'Đã ghép intro ({intro_clip.duration:.1f}s)')
                except Exception as e:
                    logger.warning(f"Could not add intro: {e}")
                    self.progress.emit('Không thể thêm intro, tiếp tục với video gốc')
                    video = main_video

            if self.should_stop:
                video.close()
                main_video.close()
                if intro_clip:
                    intro_clip.close()
                self.finished.emit(False, 'Đã hủy')
                return

            self.progress.emit('Đang tải logo...')
            self.progress_percent.emit(20)

            # Load and prepare logo - compatible with MoviePy 1.x and 2.x
            # Logo duration = total video duration (intro + main if intro exists)
            logo = ImageClip(self.logo_path, duration=video.duration)

            # Resize logo
            if hasattr(logo, 'resized'):
                # MoviePy 2.x
                logo = logo.resized(height=self.logo_size)
            else:
                # MoviePy 1.x
                logo = logo.resize(height=self.logo_size)

            # Set logo opacity
            if self.opacity < 1.0:
                if hasattr(logo, 'with_opacity'):
                    # MoviePy 2.x
                    logo = logo.with_opacity(self.opacity)
                else:
                    # MoviePy 1.x
                    logo = logo.set_opacity(self.opacity)

            logo_w, logo_h = logo.size

            if self.should_stop:
                video.close()
                logo.close()
                self.finished.emit(False, 'Đã hủy')
                return

            self.progress.emit(f'Đang áp dụng hiệu ứng: {self.logo_mode}')
            self.progress_percent.emit(30)

            # Helper function to set position (compatible with both versions)
            def apply_position(clip, pos):
                if hasattr(clip, 'with_position'):
                    # MoviePy 2.x
                    return clip.with_position(pos)
                else:
                    # MoviePy 1.x
                    return clip.set_position(pos)

            # Helper function to set opacity with function (compatible with both versions)
            def apply_opacity(clip, opacity_func):
                if hasattr(clip, 'with_opacity'):
                    # MoviePy 2.x
                    return clip.with_opacity(opacity_func)
                else:
                    # MoviePy 1.x
                    return clip.set_opacity(opacity_func)

            # Apply position/motion based on mode
            if self.logo_mode == 'static':
                logo = apply_position(logo, self._get_static_position(video_w, video_h, logo_w, logo_h))

            elif self.logo_mode == 'sine_wave':
                # Di chuyển theo sóng sin (lên xuống)
                def sine_position(t):
                    x_pos = self._get_x_position(video_w, logo_w)
                    y_offset = 30 * math.sin(t * self.motion_speed)
                    base_y = self._get_base_y(video_h, logo_h)
                    return (x_pos, base_y + y_offset)
                logo = apply_position(logo, sine_position)

            elif self.logo_mode == 'cosine_wave':
                # Di chuyển theo sóng cos (trái phải)
                def cosine_position(t):
                    y_pos = self._get_base_y(video_h, logo_h)
                    x_offset = 30 * math.cos(t * self.motion_speed)
                    base_x = self._get_x_position(video_w, logo_w)
                    return (base_x + x_offset, y_pos)
                logo = apply_position(logo, cosine_position)

            elif self.logo_mode == 'circular':
                # Di chuyển theo hình tròn
                def circular_position(t):
                    base_x = self._get_x_position(video_w, logo_w)
                    base_y = self._get_base_y(video_h, logo_h)
                    radius = 40
                    x = base_x + radius * math.cos(t * self.motion_speed)
                    y = base_y + radius * math.sin(t * self.motion_speed)
                    return (x, y)
                logo = apply_position(logo, circular_position)

            elif self.logo_mode == 'slow_drift':
                # Di chuyển chậm khắp màn hình
                def drift_position(t):
                    # Sử dụng nhiều tần số sin/cos khác nhau để tạo chuyển động phức tạp
                    x = (video_w - logo_w) * (0.5 + 0.4 * math.sin(t * self.motion_speed * 0.1))
                    y = (video_h - logo_h) * (0.5 + 0.4 * math.cos(t * self.motion_speed * 0.13))
                    return (int(x), int(y))
                logo = apply_position(logo, drift_position)

            elif self.logo_mode == 'random_blink':
                # Hiện/ẩn ngẫu nhiên ở các vị trí khác nhau
                positions = self._generate_random_positions(video_w, video_h, logo_w, logo_h,
                                                           int(video.duration * 2))

                def random_position(t):
                    # Chọn vị trí dựa trên thời gian
                    index = int(t * 2) % len(positions)
                    return positions[index]

                # Tạo hiệu ứng nhấp nháy bằng cách thay đổi opacity
                def blink_opacity(t):
                    # Hiện trong 0.8s, ẩn trong 0.2s mỗi giây
                    return self.opacity if (t % 1.0) < 0.8 else 0

                logo = apply_position(logo, random_position)
                logo = apply_opacity(logo, blink_opacity)

            if self.should_stop:
                video.close()
                logo.close()
                self.finished.emit(False, 'Đã hủy')
                return

            self.progress.emit('Đang kết hợp video và logo...')
            self.progress_percent.emit(50)

            # Composite video with logo
            final_video = CompositeVideoClip([video, logo])

            if self.should_stop:
                video.close()
                logo.close()
                final_video.close()
                self.finished.emit(False, 'Đã hủy')
                return

            self.progress.emit('Đang xuất video...')
            self.progress_percent.emit(60)

            # Export video
            final_video.write_videofile(
                self.output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                fps=video.fps,
                logger=None  # Disable moviepy's logger
            )

            self.progress_percent.emit(100)

            # Clean up
            video.close()
            main_video.close()
            if intro_clip:
                intro_clip.close()
            logo.close()
            final_video.close()

            if self.should_stop:
                self.finished.emit(False, 'Đã hủy')
                return

            self.progress.emit('Hoàn thành!')
            intro_msg = f' (bao gồm intro {intro_clip.duration:.1f}s)' if intro_clip else ''
            self.finished.emit(True, f'Video đã được lưu tại: {self.output_path}{intro_msg}')

        except Exception as e:
            logger.error(f"Error processing video: {e}", exc_info=True)
            self.finished.emit(False, f'Lỗi: {str(e)}')
        finally:
            # Ensure cleanup even on error
            if intro_clip:
                try:
                    intro_clip.close()
                except:
                    pass

    def _get_static_position(self, video_w: int, video_h: int,
                            logo_w: int, logo_h: int) -> Tuple[int, int]:
        """Get static position based on selected position"""
        margin = 20

        if self.position == 'top-right':
            return (video_w - logo_w - margin, margin)
        elif self.position == 'top-left':
            return (margin, margin)
        elif self.position == 'bottom-right':
            return (video_w - logo_w - margin, video_h - logo_h - margin)
        elif self.position == 'bottom-left':
            return (margin, video_h - logo_h - margin)
        elif self.position == 'center':
            return ((video_w - logo_w) // 2, (video_h - logo_h) // 2)
        else:  # default to top-right
            return (video_w - logo_w - margin, margin)

    def _get_x_position(self, video_w: int, logo_w: int) -> int:
        """Get X position based on selected position"""
        margin = 20
        if 'right' in self.position:
            return video_w - logo_w - margin
        elif 'left' in self.position:
            return margin
        else:
            return (video_w - logo_w) // 2

    def _get_base_y(self, video_h: int, logo_h: int) -> int:
        """Get base Y position based on selected position"""
        margin = 20
        if 'top' in self.position:
            return margin
        elif 'bottom' in self.position:
            return video_h - logo_h - margin
        else:
            return (video_h - logo_h) // 2

    def _generate_random_positions(self, video_w: int, video_h: int,
                                   logo_w: int, logo_h: int,
                                   count: int) -> list:
        """Generate random positions for logo"""
        positions = []
        margin = 50

        for _ in range(count):
            x = random.randint(margin, max(margin, video_w - logo_w - margin))
            y = random.randint(margin, max(margin, video_h - logo_h - margin))
            positions.append((x, y))

        return positions

    def stop(self):
        """Stop the processing"""
        self.should_stop = True


class VideoLogoInserterDialog(QDialog):
    """Dialog for inserting logo into video"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Chèn Logo Vào Video')
        self.setMinimumWidth(600)
        self.setMinimumHeight(700)

        self.video_path = None
        self.logo_path = None
        self.worker = None

        # Check for default logo
        self.default_logo_path = os.path.join(os.path.dirname(__file__), 'logo', 'default.png')

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # File selection group
        file_group = QGroupBox('Chọn File')
        file_layout = QVBoxLayout()

        # Video selection
        video_layout = QHBoxLayout()
        self.video_label = QLabel('Chưa chọn video')
        self.video_label.setStyleSheet('color: gray;')
        video_btn = QPushButton('Chọn Video')
        video_btn.clicked.connect(self.select_video)
        video_layout.addWidget(QLabel('Video:'))
        video_layout.addWidget(self.video_label, 1)
        video_layout.addWidget(video_btn)
        file_layout.addLayout(video_layout)

        # Logo selection
        logo_layout = QHBoxLayout()
        self.logo_label = QLabel('Chưa chọn logo')

        # Check if default logo exists
        if os.path.exists(self.default_logo_path):
            self.logo_path = self.default_logo_path
            self.logo_label.setText(f'default.png (mặc định)')
            self.logo_label.setStyleSheet('color: blue; font-style: italic;')
        else:
            self.logo_label.setStyleSheet('color: gray;')

        logo_btn = QPushButton('Chọn Logo')
        logo_btn.clicked.connect(self.select_logo)
        logo_layout.addWidget(QLabel('Logo:'))
        logo_layout.addWidget(self.logo_label, 1)
        logo_layout.addWidget(logo_btn)
        file_layout.addLayout(logo_layout)

        # Intro checkbox
        intro_layout = QHBoxLayout()
        self.intro_checkbox = QCheckBox('Thêm intro video (assets/intro.mp4)')

        # Check if intro exists and set default
        intro_path = os.path.join(os.path.dirname(__file__), 'assets', 'intro.mp4')
        if os.path.exists(intro_path):
            self.intro_checkbox.setChecked(True)  # Default ON if intro exists
            self.intro_checkbox.setStyleSheet('color: green;')
            # Get intro duration
            try:
                intro_clip = VideoFileClip(intro_path)
                intro_duration = intro_clip.duration
                intro_clip.close()
                self.intro_checkbox.setText(f'Thêm intro video ({intro_duration:.1f}s) - assets/intro.mp4')
            except:
                pass
        else:
            self.intro_checkbox.setChecked(False)
            self.intro_checkbox.setEnabled(False)  # Disable if not exists
            self.intro_checkbox.setStyleSheet('color: gray;')
            self.intro_checkbox.setText('Thêm intro video (không tìm thấy assets/intro.mp4)')

        intro_layout.addWidget(self.intro_checkbox)
        file_layout.addLayout(intro_layout)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Logo mode selection
        mode_group = QGroupBox('Chế Độ Logo')
        mode_layout = QVBoxLayout()

        self.mode_group = QButtonGroup()

        # Static mode
        static_radio = QRadioButton('Tĩnh (Static)')
        static_radio.setChecked(True)
        self.mode_group.addButton(static_radio, 0)
        mode_layout.addWidget(static_radio)

        # Animated modes
        sine_radio = QRadioButton('Sóng Sin (Di chuyển lên xuống)')
        self.mode_group.addButton(sine_radio, 1)
        mode_layout.addWidget(sine_radio)

        cosine_radio = QRadioButton('Sóng Cos (Di chuyển trái phải)')
        self.mode_group.addButton(cosine_radio, 2)
        mode_layout.addWidget(cosine_radio)

        circular_radio = QRadioButton('Tròn (Di chuyển theo hình tròn)')
        self.mode_group.addButton(circular_radio, 3)
        mode_layout.addWidget(circular_radio)

        drift_radio = QRadioButton('Trôi Chậm (Di chuyển chậm khắp màn hình)')
        self.mode_group.addButton(drift_radio, 4)
        mode_layout.addWidget(drift_radio)

        blink_radio = QRadioButton('Nhấp Nháy (Hiện/ẩn ngẫu nhiên)')
        self.mode_group.addButton(blink_radio, 5)
        mode_layout.addWidget(blink_radio)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # Position selection (for static and base position for animated)
        position_group = QGroupBox('Vị Trí')
        position_layout = QVBoxLayout()

        position_combo_layout = QHBoxLayout()
        position_combo_layout.addWidget(QLabel('Vị trí cơ bản:'))
        self.position_combo = QComboBox()
        self.position_combo.addItems([
            'Góc trên phải (top-right)',
            'Góc trên trái (top-left)',
            'Góc dưới phải (bottom-right)',
            'Góc dưới trái (bottom-left)',
            'Giữa màn hình (center)'
        ])
        self.position_combo.setCurrentIndex(0)  # Default: top-right
        position_combo_layout.addWidget(self.position_combo, 1)
        position_layout.addLayout(position_combo_layout)

        position_group.setLayout(position_layout)
        layout.addWidget(position_group)

        # Logo settings
        settings_group = QGroupBox('Cài Đặt Logo')
        settings_layout = QVBoxLayout()

        # Logo size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel('Kích thước (chiều cao):'))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(30, 300)
        self.size_spin.setValue(100)  # Default 100x100 for default logo
        self.size_spin.setSuffix(' px')
        size_layout.addWidget(self.size_spin)
        size_layout.addStretch()
        settings_layout.addLayout(size_layout)

        # Motion speed
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel('Tốc độ chuyển động:'))
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.1, 5.0)
        self.speed_spin.setValue(1.0)
        self.speed_spin.setSingleStep(0.1)
        speed_layout.addWidget(self.speed_spin)
        speed_layout.addStretch()
        settings_layout.addLayout(speed_layout)

        # Opacity
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel('Độ trong suốt:'))
        self.opacity_spin = QDoubleSpinBox()
        self.opacity_spin.setRange(0.1, 1.0)
        self.opacity_spin.setValue(0.8)
        self.opacity_spin.setSingleStep(0.1)
        opacity_layout.addWidget(self.opacity_spin)
        opacity_layout.addStretch()
        settings_layout.addLayout(opacity_layout)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Progress
        self.progress_label = QLabel('Sẵn sàng')
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Buttons
        button_layout = QHBoxLayout()

        self.process_btn = QPushButton('Xử Lý Video')
        self.process_btn.clicked.connect(self.process_video)
        self.process_btn.setEnabled(False)
        button_layout.addWidget(self.process_btn)

        self.cancel_btn = QPushButton('Hủy')
        self.cancel_btn.clicked.connect(self.cancel_processing)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.cancel_btn)

        close_btn = QPushButton('Đóng')
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def select_video(self):
        """Select video file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Chọn Video',
            '',
            'Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)'
        )

        if file_path:
            self.video_path = file_path
            self.video_label.setText(os.path.basename(file_path))
            self.video_label.setStyleSheet('color: green;')
            self.check_ready()

    def select_logo(self):
        """Select logo file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Chọn Logo',
            '',
            'Image Files (*.png *.jpg *.jpeg *.gif);;All Files (*)'
        )

        if file_path:
            self.logo_path = file_path
            self.logo_label.setText(os.path.basename(file_path))
            self.logo_label.setStyleSheet('color: green;')
            self.check_ready()

    def check_ready(self):
        """Check if ready to process"""
        # Only need video path, logo is optional (use default if available)
        if self.video_path:
            self.process_btn.setEnabled(True)
        else:
            self.process_btn.setEnabled(False)

    def process_video(self):
        """Start video processing"""
        if not self.video_path:
            QMessageBox.warning(self, 'Cảnh báo', 'Vui lòng chọn video')
            return

        # Check logo path - use default if not selected
        logo_to_use = self.logo_path
        if not logo_to_use:
            # Try to use default logo
            if os.path.exists(self.default_logo_path):
                logo_to_use = self.default_logo_path
                logger.info(f"Using default logo: {self.default_logo_path}")
            else:
                # No logo selected and no default logo
                QMessageBox.information(
                    self,
                    'Thông báo',
                    'Không có logo được chọn và không tìm thấy logo mặc định (logo/default.png).\n'
                    'Video sẽ được xử lý mà không có logo.'
                )
                return

        # Get output path
        default_name = os.path.splitext(os.path.basename(self.video_path))[0] + '_with_logo.mp4'
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            'Lưu Video',
            default_name,
            'Video Files (*.mp4);;All Files (*)'
        )

        if not output_path:
            return

        # Get selected mode
        mode_id = self.mode_group.checkedId()
        mode_map = {
            0: 'static',
            1: 'sine_wave',
            2: 'cosine_wave',
            3: 'circular',
            4: 'slow_drift',
            5: 'random_blink'
        }
        logo_mode = mode_map.get(mode_id, 'static')

        # Get position
        position_text = self.position_combo.currentText()
        position_map = {
            'Góc trên phải (top-right)': 'top-right',
            'Góc trên trái (top-left)': 'top-left',
            'Góc dưới phải (bottom-right)': 'bottom-right',
            'Góc dưới trái (bottom-left)': 'bottom-left',
            'Giữa màn hình (center)': 'center'
        }
        position = position_map.get(position_text, 'top-right')

        # Get settings
        logo_size = self.size_spin.value()
        motion_speed = self.speed_spin.value()
        opacity = self.opacity_spin.value()
        add_intro = self.intro_checkbox.isChecked()

        # Disable UI
        self.process_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

        # Start worker
        self.worker = VideoLogoWorker(
            self.video_path,
            logo_to_use,  # Use default logo if no logo selected
            output_path,
            logo_mode,
            logo_size,
            position,
            motion_speed,
            opacity,
            add_intro  # Add intro video if checked
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.progress_percent.connect(self.on_progress_percent)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def cancel_processing(self):
        """Cancel video processing"""
        if self.worker:
            self.worker.stop()
            self.progress_label.setText('Đang hủy...')

    def on_progress(self, message: str):
        """Update progress message"""
        self.progress_label.setText(message)

    def on_progress_percent(self, percent: int):
        """Update progress bar"""
        self.progress_bar.setValue(percent)

    def on_finished(self, success: bool, message: str):
        """Handle processing finished"""
        self.process_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        if success:
            QMessageBox.information(self, 'Thành công', message)
            self.progress_bar.setValue(0)
            self.progress_label.setText('Sẵn sàng')
        else:
            QMessageBox.warning(self, 'Lỗi', message)
            self.progress_bar.setValue(0)
            self.progress_label.setText('Lỗi: ' + message)

        self.worker = None


# For testing
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dialog = VideoLogoInserterDialog()
    dialog.show()
    sys.exit(app.exec_())
