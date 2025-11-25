"""
Audio Generator Desktop Application
A PyQt5 desktop application for generating audio from story chapters
Similar to StoryDetailScreen interface
"""
import sys
import re
import os
import webbrowser
import traceback
from typing import Set, Dict, List, Optional
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QCheckBox,
    QTextEdit, QGroupBox, QSplitter, QMessageBox, QProgressBar,
    QDialog, QFileDialog, QScrollArea, QFrame, QSpinBox, QComboBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QColor

from database_service import DatabaseService
from config import WINDOW_WIDTH, WINDOW_HEIGHT, CHAPTERS_PER_PAGE
from logger_config import LoggerConfig, LogBlock, log_function_execution
# from login_dialog import LoginDialog  # Not needed with local database
from profile_manager import ProfileManagerDialog
from settings_manager import SettingsManagerDialog
from proxy_manager import ProxyManagerDialog
import config
from selenium_audio_generator import SeleniumAudioGenerator, convert_to_slug
from story_manager_dialog import StoryEditorDialog
from chapter_manager_dialog import ChapterEditorDialog
from whisper_transcriber import ensure_srt_exists
from video_generator import get_srt_path_for_chapter
# Initialize logger for main module
logger = LoggerConfig.get_logger('main')


class SeleniumAudioWorker(QThread):
    """Worker thread for LOCAL Selenium audio generation
    
    Thay thế AudioGenerationWorker cũ (API-based).
    Sử dụng SeleniumAudioGenerator để tạo audio trực tiếp trên máy local.
    """
    progress = pyqtSignal(str)  # Status message
    finished = pyqtSignal(bool, str, str)  # Success, message, audio_path
    
    def __init__(self,
                 db_service: DatabaseService,
                 chapter_id: int,
                 chapter_title: str,
                 chapter_content: str,
                 has_existing_audio: bool = False,
                 story_id: Optional[int] = None,
                 story_name: Optional[str] = None,
                 chapter_number: Optional[int] = None,
                 voice_gender: str = 'male',
                 channel_intro: str = '',
                 language: str = 'vi'):
        super().__init__()
        self.db_service = db_service
        self.chapter_id = chapter_id
        self.chapter_title = chapter_title
        self.chapter_content = chapter_content
        self.has_existing_audio = has_existing_audio
        self.story_id = story_id
        self.story_name = story_name
        self.chapter_number = chapter_number
        self.voice_gender = voice_gender
        self.channel_intro = channel_intro
        self.language = language
        self.should_stop = False
        self.generator = None
    
    def run(self):
        if self.generator:
            self.generator.cleanup()
        audio_path = None
        
        try:
            # Delete old audio if exists
            if self.has_existing_audio:
                self.progress.emit('Đang xóa audio cũ...')
                try:
                    self.db_service.delete_chapter_audio(self.chapter_id)
                    self.progress.emit('Đã xóa audio cũ')
                except Exception as e:
                    logger.warning(f"Failed to delete existing audio: {e}")
                    # Continue anyway
            
            if self.should_stop:
                self.finished.emit(False, 'Đã dừng', None)
                return
            
            # Import and initialize Selenium generator
            self.progress.emit('Đang khởi tạo Selenium...')
            
            # Determine paths relative to project structure
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            
            chrome_binary = config.get_chrome_binary_path()
            chromedriver = config.get_chrome_driver_path()
            download_path = os.path.join(current_dir, 'audio_downloads')
            
            # Ensure download path exists
            os.makedirs(download_path, exist_ok=True)
            
            # Create generator
            self.generator = SeleniumAudioGenerator(
                chrome_binary_path=chrome_binary,
                chromedriver_path=chromedriver,
                download_path=download_path,
                headless=False  # Show browser for now
            )
            
            if self.should_stop:
                self.finished.emit(False, 'Đã dừng', None)
                return
            
            # Generate audio
            self.progress.emit(f'Đang tạo audio cho "{self.chapter_title}"...')

            result = self.generator.generate_audio_for_chapter(
                chapter_content=self.chapter_content,
                chapter_id=self.chapter_id,
                chapter_title=self.chapter_title,
                story_id=self.story_id,
                story_name=self.story_name,
                chapter_number=self.chapter_number,
                voice_gender=self.voice_gender,
                channel_intro=self.channel_intro,
                language=self.language
            )
            
            if self.should_stop:
                self.finished.emit(False, 'Đã dừng', None)
                return
            
            # Check result
            logger.info(f"🔍 Generation result: {result}")
            
            # Handle None result
            if result is None:
                logger.error("❌ Audio generation returned None")
                self.generator.cleanup()
                self.finished.emit(False, 'Thất bại: Không có kết quả trả về', None)
                return
            
            # Check success
            if result.get('success'):
                audio_path = result.get('audio_path')

                if not audio_path:
                    logger.error("❌ Success=True but no audio_path in result")
                    logger.error(f"Result keys: {list(result.keys())}")
                    self.generator.cleanup()
                    self.finished.emit(False, 'Thất bại: Không có đường dẫn audio', None)
                    return

                # Generate SRT using Whisper
                if self.story_name and self.chapter_number:
                    self.progress.emit('Đang tạo SRT từ audio (Whisper)...')
                    try:
                        srt_path = get_srt_path_for_chapter(
                            self.story_name,
                            self.chapter_number,
                            self.language
                        )

                        srt_success = ensure_srt_exists(
                            audio_path=audio_path,
                            srt_path=srt_path,
                            language=self.language,
                            model_name="large"
                        )

                        if srt_success:
                            self.progress.emit(f'✓ Đã tạo SRT: {os.path.basename(srt_path)}')
                        else:
                            logger.warning(f"Failed to generate SRT for chapter {self.chapter_number}")
                            self.progress.emit('⚠ Không thể tạo SRT, bỏ qua...')

                    except Exception as srt_error:
                        logger.warning(f"SRT generation error: {srt_error}")
                        self.progress.emit('⚠ Lỗi tạo SRT, bỏ qua...')

                # Upload audio to backend
                self.progress.emit('Đang upload audio lên server...')

                try:
                    upload_result = self.db_service.upload_chapter_audio(
                        self.chapter_id,
                        audio_path
                    )
                    self.progress.emit('Đã upload audio thành công!')

                    self.finished.emit(True, 'Hoàn thành!', audio_path)
                    
                except Exception as upload_error:
                    logger.error(f"Failed to upload audio: {upload_error}", exc_info=True)
                    self.generator.cleanup()
                    self.finished.emit(
                        False, 
                        f'Tạo audio thành công nhưng upload thất bại: {str(upload_error)}',
                        audio_path
                    )
            else:
                # Log full result for debugging
                logger.error(f"❌ Audio generation failed")
                logger.error(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                logger.error(f"Result content: {result}")
                
                error_msg = result.get('message', result.get('error', 'Unknown error in generation flow'))
                logger.error(f"Error message: {error_msg}")
                
                self.generator.cleanup()
                self.finished.emit(False, f'Thất bại: {error_msg}', None)
                
        except Exception as e:
            logger.error(f"SeleniumAudioWorker exception for chapter {self.chapter_id}: {str(e)}", 
                        exc_info=True)
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.generator.cleanup_automation()
            self.finished.emit(False, f'Lỗi: {str(e)}', None)
            
        finally:
            # Cleanup
            self.generator.cleanup()
    
    def stop(self):
        self.should_stop = True


class ConversationGenerationWorker(QThread):
    """Worker thread for generating conversation JSON using Grok AI"""

    progress = pyqtSignal(str)  # Status message
    finished = pyqtSignal(bool, str, str)  # Success, message, json_path

    def __init__(self,
                 story_id: int,
                 chapter_id: int,
                 chapter_title: str,
                 chapter_content: str,
                 story_name: Optional[str] = None,
                 chapter_number: Optional[int] = None,
                 language: str = 'vi'):
        super().__init__()
        self.story_id = story_id
        self.chapter_id = chapter_id
        self.chapter_title = chapter_title
        self.chapter_content = chapter_content
        self.story_name = story_name
        self.chapter_number = chapter_number
        self.language = language
        self.should_stop = False
        self.generator = None
    
    def run(self):
        if self.generator:
            self.generator.close()
        json_path = None

        try:
            self.progress.emit('Đang khởi tạo Grok AI...')

            from grok_conversation_generator import GrokConversationGenerator
            from config import get_grok_ai_profile
            import os

            # Create conversation directory in story folder: audio_downloads/<language>/<story_name>/conversations/
            current_dir = os.path.dirname(os.path.abspath(__file__))
            safe_story_name = convert_to_slug(self.story_name) if self.story_name else f"story_{self.story_id}"
            conversation_dir = os.path.join(
                current_dir,
                'audio_downloads',
                self.language,
                safe_story_name,
                'conversations'
            )
            os.makedirs(conversation_dir, exist_ok=True)

            # Create generator
            self.generator = GrokConversationGenerator(
                conversation_dir=conversation_dir,
                headless=False,
                profile_name=get_grok_ai_profile()
            )
            
            if self.should_stop:
                self.finished.emit(False, 'Đã dừng', None)
                return
            
            # Send chapter content directly - Grok AI will create its own prompt
            self.progress.emit('📖 Đang gửi nội dung chương tới Grok AI...')
            self.progress.emit('(Grok sẽ tự tạo prompt và tạo hội thoại)')

            if self.should_stop:
                self.finished.emit(False, 'Đã dừng', None)
                return

            # Generate conversation using chapter content
            result = self.generator.create_conversation_full_workflow(
                chapter_content=self.chapter_content,
                story_name=self.story_name,
                story_id=self.story_id,
                chapter_number=self.chapter_number,
                voice_mapping=None,  # Auto-assign voices
                save_to_file=True,
                filename=f"{self.story_id}_{self.chapter_number or 0}.json"
            )
            
            if self.should_stop:
                self.finished.emit(False, 'Đã dừng', None)
                return
            
            # Check result
            if result and result.get('filepath'):
                json_path = result['filepath']
                segments_count = len(result.get('gemini_segments', []))
                self.generator.close()
                self.progress.emit(f'✓ Tạo thành công {segments_count} segments!')
                self.finished.emit(True, f'Hoàn thành! ({segments_count} segments)', json_path)
            else:
                logger.error("Failed to generate conversation")
                self.generator.close()
                self.finished.emit(False, 'Thất bại khi tạo conversation', None)
                
        except Exception as e:
            self.generator.close()
            logger.error(f"ConversationGenerationWorker exception: {str(e)}", exc_info=True)
            self.finished.emit(False, f'Lỗi: {str(e)}', None)
            
        finally:
            # Cleanup
            if self.generator:
                try:
                    self.generator.close()
                except Exception as cleanup_error:
                    logger.warning(f"Cleanup error: {cleanup_error}")
    
    def stop(self):
        self.should_stop = True


class PerplexityConversationGenerationWorker(QThread):
    """Worker thread for generating conversation JSON using Perplexity AI"""

    progress = pyqtSignal(str)  # Status message
    finished = pyqtSignal(bool, str, str)  # Success, message, json_path

    def __init__(self,
                 story_id: int,
                 chapter_id: int,
                 chapter_title: str,
                 chapter_content: str,
                 story_name: Optional[str] = None,
                 chapter_number: Optional[int] = None,
                 language: str = 'vi'):
        super().__init__()
        self.story_id = story_id
        self.chapter_id = chapter_id
        self.chapter_title = chapter_title
        self.chapter_content = chapter_content
        self.story_name = story_name
        self.chapter_number = chapter_number
        self.language = language
        self.should_stop = False
        self.generator = None

    def run(self):
        if self.generator:
            self.generator.close()
        json_path = None

        try:
            self.progress.emit('Đang khởi tạo Perplexity AI...')

            from perplexity_conversation_generator import PerplexityConversationGenerator
            from config import get_perplexity_ai_profile
            import os

            # Create conversation directory in story folder: audio_downloads/<language>/<story_name>/conversations/
            current_dir = os.path.dirname(os.path.abspath(__file__))
            safe_story_name = convert_to_slug(self.story_name) if self.story_name else f"story_{self.story_id}"
            conversation_dir = os.path.join(
                current_dir,
                'audio_downloads',
                self.language,
                safe_story_name,
                'conversations'
            )
            os.makedirs(conversation_dir, exist_ok=True)

            # Create generator
            self.generator = PerplexityConversationGenerator(
                conversation_dir=conversation_dir,
                headless=False,
                profile_name=get_perplexity_ai_profile()
            )
            
            if self.should_stop:
                self.finished.emit(False, 'Đã dừng', None)
                return
            
            # Send chapter content directly - Perplexity AI will create its own prompt
            self.progress.emit('📖 Đang gửi nội dung chương tới Perplexity AI...')
            self.progress.emit('(Perplexity sẽ tự tạo prompt và tạo hội thoại)')

            if self.should_stop:
                self.finished.emit(False, 'Đã dừng', None)
                return

            # Generate conversation using chapter content
            result = self.generator.create_conversation_full_workflow(
                chapter_content=self.chapter_content,
                story_name=self.story_name,
                story_id=self.story_id,
                chapter_number=self.chapter_number,
                voice_mapping=None,  # Auto-assign voices
                save_to_file=True,
                filename=f"{self.story_id}_{self.chapter_number or 0}.json"
            )
            
            if self.should_stop:
                self.finished.emit(False, 'Đã dừng', None)
                return
            
            # Check result
            if result and result.get('filepath'):
                json_path = result['filepath']
                segments_count = len(result.get('gemini_segments', []))
                self.generator.close()
                self.progress.emit(f'✓ Tạo thành công {segments_count} segments!')
                self.finished.emit(True, f'Hoàn thành! ({segments_count} segments)', json_path)
            else:
                logger.error("Failed to generate conversation")
                self.generator.close()
                self.finished.emit(False, 'Thất bại khi tạo conversation', None)
                
        except Exception as e:
            self.generator.close()
            logger.error(f"PerplexityConversationGenerationWorker exception: {str(e)}", exc_info=True)
            self.finished.emit(False, f'Lỗi: {str(e)}', None)
            
        finally:
            # Cleanup
            if self.generator:
                try:
                    self.generator.close()
                except Exception as cleanup_error:
                    logger.warning(f"Cleanup error: {cleanup_error}")
    
    def stop(self):
        self.should_stop = True


class ImagePromptGenerationWorker(QThread):
    """Worker thread for generating image prompts using Perplexity AI"""

    progress = pyqtSignal(str)  # Status message
    finished = pyqtSignal(bool, str, str)  # Success, message, json_path

    def __init__(self,
                 story_id: int,
                 chapter_id: int,
                 chapter_title: str,
                 chapter_content: str,
                 story_name: Optional[str] = None,
                 chapter_number: Optional[int] = None,
                 language: str = 'vi'):
        super().__init__()
        self.story_id = story_id
        self.chapter_id = chapter_id
        self.chapter_title = chapter_title
        self.chapter_content = chapter_content
        self.story_name = story_name
        self.chapter_number = chapter_number
        self.language = language
        self.should_stop = False
        self.generator = None
    
    def run(self):
        if self.generator:
            self.generator.close()
        json_path = None

        try:
            import json
            from selenium_audio_generator import convert_to_slug

            self.progress.emit('Đang khởi tạo Perplexity AI...')

            from perplexity_conversation_generator import PerplexityConversationGenerator
            from config import get_conversations_dir, get_perplexity_ai_profile
            import config

            # NEW: Get content from conversation file if available, otherwise use chapter_content
            content_to_use = self.chapter_content
            safe_story_name = convert_to_slug(self.story_name) if self.story_name else f"story_{self.story_id}"
            conversation_dir = os.path.join(
                config.AUDIO_DOWNLOAD_PATH,
                self.language,
                safe_story_name,
                'conversations'
            )
            conversation_filename = f"{self.story_id}_{self.chapter_number or 0}.json"
            conversation_path = os.path.join(conversation_dir, conversation_filename)

            # Check if conversation file exists
            if os.path.exists(conversation_path):
                self.progress.emit(f'📄 Tìm thấy file conversation: {conversation_filename}')
                try:
                    with open(conversation_path, 'r', encoding='utf-8') as f:
                        conversation_data = json.load(f)

                    # Send full JSON content instead of extracting text
                    if 'speakers' in conversation_data:
                        # Convert JSON to formatted string for sending
                        content_to_use = json.dumps(conversation_data, ensure_ascii=False, indent=2)
                        self.progress.emit('✓ Sử dụng toàn bộ nội dung JSON từ file conversation')
                    else:
                        self.progress.emit('⚠️ File conversation không đúng format, dùng nội dung chapter')
                except Exception as e:
                    logger.warning(f"Không thể đọc conversation file: {e}")
                    self.progress.emit('⚠️ Lỗi đọc conversation, dùng nội dung chapter')
            else:
                # Try to create conversation file first
                self.progress.emit('📝 Chưa có file conversation, đang tạo...')
                try:
                    os.makedirs(conversation_dir, exist_ok=True)

                    temp_generator = PerplexityConversationGenerator(
                        conversation_dir=conversation_dir,
                        headless=False,
                        profile_name=get_perplexity_ai_profile()
                    )

                    if self.should_stop:
                        self.finished.emit(False, 'Đã dừng', None)
                        return

                    self.progress.emit('🔮 Đang tạo conversation với Perplexity AI...')

                    result = temp_generator.create_conversation_full_workflow(
                        chapter_content=self.chapter_content,
                        story_name=self.story_name,
                        story_id=self.story_id,
                        chapter_number=self.chapter_number,
                        save_to_file=True,
                        filename=conversation_filename
                    )

                    temp_generator.close()

                    if result and result.get('filepath') and os.path.exists(conversation_path):
                        self.progress.emit('✓ Đã tạo file conversation thành công')
                        # Load the newly created conversation
                        with open(conversation_path, 'r', encoding='utf-8') as f:
                            conversation_data = json.load(f)

                        if 'speakers' in conversation_data:
                            # Send full JSON content instead of extracting text
                            content_to_use = json.dumps(conversation_data, ensure_ascii=False, indent=2)
                            self.progress.emit('✓ Sử dụng toàn bộ nội dung JSON từ file conversation mới tạo')
                    else:
                        self.progress.emit('⚠️ Không tạo được conversation, dùng nội dung chapter')

                except Exception as e:
                    logger.warning(f"Không thể tạo conversation file: {e}")
                    self.progress.emit('⚠️ Lỗi tạo conversation, dùng nội dung chapter')

            # Create generator
            self.generator = PerplexityConversationGenerator(
                conversation_dir=get_conversations_dir(),
                headless=False,
                profile_name=get_perplexity_ai_profile()
            )

            if self.should_stop:
                self.finished.emit(False, 'Đã dừng', None)
                return

            # Send content to generate image prompts
            self.progress.emit('🎨 Đang gửi nội dung để tạo image prompts...')
            self.progress.emit('(Sử dụng nội dung từ conversation)')

            if self.should_stop:
                self.finished.emit(False, 'Đã dừng', None)
                return

            # Generate image prompts using conversation content
            result = self.generator.generate_image_prompts_from_chapter(
                chapter_content=content_to_use,
                story_name=self.story_name,
                story_id=self.story_id,
                chapter_number=self.chapter_number
            )
            
            if self.should_stop:
                self.finished.emit(False, 'Đã dừng', None)
                return
            
            # Check result
            if result:
                # Image prompts are auto-saved by the generator
                prompts_count = len(result.get('prompts', []))
                self.generator.close()
                self.progress.emit(f'✓ Tạo thành công {prompts_count} image prompts!')
                json_path = result.get('saved_filepath', '')
                self.finished.emit(True, f'Hoàn thành! ({prompts_count} prompts)', json_path)
            else:
                logger.error("Failed to generate image prompts")
                self.generator.close()
                self.finished.emit(False, 'Thất bại khi tạo image prompts', None)
                
        except Exception as e:
            if self.generator:
                self.generator.close()
            logger.error(f"ImagePromptGenerationWorker exception: {str(e)}", exc_info=True)
            self.finished.emit(False, f'Lỗi: {str(e)}', None)
            
        finally:
            # Cleanup
            if self.generator:
                try:
                    self.generator.close()
                except Exception as cleanup_error:
                    logger.warning(f"Cleanup error: {cleanup_error}")
    
    def stop(self):
        self.should_stop = True


class RunwareImageGenerationWorker(QThread):
    """Worker thread for generating images from JSON prompts using Runware API"""

    progress = pyqtSignal(str)  # Status message
    finished = pyqtSignal(bool, str, str)  # Success, message, output_dir

    def __init__(self,
                 story_id: int,
                 chapter_id: int,
                 chapter_title: str,
                 chapter_content: str,
                 story_name: Optional[str] = None,
                 chapter_number: Optional[int] = None,
                 language: str = 'vi'):
        super().__init__()
        self.story_id = story_id
        self.chapter_id = chapter_id
        self.chapter_title = chapter_title
        self.chapter_content = chapter_content
        self.story_name = story_name
        self.chapter_number = chapter_number
        self.language = language
        self.should_stop = False
    
    def run(self):
        output_dir = None

        try:
            import asyncio
            from runware_image_generator import RunwareImageGenerator
            from perplexity_ai_automation import PerplexityAIAutomation
            import config
            import json

            # Check if JSON prompt file exists in story folder
            from selenium_audio_generator import convert_to_slug
            safe_story_name = convert_to_slug(self.story_name) if self.story_name else f"story_{self.story_id}"

            prompts_dir = os.path.join(
                config.AUDIO_DOWNLOAD_PATH,
                self.language,
                safe_story_name,
                'image_prompts'
            )
            json_filename = f"{self.story_id}_chapter_{self.chapter_number or 0}.json"
            json_path = os.path.join(prompts_dir, json_filename)

            logger.info(f"Expected image prompts path: {json_path}")
            logger.info(f"File exists initially: {os.path.exists(json_path)}")

            # If JSON doesn't exist, generate it first
            if not os.path.exists(json_path):
                self.progress.emit('📝 Chưa có file JSON prompts, đang tạo...')
                logger.info(f"Image prompts file not found: {json_path}")

                try:
                    perplexity = PerplexityAIAutomation(
                        headless=False,
                        use_profile=True,
                        profile_name=config.PERPLEXITY_AI_PROFILE
                    )

                    if self.should_stop:
                        self.finished.emit(False, 'Đã dừng', None)
                        return

                    self.progress.emit('🔮 Đang tạo image prompts với Perplexity AI...')
                    self.progress.emit('(Sử dụng nội dung chapter trực tiếp)')
                    logger.info(f"Generating image prompts via Perplexity for story {self.story_id}, chapter {self.chapter_number}")

                    result = perplexity.generate_image_prompts(
                        chapter_content=self.chapter_content,
                        story_name=self.story_name,
                        story_id=self.story_id,
                        chapter_number=self.chapter_number,
                        timeout=480,
                        save_to_file=True
                    )

                    perplexity.close()

                    if not result:
                        logger.error(f"Failed to generate image prompts. Result is empty or None")
                        self.finished.emit(False, 'Không thể tạo file JSON prompts', None)
                        return

                    # Update json_path to the actual saved file path
                    if 'saved_filepath' in result and result['saved_filepath']:
                        json_path = result['saved_filepath']
                        logger.info(f"Updated json_path to actual saved file: {json_path}")

                    # Verify file exists
                    if not os.path.exists(json_path):
                        logger.error(f"Image prompts file not found after generation. Expected: {json_path}, JSON exists: {os.path.exists(json_path)}")
                        self.finished.emit(False, 'Không thể tạo file JSON prompts', None)
                        return

                    self.progress.emit('✓ Đã tạo file JSON prompts thành công')
                    logger.info(f"Successfully created image prompts at: {json_path}")

                except Exception as e:
                    logger.error(f"Error generating JSON prompts: {e}", exc_info=True)
                    self.finished.emit(False, f'Lỗi khi tạo JSON prompts: {str(e)}', None)
                    return
            else:
                self.progress.emit(f'✓ Đã tìm thấy file JSON prompts: {json_filename}')
                logger.info(f"Using existing image prompts file: {json_path}")
            
            if self.should_stop:
                self.finished.emit(False, 'Đã dừng', None)
                return
            
            # Generate images using Runware API
            self.progress.emit('🎨 Đang tạo hình ảnh với Runware API...')
            self.progress.emit('(Quá trình này có thể mất vài phút)')
            logger.info(f"Starting Runware image generation from: {json_path}")
            logger.info(f"Model: {config.RUNWARE_DEFAULT_MODEL}, Size: {config.RUNWARE_DEFAULT_WIDTH}x{config.RUNWARE_DEFAULT_HEIGHT}")

            # Run async function in sync context
            generator = RunwareImageGenerator()
            logger.info("Calling RunwareImageGenerator.generate_images_from_json()")
            result = asyncio.run(
                generator.generate_images_from_json(
                    json_path=json_path,
                    story_name=self.story_name,
                    story_id=self.story_id,
                    chapter_number=self.chapter_number,
                    model=config.RUNWARE_DEFAULT_MODEL,
                    width=config.RUNWARE_DEFAULT_WIDTH,
                    height=config.RUNWARE_DEFAULT_HEIGHT,
                    language=self.language
                )
            )
            logger.info(f"Runware API call completed. Success: {result.get('success')}, Images: {result.get('generated_images', 0)}")
            
            if self.should_stop:
                self.finished.emit(False, 'Đã dừng', None)
                return
            
            # Check result
            if result.get('success'):
                output_dir = result.get('output_dir')
                generated_count = result.get('generated_images', 0)
                total_count = result.get('total_prompts', 0)
                cached_count = result.get('cached_images', 0)
                new_count = result.get('new_images', 0)
                is_cached = result.get('cached', False)
                
                # Display appropriate message
                if is_cached or cached_count == generated_count:
                    self.progress.emit(f'✓ Sử dụng {generated_count}/{total_count} hình ảnh có sẵn!')
                    self.progress.emit('⚡ Bỏ qua việc gọi Runware API (ảnh đã tồn tại)')
                elif cached_count > 0:
                    self.progress.emit(f'✓ Hoàn tất: {generated_count}/{total_count} hình ảnh!')
                    self.progress.emit(f'  ({cached_count} có sẵn + {new_count} mới tạo)')
                else:
                    self.progress.emit(f'✓ Đã tạo {generated_count}/{total_count} hình ảnh!')
                
                self.progress.emit(f'📁 Lưu tại: {output_dir}')
                
                # Now create video from images + audio
                if generated_count > 0:
                    if self.should_stop:
                        self.finished.emit(False, 'Đã dừng', None)
                        return
                    
                    self.progress.emit('')
                    self.progress.emit('🎬 Bắt đầu tạo video từ ảnh và audio...')
                    
                    # Find audio file
                    # Sử dụng slug cho tên thư mục audio với language
                    safe_story_name = convert_to_slug(self.story_name or f"story_{self.story_id}")
                    audio_dir = os.path.join(
                        config.AUDIO_DOWNLOAD_PATH,
                        self.language,
                        safe_story_name
                    )
                    audio_filename = f"chuong_{self.chapter_number:02d}.mp3"
                    audio_path = os.path.join(audio_dir, audio_filename)

                    if not os.path.exists(audio_path):
                        self.progress.emit(f'⚠️ Không tìm thấy file audio: {audio_filename}')
                        self.progress.emit('Vui lòng tạo audio trước khi tạo video')
                        self.finished.emit(
                            True,
                            f'Hoàn thành ảnh! ({generated_count}/{total_count}) - Thiếu audio',
                            output_dir
                        )
                        return
                    
                    self.progress.emit(f'✓ Tìm thấy audio: {audio_filename}')
                    
                    # Create video
                    try:
                        from video_generator import create_video_sync, get_srt_path_for_chapter

                        # Auto-generate video path in story folder: audio_downloads/<language>/<story_name>/videos/
                        safe_story_name = convert_to_slug(self.story_name or f"story_{self.story_id}")
                        video_dir = os.path.join(
                            config.AUDIO_DOWNLOAD_PATH,
                            self.language,
                            safe_story_name,
                            'videos'
                        )
                        os.makedirs(video_dir, exist_ok=True)
                        video_filename = f"chapter_{self.chapter_number:02d}.mp4"
                        video_path = os.path.join(video_dir, video_filename)

                        # Get SRT path for sync (if exists)
                        srt_path = get_srt_path_for_chapter(
                            self.story_name or f"story_{self.story_id}",
                            self.chapter_number,
                            self.language
                        )

                        # Check if SRT file exists
                        if os.path.exists(srt_path):
                            self.progress.emit(f'🎯 Tìm thấy file SRT: {os.path.basename(srt_path)}')
                            self.progress.emit('Sẽ sync video chính xác với audio')
                        else:
                            self.progress.emit('📝 Không có file SRT, sử dụng sync ước tính từ text')
                            srt_path = None  # Don't pass non-existent path

                        self.progress.emit('🎥 Đang ghép ảnh và audio thành video...')
                        self.progress.emit('(Quá trình này có thể mất vài phút)')

                        # Use create_video_sync with full sync support
                        video_result = create_video_sync(
                            image_dir=output_dir,
                            audio_path=audio_path,
                            output_path=video_path,
                            image_prompts_path=json_path,
                            chapter_content=self.chapter_content,
                            srt_path=srt_path,
                            fps=config.VIDEO_FPS,
                            transition_duration=config.VIDEO_TRANSITION_DURATION,
                            language=self.language
                        )
                        
                        if self.should_stop:
                            self.finished.emit(False, 'Đã dừng', None)
                            return
                        
                        if video_result.get('success'):
                            video_output = video_result.get('output_path')
                            video_duration = video_result.get('duration', 0)
                            
                            self.progress.emit(f'✓ Video đã được tạo thành công!')
                            self.progress.emit(f'📹 Video: {video_filename}')
                            self.progress.emit(f'⏱️ Thời lượng: {video_duration:.1f}s')
                            self.progress.emit(f'📁 Lưu tại: {video_output}')
                            
                            self.finished.emit(
                                True,
                                f'Hoàn thành! ({generated_count}/{total_count} ảnh + video)',
                                video_output
                            )
                        else:
                            error_msg = video_result.get('error', 'Unknown error')
                            logger.error(f"Failed to create video: {error_msg}")
                            self.progress.emit(f'⚠️ Lỗi tạo video: {error_msg}')
                            self.finished.emit(
                                True,
                                f'Hoàn thành ảnh ({generated_count}/{total_count}) - Lỗi tạo video',
                                output_dir
                            )
                    
                    except ImportError:
                        self.progress.emit('⚠️ MoviePy chưa được cài đặt')
                        self.progress.emit('Chạy: pip install moviepy imageio-ffmpeg')
                        self.finished.emit(
                            True,
                            f'Hoàn thành ảnh! ({generated_count}/{total_count}) - Thiếu MoviePy',
                            output_dir
                        )
                    except Exception as e:
                        logger.error(f"Error creating video: {e}", exc_info=True)
                        self.progress.emit(f'⚠️ Lỗi khi tạo video: {str(e)}')
                        self.finished.emit(
                            True,
                            f'Hoàn thành ảnh ({generated_count}/{total_count}) - Lỗi video',
                            output_dir
                        )
                else:
                    self.finished.emit(
                        True,
                        f'Hoàn thành! ({generated_count}/{total_count} ảnh)',
                        output_dir
                    )
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"Failed to generate images: {error_msg}")
                self.finished.emit(False, f'Thất bại: {error_msg}', None)
                
        except Exception as e:
            logger.error(f"RunwareImageGenerationWorker exception: {str(e)}", exc_info=True)
            self.finished.emit(False, f'Lỗi: {str(e)}', None)
    
    def stop(self):
        self.should_stop = True


class WhisperSRTWorker(QThread):
    """Worker thread for generating SRT subtitles using Whisper"""

    progress = pyqtSignal(str)  # Status message
    finished = pyqtSignal(bool, str, str)  # Success, message, srt_path

    def __init__(self,
                 story_id: int,
                 chapter_id: int,
                 chapter_number: int,
                 story_name: Optional[str] = None,
                 language: str = 'vi'):
        super().__init__()
        self.story_id = story_id
        self.chapter_id = chapter_id
        self.chapter_number = chapter_number
        self.story_name = story_name
        self.language = language
        self.should_stop = False

    def run(self):
        srt_path = None

        try:
            from selenium_audio_generator import convert_to_slug
            import config

            # Find audio file
            safe_story_name = convert_to_slug(self.story_name) if self.story_name else f"story_{self.story_id}"
            audio_dir = os.path.join(
                config.AUDIO_DOWNLOAD_PATH,
                self.language,
                safe_story_name
            )

            # Try multiple audio filename patterns (prefer mp3)
            audio_path = None
            audio_patterns = [
                f"chuong_{self.chapter_number:02d}.mp3",
                f"chuong_{self.chapter_number:02d}.wav",
                f"chapter_{self.chapter_number}.mp3",
                f"chapter_{self.chapter_number}.wav",
            ]

            for pattern in audio_patterns:
                test_path = os.path.join(audio_dir, pattern)
                if os.path.exists(test_path):
                    audio_path = test_path
                    break

            if not audio_path:
                self.progress.emit(f'❌ Không tìm thấy file audio cho chương {self.chapter_number}')
                self.finished.emit(False, 'Không tìm thấy file audio', None)
                return

            self.progress.emit(f'✓ Tìm thấy audio: {os.path.basename(audio_path)}')

            if self.should_stop:
                self.finished.emit(False, 'Đã dừng', None)
                return

            # Get SRT path
            srt_path = get_srt_path_for_chapter(
                self.story_name or f"story_{self.story_id}",
                self.chapter_number,
                self.language
            )

            # Check if SRT already exists
            if os.path.exists(srt_path):
                self.progress.emit(f'⚠️ File SRT đã tồn tại: {os.path.basename(srt_path)}')
                self.progress.emit('Đang tạo lại SRT mới...')

            # Generate SRT using Whisper
            self.progress.emit('🎤 Đang load model Whisper (medium)...')
            self.progress.emit('(Quá trình này có thể mất 1-3 phút)')

            if self.should_stop:
                self.finished.emit(False, 'Đã dừng', None)
                return

            srt_success = ensure_srt_exists(
                audio_path=audio_path,
                srt_path=srt_path,
                language=self.language,
                model_name="large",
                force_regenerate=True  # Always regenerate when called manually
            )

            if self.should_stop:
                self.finished.emit(False, 'Đã dừng', None)
                return

            if srt_success:
                self.progress.emit(f'✓ Đã tạo SRT: {os.path.basename(srt_path)}')
                self.finished.emit(True, 'Hoàn thành tạo SRT!', srt_path)
            else:
                self.finished.emit(False, 'Không thể tạo file SRT', None)

        except Exception as e:
            logger.error(f"WhisperSRTWorker exception: {str(e)}", exc_info=True)
            self.finished.emit(False, f'Lỗi: {str(e)}', None)

    def stop(self):
        self.should_stop = True


# Legacy class kept for backwards compatibility - redirects to new implementation
class AudioGenerationWorker(SeleniumAudioWorker):
    """Deprecated: Use SeleniumAudioWorker instead
    
    This class is kept for backwards compatibility only.
    """
    def __init__(self, db_service: DatabaseService, chapter_id: int, method: str, has_existing_audio: bool = False):
        logger.warning(f"AudioGenerationWorker is deprecated. Use SeleniumAudioWorker instead.")
        # For backwards compatibility, we need chapter data
        # This should not be used anymore - update callers to use SeleniumAudioWorker
        super().__init__(
            db_service=db_service,
            chapter_id=chapter_id,
            chapter_title=f"Chapter {chapter_id}",
            chapter_content="",
            has_existing_audio=has_existing_audio
        )


class BatchAudioGenerationDialog(QDialog):
    """Dialog for batch audio generation"""
    
    def __init__(self, parent, db_service: DatabaseService, selected_chapters: List[Dict], current_story: Dict = None):
        super().__init__(parent)
        self.db_service = db_service
        self.selected_chapters = selected_chapters
        self.current_story = current_story
        self.is_processing = False
        self.current_worker = None
        self.current_chapter_index = 0
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('🤖 Tạo Audio Tuần Tự Bằng Selenium')
        self.setModal(True)
        self.resize(700, 500)
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel(f'<h3>Chương đã chọn: {len(self.selected_chapters)}</h3>')
        layout.addWidget(header)
        
        # Chapter list
        list_widget = QListWidget()
        for chapter in self.selected_chapters:
            item_text = f"Chương {chapter['chapter_number']}: {chapter['title']}"
            if chapter.get('audio_url'):
                item_text += " [🎵 Có audio cũ]"
            list_widget.addItem(item_text)
        layout.addWidget(list_widget)
        
        # Progress bar
        self.progress_label = QLabel('Sẵn sàng bắt đầu')
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(len(self.selected_chapters))
        layout.addWidget(self.progress_bar)
        
        # Status text
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        layout.addWidget(self.status_text)
        
        # Warning
        warning = QLabel('''
<b>⚠️ Lưu ý:</b><br>
• Quá trình này sẽ tạo audio tuần tự cho tất cả chương đã chọn<br>
• Audio cũ (nếu có) sẽ được xóa và thay thế<br>
• Thời gian xử lý: khoảng 2-5 phút mỗi chương<br>
• Vui lòng không đóng cửa sổ này trong quá trình xử lý
        ''')
        warning.setStyleSheet('background-color: #fff3cd; padding: 10px; border-radius: 5px;')
        layout.addWidget(warning)

        # Options
        options_layout = QHBoxLayout()

        # Voice gender selection
        voice_label = QLabel('Giọng đọc:')
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(['Nam', 'Nữ'])
        options_layout.addWidget(voice_label)
        options_layout.addWidget(self.voice_combo)

        # Channel Intro selection
        from channel_intro_manager import ChannelIntroManager
        intro_label = QLabel('Channel Intro:')
        self.intro_combo = QComboBox()
        self.intro_manager = ChannelIntroManager()
        self.intro_combo.addItems(self.intro_manager.get_intro_names())
        self.intro_combo.setCurrentIndex(0)
        options_layout.addWidget(intro_label)
        options_layout.addWidget(self.intro_combo)

        layout.addLayout(options_layout)

        # Buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton('🚀 Bắt đầu tạo audio')
        self.start_button.clicked.connect(self.start_batch_processing)
        button_layout.addWidget(self.start_button)
        
        self.cancel_button = QPushButton('Hủy')
        self.cancel_button.clicked.connect(self.close)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def start_batch_processing(self):
        self.is_processing = True
        self.start_button.setEnabled(False)
        self.current_chapter_index = 0
        self.process_next_chapter()
    
    def process_next_chapter(self):
        if self.current_chapter_index >= len(self.selected_chapters):
            self.finish_batch_processing()
            return
        
        chapter = self.selected_chapters[self.current_chapter_index]
        self.progress_label.setText(
            f'Đang xử lý chương {self.current_chapter_index + 1}/{len(self.selected_chapters)}: '
            f'{chapter["title"]}'
        )
        self.progress_bar.setValue(self.current_chapter_index)
        
        # Fetch full chapter content if needed
        try:
            if not chapter.get('content'):
                self.status_text.append(
                    f'[Chương {self.current_chapter_index + 1}] Đang tải nội dung...'
                )
                # Fetch full chapter data from API
                full_chapter = self.db_service.get_chapter(chapter['id'])
                chapter['content'] = full_chapter.get('content', '')
        except Exception as e:
            logger.error(f"Failed to fetch chapter content: {e}")
            self.status_text.append(
                f'❌ Chương {chapter["chapter_number"]}: Không thể tải nội dung - {str(e)}\n'
            )
            self.current_chapter_index += 1
            QTimer.singleShot(500, self.process_next_chapter)
            return
        
        # Check if chapter has content
        if not chapter.get('content'):
            self.status_text.append(
                f'⚠️ Chương {chapter["chapter_number"]}: Không có nội dung, bỏ qua\n'
            )
            self.current_chapter_index += 1
            QTimer.singleShot(500, self.process_next_chapter)
            return
        
        # Get selected voice gender
        voice_gender = 'male' if self.voice_combo.currentText() == 'Nam' else 'female'

        # Get selected channel intro
        intro_name = self.intro_combo.currentText()
        channel_intro = self.intro_manager.get_intro_by_name(intro_name) or ""

        # Start worker with new SeleniumAudioWorker
        self.current_worker = SeleniumAudioWorker(
            db_service=self.db_service,
            chapter_id=chapter['id'],
            chapter_title=chapter.get('title', f"Chapter {chapter['id']}"),
            chapter_content=chapter['content'],
            has_existing_audio=bool(chapter.get('audio_url')),
            story_id=self.current_story.get('id') if self.current_story else None,
            story_name=self.current_story.get('name') if self.current_story else None,
            chapter_number=chapter.get('chapter_number'),
            voice_gender=voice_gender,
            channel_intro=channel_intro,
            language=self.current_story.get('language', 'vi') if self.current_story else 'vi'
        )
        self.current_worker.progress.connect(self.on_worker_progress)
        self.current_worker.finished.connect(self.on_worker_finished)
        self.current_worker.start()
    
    def on_worker_progress(self, message: str):
        self.status_text.append(f'[Chương {self.current_chapter_index + 1}] {message}')
    
    def on_worker_finished(self, success: bool, message: str, audio_path: str = None):
        """Handle worker completion
        
        Args:
            success: Whether generation succeeded
            message: Status message
            audio_path: Path to generated audio file (if successful)
        """
        chapter = self.selected_chapters[self.current_chapter_index]
        status = '✅' if success else '❌'
        
        log_msg = f'{status} Chương {chapter["chapter_number"]}: {message}'
        if audio_path and success:
            log_msg += f' ({audio_path})'
        self.status_text.append(log_msg + '\n')
        
        # Move to next chapter
        self.current_chapter_index += 1
        QTimer.singleShot(2000, self.process_next_chapter)  # 2 second delay between chapters
    
    def finish_batch_processing(self):
        self.is_processing = False
        self.progress_bar.setValue(len(self.selected_chapters))
        self.progress_label.setText(
            f'✅ Hoàn thành tạo audio cho {len(self.selected_chapters)} chương!'
        )
        self.start_button.setText('Đóng')
        self.start_button.setEnabled(True)
        self.start_button.clicked.disconnect()
        self.start_button.clicked.connect(self.close)
    
    def closeEvent(self, event):
        if self.is_processing:
            reply = QMessageBox.question(
                self,
                'Xác nhận',
                'Quá trình đang chạy. Bạn có chắc muốn hủy?',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            if self.current_worker:
                self.current_worker.stop()
        event.accept()


class BatchConversationGenerationDialog(QDialog):
    """Dialog for batch conversation JSON generation"""
    
    def __init__(self, parent, selected_chapters: List[Dict], current_story: Dict = None):
        super().__init__(parent)
        self.selected_chapters = selected_chapters
        self.current_story = current_story
        self.is_processing = False
        self.current_worker = None
        self.current_chapter_index = 0
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('💬 Tạo JSON Hội Thoại Tuần Tự')
        self.setModal(True)
        self.resize(700, 500)
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel(f'<h3>Chương đã chọn: {len(self.selected_chapters)}</h3>')
        layout.addWidget(header)
        
        # Chapter list
        list_widget = QListWidget()
        for chapter in self.selected_chapters:
            item_text = f"Chương {chapter['chapter_number']}: {chapter['title']}"
            list_widget.addItem(item_text)
        layout.addWidget(list_widget)
        
        # Progress bar
        self.progress_label = QLabel('Sẵn sàng bắt đầu')
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(len(self.selected_chapters))
        layout.addWidget(self.progress_bar)
        
        # Status text
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        layout.addWidget(self.status_text)
        
        # Warning
        warning = QLabel('''
<b>⚠️ Lưu ý:</b><br>
• Quá trình này sẽ tạo JSON conversation tuần tự cho tất cả chương đã chọn<br>
• Grok AI sẽ được sử dụng để tạo hội thoại tự động<br>
• JSON sẽ được lưu vào thư mục audio_downloads/<story_name>/conversations/<br>
• Bạn cần đăng nhập X/Twitter (lần đầu)<br>
• Quá trình có thể mất nhiều thời gian
        ''')
        warning.setWordWrap(True)
        warning.setStyleSheet('background-color: #fff3cd; padding: 10px; border-radius: 5px;')
        layout.addWidget(warning)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.start_button = QPushButton('🚀 Bắt đầu')
        self.start_button.clicked.connect(self.start_batch_processing)
        button_layout.addWidget(self.start_button)
        
        cancel_button = QPushButton('❌ Hủy')
        cancel_button.clicked.connect(self.close)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def start_batch_processing(self):
        """Start processing chapters"""
        self.is_processing = True
        self.start_button.setEnabled(False)
        self.progress_label.setText('Đang xử lý...')
        self.status_text.append('🚀 Bắt đầu tạo JSON conversation...\n')
        
        self.current_chapter_index = 0
        self.process_next_chapter()
    
    def process_next_chapter(self):
        """Process next chapter in queue"""
        if self.current_chapter_index >= len(self.selected_chapters):
            self.finish_batch_processing()
            return
        
        chapter = self.selected_chapters[self.current_chapter_index]
        
        # Update progress
        self.progress_bar.setValue(self.current_chapter_index)
        self.progress_label.setText(
            f'Đang xử lý chương {self.current_chapter_index + 1}/{len(self.selected_chapters)}'
        )
        self.status_text.append(
            f'\n📝 Chương {chapter["chapter_number"]}: {chapter["title"]}\n'
        )
        
        # Check if chapter has content
        if not chapter.get('content'):
            self.status_text.append(
                f'⚠️ Chương {chapter["chapter_number"]}: Không có nội dung, bỏ qua\n'
            )
            self.current_chapter_index += 1
            QTimer.singleShot(500, self.process_next_chapter)
            return
        
        # Start worker
        self.current_worker = ConversationGenerationWorker(
            story_id=self.current_story.get('id') if self.current_story else None,
            chapter_id=chapter['id'],
            chapter_title=chapter.get('title', f"Chapter {chapter['id']}"),
            chapter_content=chapter['content'],
            story_name=self.current_story.get('name') if self.current_story else None,
            chapter_number=chapter.get('chapter_number'),
            language=self.current_story.get('language', 'vi') if self.current_story else 'vi'
        )
        self.current_worker.progress.connect(self.on_worker_progress)
        self.current_worker.finished.connect(self.on_worker_finished)
        self.current_worker.start()
    
    def on_worker_progress(self, message: str):
        self.status_text.append(f'[Chương {self.current_chapter_index + 1}] {message}')
    
    def on_worker_finished(self, success: bool, message: str, json_path: str = None):
        """Handle worker completion"""
        chapter = self.selected_chapters[self.current_chapter_index]
        status = '✅' if success else '❌'
        
        log_msg = f'{status} Chương {chapter["chapter_number"]}: {message}'
        if json_path and success:
            log_msg += f' ({json_path})'
        self.status_text.append(log_msg + '\n')
        
        # Move to next chapter
        self.current_chapter_index += 1
        QTimer.singleShot(3000, self.process_next_chapter)  # 3 second delay between chapters
    
    def finish_batch_processing(self):
        self.is_processing = False
        self.progress_bar.setValue(len(self.selected_chapters))
        self.progress_label.setText(
            f'✅ Hoàn thành tạo JSON cho {len(self.selected_chapters)} chương!'
        )
        self.start_button.setText('Đóng')
        self.start_button.setEnabled(True)
        self.start_button.clicked.disconnect()
        self.start_button.clicked.connect(self.close)
    
    def closeEvent(self, event):
        if self.is_processing:
            reply = QMessageBox.question(
                self,
                'Xác nhận',
                'Quá trình đang chạy. Bạn có chắc muốn hủy?',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            if self.current_worker:
                self.current_worker.stop()
        event.accept()


class BatchPerplexityConversationGenerationDialog(QDialog):
    """Dialog for batch conversation JSON generation using Perplexity AI"""
    
    def __init__(self, parent, selected_chapters: List[Dict], current_story: Dict = None):
        super().__init__(parent)
        self.selected_chapters = selected_chapters
        self.current_story = current_story
        self.is_processing = False
        self.current_worker = None
        self.current_chapter_index = 0
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('🔮 Tạo JSON Hội Thoại Tuần Tự (Perplexity)')
        self.setModal(True)
        self.resize(700, 500)
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel(f'<h3>Chương đã chọn: {len(self.selected_chapters)}</h3>')
        layout.addWidget(header)
        
        # Chapter list
        list_widget = QListWidget()
        for chapter in self.selected_chapters:
            item_text = f"Chương {chapter['chapter_number']}: {chapter['title']}"
            list_widget.addItem(item_text)
        layout.addWidget(list_widget)
        
        # Progress bar
        self.progress_label = QLabel('Sẵn sàng bắt đầu')
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(len(self.selected_chapters))
        layout.addWidget(self.progress_bar)
        
        # Status text
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        layout.addWidget(self.status_text)
        
        # Warning
        warning = QLabel('''
<b>⚠️ Lưu ý:</b><br>
• Quá trình này sẽ tạo JSON conversation tuần tự cho tất cả chương đã chọn<br>
• Perplexity AI sẽ được sử dụng để tạo hội thoại tự động<br>
• JSON sẽ được lưu vào thư mục audio_downloads/<story_name>/conversations/<br>
• Bạn cần đăng nhập Perplexity.ai (lần đầu)<br>
• Quá trình có thể mất nhiều thời gian
        ''')
        warning.setWordWrap(True)
        warning.setStyleSheet('background-color: #e7d4f7; padding: 10px; border-radius: 5px;')
        layout.addWidget(warning)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.start_button = QPushButton('🚀 Bắt đầu')
        self.start_button.clicked.connect(self.start_batch_processing)
        button_layout.addWidget(self.start_button)
        
        cancel_button = QPushButton('❌ Hủy')
        cancel_button.clicked.connect(self.close)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def start_batch_processing(self):
        """Start processing chapters"""
        self.is_processing = True
        self.start_button.setEnabled(False)
        self.progress_label.setText('Đang xử lý...')
        self.status_text.append('🚀 Bắt đầu tạo JSON conversation với Perplexity...\n')
        
        self.current_chapter_index = 0
        self.process_next_chapter()
    
    def process_next_chapter(self):
        """Process next chapter in queue"""
        if self.current_chapter_index >= len(self.selected_chapters):
            self.finish_batch_processing()
            return
        
        chapter = self.selected_chapters[self.current_chapter_index]
        
        # Update progress
        self.progress_bar.setValue(self.current_chapter_index)
        self.progress_label.setText(
            f'Đang xử lý chương {self.current_chapter_index + 1}/{len(self.selected_chapters)}'
        )
        self.status_text.append(
            f'\n📝 Chương {chapter["chapter_number"]}: {chapter["title"]}\n'
        )
        
        # Check if chapter has content
        if not chapter.get('content'):
            self.status_text.append(
                f'⚠️ Chương {chapter["chapter_number"]}: Không có nội dung, bỏ qua\n'
            )
            self.current_chapter_index += 1
            QTimer.singleShot(500, self.process_next_chapter)
            return
        
        # Start worker
        self.current_worker = PerplexityConversationGenerationWorker(
            story_id=self.current_story.get('id') if self.current_story else None,
            chapter_id=chapter['id'],
            chapter_title=chapter.get('title', f"Chapter {chapter['id']}"),
            chapter_content=chapter['content'],
            story_name=self.current_story.get('name') if self.current_story else None,
            chapter_number=chapter.get('chapter_number'),
            language=self.current_story.get('language', 'vi') if self.current_story else 'vi'
        )
        self.current_worker.progress.connect(self.on_worker_progress)
        self.current_worker.finished.connect(self.on_worker_finished)
        self.current_worker.start()

    def on_worker_progress(self, message: str):
        self.status_text.append(f'[Chương {self.current_chapter_index + 1}] {message}')

    def on_worker_finished(self, success: bool, message: str, json_path: str = None):
        """Handle worker completion"""
        chapter = self.selected_chapters[self.current_chapter_index]
        status = '✅' if success else '❌'
        
        log_msg = f'{status} Chương {chapter["chapter_number"]}: {message}'
        if json_path and success:
            log_msg += f' ({json_path})'
        self.status_text.append(log_msg + '\n')
        
        # Move to next chapter
        self.current_chapter_index += 1
        QTimer.singleShot(3000, self.process_next_chapter)  # 3 second delay between chapters
    
    def finish_batch_processing(self):
        self.is_processing = False
        self.progress_bar.setValue(len(self.selected_chapters))
        self.progress_label.setText(
            f'✅ Hoàn thành tạo JSON cho {len(self.selected_chapters)} chương!'
        )
        self.start_button.setText('Đóng')
        self.start_button.setEnabled(True)
        self.start_button.clicked.disconnect()
        self.start_button.clicked.connect(self.close)
    
    def closeEvent(self, event):
        if self.is_processing:
            reply = QMessageBox.question(
                self,
                'Xác nhận',
                'Quá trình đang chạy. Bạn có chắc muốn hủy?',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            if self.current_worker:
                self.current_worker.stop()
        event.accept()


class BatchImagePromptGenerationDialog(QDialog):
    """Dialog for batch image prompt generation using Perplexity AI"""
    
    def __init__(self, parent, selected_chapters: List[Dict], current_story: Dict = None):
        super().__init__(parent)
        self.selected_chapters = selected_chapters
        self.current_story = current_story
        self.is_processing = False
        self.current_worker = None
        self.current_chapter_index = 0
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('🎨 Tạo Image Prompts Tuần Tự (Perplexity)')
        self.setModal(True)
        self.resize(700, 500)
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel(f'<h3>Chương đã chọn: {len(self.selected_chapters)}</h3>')
        layout.addWidget(header)
        
        # Chapter list
        list_widget = QListWidget()
        for chapter in self.selected_chapters:
            item_text = f"Chương {chapter['chapter_number']}: {chapter['title']}"
            list_widget.addItem(item_text)
        layout.addWidget(list_widget)
        
        # Progress bar
        self.progress_label = QLabel('Sẵn sàng bắt đầu')
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(len(self.selected_chapters))
        layout.addWidget(self.progress_bar)
        
        # Status text
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        layout.addWidget(self.status_text)
        
        # Warning
        warning = QLabel('''
<b>⚠️ Lưu ý:</b><br>
• Quá trình này sẽ tạo image prompts tuần tự cho tất cả chương đã chọn<br>
• Perplexity AI sẽ được sử dụng để tạo prompts cho từng cảnh<br>
• JSON sẽ được lưu vào thư mục audio_downloads/<story_name>/image_prompts/<br>
• Bạn cần đăng nhập Perplexity.ai (lần đầu)<br>
• Image prompts sẽ được dùng với Runware API để tạo hình ảnh<br>
• Quá trình có thể mất nhiều thời gian
        ''')
        warning.setWordWrap(True)
        warning.setStyleSheet('background-color: #ffe7e7; padding: 10px; border-radius: 5px;')
        layout.addWidget(warning)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.start_button = QPushButton('🚀 Bắt đầu')
        self.start_button.clicked.connect(self.start_batch_processing)
        button_layout.addWidget(self.start_button)
        
        cancel_button = QPushButton('❌ Hủy')
        cancel_button.clicked.connect(self.close)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def start_batch_processing(self):
        """Start processing chapters"""
        self.is_processing = True
        self.start_button.setEnabled(False)
        self.progress_label.setText('Đang xử lý...')
        self.status_text.append('🚀 Bắt đầu tạo image prompts với Perplexity...\n')
        
        self.current_chapter_index = 0
        self.process_next_chapter()
    
    def process_next_chapter(self):
        """Process next chapter in queue"""
        if self.current_chapter_index >= len(self.selected_chapters):
            self.finish_batch_processing()
            return
        
        chapter = self.selected_chapters[self.current_chapter_index]
        
        # Update progress
        self.progress_bar.setValue(self.current_chapter_index)
        self.progress_label.setText(
            f'Đang xử lý chương {self.current_chapter_index + 1}/{len(self.selected_chapters)}'
        )
        self.status_text.append(
            f'\n🎨 Chương {chapter["chapter_number"]}: {chapter["title"]}\n'
        )
        
        # Check if chapter has content
        if not chapter.get('content'):
            self.status_text.append(
                f'⚠️ Chương {chapter["chapter_number"]}: Không có nội dung, bỏ qua\n'
            )
            self.current_chapter_index += 1
            QTimer.singleShot(500, self.process_next_chapter)
            return
        
        # Start worker
        self.current_worker = ImagePromptGenerationWorker(
            story_id=self.current_story.get('id') if self.current_story else None,
            chapter_id=chapter['id'],
            chapter_title=chapter.get('title', f"Chapter {chapter['id']}"),
            chapter_content=chapter['content'],
            story_name=self.current_story.get('name') if self.current_story else None,
            chapter_number=chapter.get('chapter_number'),
            language=self.current_story.get('language', 'vi') if self.current_story else 'vi'
        )
        self.current_worker.progress.connect(self.on_worker_progress)
        self.current_worker.finished.connect(self.on_worker_finished)
        self.current_worker.start()

    def on_worker_progress(self, message: str):
        self.status_text.append(f'[Chương {self.current_chapter_index + 1}] {message}')

    def on_worker_finished(self, success: bool, message: str, json_path: str = None):
        """Handle worker completion"""
        chapter = self.selected_chapters[self.current_chapter_index]
        status = '✅' if success else '❌'
        
        log_msg = f'{status} Chương {chapter["chapter_number"]}: {message}'
        if json_path and success:
            log_msg += f' ({json_path})'
        self.status_text.append(log_msg + '\n')
        
        # Move to next chapter
        self.current_chapter_index += 1
        QTimer.singleShot(3000, self.process_next_chapter)  # 3 second delay between chapters
    
    def finish_batch_processing(self):
        self.is_processing = False
        self.progress_bar.setValue(len(self.selected_chapters))
        self.progress_label.setText(
            f'✅ Hoàn thành tạo image prompts cho {len(self.selected_chapters)} chương!'
        )
        self.start_button.setText('Đóng')
        self.start_button.setEnabled(True)
        self.start_button.clicked.disconnect()
        self.start_button.clicked.connect(self.close)
    
    def closeEvent(self, event):
        if self.is_processing:
            reply = QMessageBox.question(
                self,
                'Xác nhận',
                'Quá trình đang chạy. Bạn có chắc muốn hủy?',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            if self.current_worker:
                self.current_worker.stop()
        event.accept()


class BatchRunwareImageGenerationDialog(QDialog):
    """Dialog for batch image generation using Runware API"""
    
    def __init__(self, parent, selected_chapters: List[Dict], current_story: Dict = None):
        super().__init__(parent)
        self.selected_chapters = selected_chapters
        self.current_story = current_story
        self.is_processing = False
        self.current_worker = None
        self.current_chapter_index = 0
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('🖼️ Tạo Hình Ảnh Tuần Tự (Runware API)')
        self.setModal(True)
        self.resize(700, 550)
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel(f'<h3>Chương đã chọn: {len(self.selected_chapters)}</h3>')
        layout.addWidget(header)
        
        # Chapter list
        list_widget = QListWidget()
        for chapter in self.selected_chapters:
            list_widget.addItem(f"Chương {chapter['chapter_number']}: {chapter['title']}")
        layout.addWidget(list_widget)
        
        # Progress bar
        self.progress_label = QLabel('Sẵn sàng bắt đầu')
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(len(self.selected_chapters))
        layout.addWidget(self.progress_bar)
        
        # Status text
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        layout.addWidget(self.status_text)
        
        # Warning
        warning = QLabel('''
<b>⚠️ Lưu ý:</b><br>
• Quá trình này sẽ tạo hình ảnh tuần tự cho tất cả chương đã chọn<br>
• Runware API sẽ được sử dụng để tạo hình ảnh từ prompts<br>
• Nếu chưa có file JSON prompts, hệ thống sẽ tự động tạo qua Perplexity AI<br>
• Sử dụng nội dung chapter trực tiếp (không dùng conversation JSON)<br>
• Hình ảnh sẽ được lưu trong thư mục audio_downloads/<story_name>/images/<br>
• Cần có RUNWARE_API_KEY trong config<br>
• Quá trình có thể mất nhiều thời gian (3-10 phút/chương)
        ''')
        warning.setWordWrap(True)
        warning.setStyleSheet('background-color: #d4edda; padding: 10px; border-radius: 5px;')
        layout.addWidget(warning)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.start_button = QPushButton('🚀 Bắt đầu')
        self.start_button.clicked.connect(self.start_batch_processing)
        button_layout.addWidget(self.start_button)
        
        cancel_button = QPushButton('❌ Hủy')
        cancel_button.clicked.connect(self.close)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def start_batch_processing(self):
        """Start processing chapters"""
        self.is_processing = True
        self.start_button.setEnabled(False)
        self.progress_label.setText('Đang xử lý...')
        self.status_text.append('🚀 Bắt đầu tạo hình ảnh với Runware API...\n')
        
        self.current_chapter_index = 0
        self.process_next_chapter()
    
    def process_next_chapter(self):
        """Process next chapter in queue"""
        if self.current_chapter_index >= len(self.selected_chapters):
            self.finish_batch_processing()
            return
        
        chapter = self.selected_chapters[self.current_chapter_index]
        
        # Update progress
        self.progress_bar.setValue(self.current_chapter_index)
        self.progress_label.setText(
            f'Đang xử lý chương {self.current_chapter_index + 1}/{len(self.selected_chapters)}'
        )
        self.status_text.append(
            f'\n🖼️ Chương {chapter["chapter_number"]}: {chapter["title"]}\n'
        )
        
        # Check if chapter has content
        if not chapter.get('content'):
            self.status_text.append('❌ Chương không có nội dung, bỏ qua\n')
            self.current_chapter_index += 1
            QTimer.singleShot(1000, self.process_next_chapter)
            return
        
        # Start worker
        self.current_worker = RunwareImageGenerationWorker(
            story_id=self.current_story.get('id') if self.current_story else None,
            chapter_id=chapter['id'],
            chapter_title=chapter.get('title', f"Chapter {chapter['id']}"),
            chapter_content=chapter['content'],
            story_name=self.current_story.get('name') if self.current_story else None,
            chapter_number=chapter.get('chapter_number'),
            language=self.current_story.get('language', 'vi') if self.current_story else 'vi'
        )
        self.current_worker.progress.connect(self.on_worker_progress)
        self.current_worker.finished.connect(self.on_worker_finished)
        self.current_worker.start()

    def on_worker_progress(self, message: str):
        self.status_text.append(f'[Chương {self.current_chapter_index + 1}] {message}')

    def on_worker_finished(self, success: bool, message: str, output_dir: str = None):
        """Handle worker completion"""
        chapter = self.selected_chapters[self.current_chapter_index]
        status = '✅' if success else '❌'
        
        log_msg = f'{status} Chương {chapter["chapter_number"]}: {message}'
        if output_dir and success:
            log_msg += f'\n    📁 {output_dir}'
        self.status_text.append(log_msg + '\n')
        
        # Move to next chapter
        self.current_chapter_index += 1
        QTimer.singleShot(3000, self.process_next_chapter)  # 3 second delay between chapters
    
    def finish_batch_processing(self):
        self.is_processing = False
        self.progress_bar.setValue(len(self.selected_chapters))
        self.progress_label.setText(
            f'✅ Hoàn thành tạo hình ảnh cho {len(self.selected_chapters)} chương!'
        )
        self.start_button.setText('Đóng')
        self.start_button.setEnabled(True)
        self.start_button.clicked.disconnect()
        self.start_button.clicked.connect(self.close)
    
    def closeEvent(self, event):
        if self.is_processing:
            reply = QMessageBox.question(
                self,
                'Xác nhận',
                'Quá trình đang chạy. Bạn có chắc muốn hủy?',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            if self.current_worker:
                self.current_worker.stop()
        event.accept()


class BatchSRTGenerationDialog(QDialog):
    """Dialog for batch SRT subtitle generation using Whisper"""

    def __init__(self, parent, selected_chapters: List[Dict], current_story: Dict = None):
        super().__init__(parent)
        self.selected_chapters = selected_chapters
        self.current_story = current_story
        self.is_processing = False
        self.current_worker = None
        self.current_chapter_index = 0

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('🎤 Tạo SRT Subtitles Tuần Tự (Whisper)')
        self.setModal(True)
        self.resize(700, 550)

        layout = QVBoxLayout()

        # Header
        header = QLabel(f'<h3>Chương đã chọn: {len(self.selected_chapters)}</h3>')
        layout.addWidget(header)

        # Chapter list
        list_widget = QListWidget()
        for chapter in self.selected_chapters:
            list_widget.addItem(f"Chương {chapter['chapter_number']}: {chapter['title']}")
        layout.addWidget(list_widget)

        # Progress bar
        self.progress_label = QLabel('Sẵn sàng bắt đầu')
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(len(self.selected_chapters))
        layout.addWidget(self.progress_bar)

        # Status text
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        layout.addWidget(self.status_text)

        # Warning
        warning = QLabel('''
<b>⚠️ Lưu ý:</b><br>
• Quá trình này sẽ tạo file SRT subtitles cho tất cả chương đã chọn<br>
• Sử dụng OpenAI Whisper model "medium" để transcribe audio<br>
• Cần có file audio (.wav hoặc .mp3) cho mỗi chương<br>
• File SRT sẽ được lưu trong thư mục subtitles/<br>
• Quá trình có thể mất 1-3 phút cho mỗi chương<br>
• Nếu file SRT đã tồn tại, sẽ được ghi đè
        ''')
        warning.setWordWrap(True)
        warning.setStyleSheet('background-color: #fff3cd; padding: 10px; border-radius: 5px;')
        layout.addWidget(warning)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.start_button = QPushButton('🚀 Bắt đầu')
        self.start_button.clicked.connect(self.start_batch_processing)
        button_layout.addWidget(self.start_button)

        cancel_button = QPushButton('❌ Hủy')
        cancel_button.clicked.connect(self.close)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def start_batch_processing(self):
        """Start processing chapters"""
        self.is_processing = True
        self.start_button.setEnabled(False)
        self.progress_label.setText('Đang xử lý...')
        self.status_text.append('🚀 Bắt đầu tạo SRT subtitles với Whisper...\n')

        self.current_chapter_index = 0
        self.process_next_chapter()

    def process_next_chapter(self):
        """Process next chapter in queue"""
        if self.current_chapter_index >= len(self.selected_chapters):
            self.finish_batch_processing()
            return

        chapter = self.selected_chapters[self.current_chapter_index]

        # Update progress
        self.progress_bar.setValue(self.current_chapter_index)
        self.progress_label.setText(
            f'Đang xử lý chương {self.current_chapter_index + 1}/{len(self.selected_chapters)}'
        )
        self.status_text.append(
            f'\n🎤 Chương {chapter["chapter_number"]}: {chapter["title"]}\n'
        )

        # Start worker
        self.current_worker = WhisperSRTWorker(
            story_id=self.current_story.get('id') if self.current_story else None,
            chapter_id=chapter['id'],
            chapter_number=chapter.get('chapter_number'),
            story_name=self.current_story.get('name') if self.current_story else None,
            language=self.current_story.get('language', 'vi') if self.current_story else 'vi'
        )
        self.current_worker.progress.connect(self.on_worker_progress)
        self.current_worker.finished.connect(self.on_worker_finished)
        self.current_worker.start()

    def on_worker_progress(self, message: str):
        self.status_text.append(f'[Chương {self.current_chapter_index + 1}] {message}')

    def on_worker_finished(self, success: bool, message: str, srt_path: str = None):
        """Handle worker completion"""
        chapter = self.selected_chapters[self.current_chapter_index]
        status = '✅' if success else '❌'

        log_msg = f'{status} Chương {chapter["chapter_number"]}: {message}'
        if srt_path and success:
            log_msg += f'\n    📁 {srt_path}'
        self.status_text.append(log_msg + '\n')

        # Move to next chapter
        self.current_chapter_index += 1
        QTimer.singleShot(2000, self.process_next_chapter)  # 2 second delay between chapters

    def finish_batch_processing(self):
        self.is_processing = False
        self.progress_bar.setValue(len(self.selected_chapters))
        self.progress_label.setText(
            f'✅ Hoàn thành tạo SRT cho {len(self.selected_chapters)} chương!'
        )
        self.start_button.setText('Đóng')
        self.start_button.setEnabled(True)
        self.start_button.clicked.disconnect()
        self.start_button.clicked.connect(self.close)

    def closeEvent(self, event):
        if self.is_processing:
            reply = QMessageBox.question(
                self,
                'Xác nhận',
                'Quá trình đang chạy. Bạn có chắc muốn hủy?',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            if self.current_worker:
                self.current_worker.stop()
        event.accept()


class ChapterWidget(QFrame):
    """Widget for displaying a single chapter"""
    
    audio_generated = pyqtSignal()
    
    def __init__(self, chapter: Dict, db_service: DatabaseService, current_story: Dict = None):
        super().__init__()
        self.chapter = chapter
        self.db_service = db_service
        self.current_story = current_story
        self.worker = None
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Header with checkbox and title
        header_layout = QHBoxLayout()
        
        self.checkbox = QCheckBox()
        header_layout.addWidget(self.checkbox)
        
        chapter_badge = QLabel(f'Chương {self.chapter["chapter_number"]}')
        chapter_badge.setStyleSheet(
            'background-color: #007bff; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;'
        )
        header_layout.addWidget(chapter_badge)
        
        title_label = QLabel(self.chapter['title'])
        title_label.setFont(QFont('Arial', 10, QFont.Bold))
        header_layout.addWidget(title_label, 1)
        
        if self.chapter.get('audio_url'):
            audio_badge = QLabel('🎵 Có audio')
            audio_badge.setStyleSheet(
                'background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px;'
            )
            header_layout.addWidget(audio_badge)
        
        layout.addLayout(header_layout)
        
        # Buttons
        button_layout = QHBoxLayout()

        # Voice selection combobox
        voice_layout = QHBoxLayout()
        voice_label = QLabel('Giọng đọc:')
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(['Nam', 'Nữ'])
        self.voice_combo.setCurrentIndex(0)  # Default: Nam
        voice_layout.addWidget(voice_label)
        voice_layout.addWidget(self.voice_combo)
        button_layout.addLayout(voice_layout)

        # Channel Intro selection combobox
        from channel_intro_manager import ChannelIntroManager
        intro_layout = QHBoxLayout()
        intro_label = QLabel('Channel Intro:')
        self.intro_combo = QComboBox()
        self.intro_manager = ChannelIntroManager()
        self.intro_combo.addItems(self.intro_manager.get_intro_names())
        self.intro_combo.setCurrentIndex(1)  # Default: First intro
        intro_layout.addWidget(intro_label)
        intro_layout.addWidget(self.intro_combo)
        button_layout.addLayout(intro_layout)

        # Selenium Button
        self.selenium_button = QPushButton('🤖 Tạo Audio ' if not self.chapter.get('audio_url') else '🔄 Tạo Audio Lại')
        self.selenium_button.clicked.connect(lambda: self.generate_audio('selenium'))
        button_layout.addWidget(self.selenium_button)
        
        
        # JSON Conversation Button (Perplexity)
        self.perplexity_json_button = QPushButton('🔮 Biên tập lại hội thoại (Perplexity)')
        self.perplexity_json_button.clicked.connect(self.generate_conversation_json_perplexity)
        self.perplexity_json_button.setStyleSheet('background-color: #6f42c1; color: white;')
        button_layout.addWidget(self.perplexity_json_button)
        
        # View Content Button
        view_button = QPushButton('📄 Xem nội dung')
        view_button.clicked.connect(self.view_content)
        button_layout.addWidget(view_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Status label
        self.status_label = QLabel('')
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(1)
    
    def generate_audio(self, method: str):
        """Generate audio using Selenium (local)

        NOTE: TTS method is deprecated. Only Selenium is supported now.
        """
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, 'Cảnh báo', 'Đang xử lý, vui lòng đợi...')
            return

        # Validate chapter has content
        if not self.chapter.get('content'):
            QMessageBox.warning(
                self,
                'Cảnh báo',
                'Chương không có nội dung để tạo audio!'
            )
            return

        # Get selected voice gender
        voice_gender = 'male' if self.voice_combo.currentText() == 'Nam' else 'female'

        # Get selected channel intro
        intro_name = self.intro_combo.currentText()
        channel_intro = self.intro_manager.get_intro_by_name(intro_name) or ""

        # Disable buttons
        # self.tts_button.setEnabled(False)  # TTS button is disabled
        self.selenium_button.setEnabled(False)
        self.perplexity_json_button.setEnabled(False)

        # Create new Selenium worker
        self.worker = SeleniumAudioWorker(
            db_service=self.db_service,
            chapter_id=self.chapter['id'],
            chapter_title=self.chapter.get('title', f"Chapter {self.chapter['id']}"),
            chapter_content=self.chapter['content'],
            has_existing_audio=bool(self.chapter.get('audio_url')),
            story_id=self.current_story.get('id') if self.current_story else None,
            story_name=self.current_story.get('name') if self.current_story else None,
            chapter_number=self.chapter.get('chapter_number'),
            voice_gender=voice_gender,
            channel_intro=channel_intro,
            language=self.current_story.get('language', 'vi') if self.current_story else 'vi'
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
    
    def generate_conversation_json(self):
        """Generate conversation JSON using Grok AI"""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, 'Cảnh báo', 'Đang xử lý, vui lòng đợi...')
            return
        
        # Validate chapter has content
        if not self.chapter.get('content'):
            QMessageBox.warning(
                self, 
                'Cảnh báo', 
                'Chương không có nội dung để tạo conversation!'
            )
            return
        
        # Confirm with user
        reply = QMessageBox.question(
            self,
            'Xác nhận',
            f'Tạo JSON hội thoại cho chương {self.chapter["chapter_number"]}?\n'
            f'Tên: {self.chapter["title"]}\n\n'
            f'Grok AI sẽ được sử dụng để tạo hội thoại dựa trên nội dung chương.',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        # Disable buttons
        self.selenium_button.setEnabled(False)
        
        # Create conversation worker
        self.worker = ConversationGenerationWorker(
            story_id=self.current_story.get('id') if self.current_story else self.chapter.get('story_id'),
            chapter_id=self.chapter['id'],
            chapter_title=self.chapter.get('title', f"Chapter {self.chapter['id']}"),
            chapter_content=self.chapter['content'],
            story_name=self.current_story.get('name') if self.current_story else None,
            chapter_number=self.chapter.get('chapter_number'),
            language=self.current_story.get('language', 'vi') if self.current_story else 'vi'
        )
        self.worker.progress.connect(self.on_conversation_progress)
        self.worker.finished.connect(self.on_conversation_finished)
        self.worker.start()
    
    def generate_conversation_json_perplexity(self):
        """Generate conversation JSON using Perplexity AI"""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, 'Cảnh báo', 'Đang xử lý, vui lòng đợi...')
            return
        
        # Validate chapter has content
        if not self.chapter.get('content'):
            QMessageBox.warning(
                self, 
                'Cảnh báo', 
                'Chương không có nội dung để tạo conversation!'
            )
            return
        
        # Confirm with user
        reply = QMessageBox.question(
            self,
            'Xác nhận',
            f'Tạo JSON hội thoại cho chương {self.chapter["chapter_number"]}?\n'
            f'Tên: {self.chapter["title"]}\n\n'
            f'Perplexity AI sẽ được sử dụng để tạo hội thoại dựa trên nội dung chương.',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        # Disable buttons
        self.selenium_button.setEnabled(False)
        self.perplexity_json_button.setEnabled(False)
        
        # Create conversation worker
        self.worker = PerplexityConversationGenerationWorker(
            story_id=self.current_story.get('id') if self.current_story else self.chapter.get('story_id'),
            chapter_id=self.chapter['id'],
            chapter_title=self.chapter.get('title', f"Chapter {self.chapter['id']}"),
            chapter_content=self.chapter['content'],
            story_name=self.current_story.get('name') if self.current_story else None,
            chapter_number=self.chapter.get('chapter_number'),
            language=self.current_story.get('language', 'vi') if self.current_story else 'vi'
        )
        self.worker.progress.connect(self.on_perplexity_conversation_progress)
        self.worker.finished.connect(self.on_perplexity_conversation_finished)
        self.worker.start()
    
    def on_perplexity_conversation_progress(self, message: str):
        """Handle Perplexity conversation generation progress"""
        self.status_label.setText(f'🔮 {message}')
        self.status_label.setStyleSheet('color: #6f42c1;')
    
    def on_perplexity_conversation_finished(self, success: bool, message: str, json_path: str = None):
        """Handle Perplexity conversation generation completion"""
        self.selenium_button.setEnabled(True)
        self.perplexity_json_button.setEnabled(True)
        
        if success:
            self.status_label.setText(f'✅ {message}')
            self.status_label.setStyleSheet('color: #28a745;')
            
            if json_path:
                # Show success message
                QMessageBox.information(
                    self, 
                    'Thành công!',
                    f'✓ Tạo JSON conversation (Perplexity) thành công!\n\n'
                    f'📁 Đã lưu tại:\n{json_path}',
                    QMessageBox.Ok
                )
        else:
            self.status_label.setText(f'❌ {message}')
            self.status_label.setStyleSheet('color: #dc3545;')
    
    def on_conversation_progress(self, message: str):
        """Handle conversation generation progress"""
        self.status_label.setText(f'💬 {message}')
        self.status_label.setStyleSheet('color: #17a2b8;')
    
    def on_conversation_finished(self, success: bool, message: str, json_path: str = None):
        """Handle conversation generation completion"""
        self.selenium_button.setEnabled(True)
        self.perplexity_json_button.setEnabled(True)
        
        if success:
            self.status_label.setText(f'✅ {message}')
            self.status_label.setStyleSheet('color: #28a745;')
            
            if json_path:
                # Show success message
                QMessageBox.information(
                    self, 
                    'Thành công!',
                    f'✓ Tạo JSON conversation thành công!\n\n'
                    f'📁 Đã lưu tại:\n{json_path}',
                    QMessageBox.Ok
                )
        else:
            self.status_label.setText(f'❌ {message}')
            self.status_label.setStyleSheet('color: #dc3545;')
    
    def on_progress(self, message: str):
        self.status_label.setText(f'⏳ {message}')
        self.status_label.setStyleSheet('color: #0066cc;')
    
    def on_finished(self, success: bool, message: str, audio_path: str = None):
        """Handle worker completion
        
        Args:
            success: Whether generation succeeded
            message: Status message
            audio_path: Path to generated audio file (if successful)
        """
        # self.tts_button.setEnabled(True)  # TTS button is disabled
        self.selenium_button.setEnabled(True)
        self.perplexity_json_button.setEnabled(True)
        
        if success:
            self.status_label.setText(f'✅ {message}')
            self.status_label.setStyleSheet('color: #28a745;')
            
            # Refresh chapter data and emit signal
            self.audio_generated.emit()
        else:
            self.status_label.setText(f'❌ {message}')
            self.status_label.setStyleSheet('color: #dc3545;')
    
    def view_content(self):
        """View chapter content"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f'Chương {self.chapter["chapter_number"]}: {self.chapter["title"]}')
        dialog.resize(700, 500)
        
        layout = QVBoxLayout()
        
        content_text = QTextEdit()
        content_text.setPlainText(self.chapter['content'])
        content_text.setReadOnly(True)
        layout.addWidget(content_text)
        
        close_button = QPushButton('Đóng')
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)
        
        dialog.setLayout(layout)
        dialog.exec_()


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.db_service = DatabaseService()
        self.current_story = None
        self.chapters_data = None
        self.current_page = 1
        self.chapter_widgets: List[ChapterWidget] = []
        
        self.init_ui()
        
        # Login not needed with local database

        
        # self.show_login_dialog()

        
        self.load_stories()  # Load stories immediately
    
    def init_ui(self):
        self.setWindowTitle('🎵 Audio Generator - Desktop App')
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Create menu bar
        menubar = self.menuBar()
        
        # Account menu
        account_menu = menubar.addMenu('👤 Tài Khoản')
        
        # Logout not needed with local database

        
        # logout_action = account_menu.addAction(\'🚪 Đăng Xuất\')

        
        # logout_action.triggered.connect(self.logout)
        
        exit_action = account_menu.addAction('❌ Thoát')
        exit_action.triggered.connect(self.close)
        
        # Profile menu
        profile_menu = menubar.addMenu('🌐 Chrome Profiles')
        
        manage_profiles_action = profile_menu.addAction('⚙️ Quản Lý Profiles')
        manage_profiles_action.triggered.connect(self.show_profile_manager)
        
        # Proxy menu
        proxy_menu = menubar.addMenu('🌐 Proxy')
        
        manage_proxy_action = proxy_menu.addAction('⚙️ Quản Lý Proxy')
        manage_proxy_action.triggered.connect(self.show_proxy_manager)
        
        # Settings menu
        settings_menu = menubar.addMenu('⚙️ Cài Đặt')

        manage_settings_action = settings_menu.addAction('🔧 Quản Lý Cài Đặt')
        manage_settings_action.triggered.connect(self.show_settings_manager)

        manage_channel_intro_action = settings_menu.addAction('🎙️ Quản Lý Channel Intro')
        manage_channel_intro_action.triggered.connect(self.show_channel_intro_manager)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        
        # Left panel - Story list
        left_panel = QGroupBox('📚 Danh sách truyện')
        left_layout = QVBoxLayout()
        
        self.story_list = QListWidget()
        self.story_list.itemClicked.connect(self.on_story_selected)
        left_layout.addWidget(self.story_list)
        
        refresh_button = QPushButton('🔄 Làm mới')
        refresh_button.clicked.connect(self.load_stories)
        left_layout.addWidget(refresh_button)
        
        # Story management buttons
        add_story_button = QPushButton('➕ Thêm truyện')
        add_story_button.clicked.connect(self.add_story)
        left_layout.addWidget(add_story_button)
        
        edit_story_button = QPushButton('✏️ Sửa truyện')
        edit_story_button.clicked.connect(self.edit_story)
        left_layout.addWidget(edit_story_button)
        
        delete_story_button = QPushButton('🗑️ Xóa truyện')
        delete_story_button.clicked.connect(self.delete_story)
        left_layout.addWidget(delete_story_button)
        
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(350)
        
        # Right panel - Chapter list
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # Story info
        self.story_info_label = QLabel('Chọn một truyện để xem chi tiết')
        self.story_info_label.setFont(QFont('Arial', 12, QFont.Bold))
        right_layout.addWidget(self.story_info_label)
        
        # Chapter management buttons
        chapter_mgmt_layout = QHBoxLayout()
        
        add_chapter_button = QPushButton('➕ Thêm chương')
        add_chapter_button.clicked.connect(self.add_chapter)
        self.add_chapter_button = add_chapter_button
        self.add_chapter_button.setEnabled(False)
        chapter_mgmt_layout.addWidget(add_chapter_button)
        
        edit_chapter_button = QPushButton('✏️ Sửa chương')
        edit_chapter_button.clicked.connect(self.edit_selected_chapter)
        self.edit_chapter_button = edit_chapter_button
        self.edit_chapter_button.setEnabled(False)
        chapter_mgmt_layout.addWidget(edit_chapter_button)
        
        delete_chapter_button = QPushButton('🗑️ Xóa chương')
        delete_chapter_button.clicked.connect(self.delete_selected_chapter)
        self.delete_chapter_button = delete_chapter_button
        self.delete_chapter_button.setEnabled(False)
        chapter_mgmt_layout.addWidget(delete_chapter_button)
        
        right_layout.addLayout(chapter_mgmt_layout)
        
        # Batch controls
        batch_controls = QHBoxLayout()
        
        self.select_all_button = QPushButton('📋 Chọn tất cả')
        self.select_all_button.clicked.connect(self.select_all_chapters)
        self.select_all_button.setEnabled(False)
        batch_controls.addWidget(self.select_all_button)
        
        self.batch_generate_button = QPushButton('🤖 Tạo audio tuần tự (0)')
        self.batch_generate_button.clicked.connect(self.batch_generate_audio)
        self.batch_generate_button.setEnabled(False)
        batch_controls.addWidget(self.batch_generate_button)
        
        self.batch_conversation_button = QPushButton('💬 JSON tuần tự Grok (0)')
        self.batch_conversation_button.clicked.connect(self.batch_generate_conversations)
        self.batch_conversation_button.setEnabled(False)
        self.batch_conversation_button.setStyleSheet('background-color: #17a2b8; color: white;')
        batch_controls.addWidget(self.batch_conversation_button)
        
        self.batch_perplexity_button = QPushButton('🔮 JSON tuần tự Perplexity (0)')
        self.batch_perplexity_button.clicked.connect(self.batch_generate_perplexity_conversations)
        self.batch_perplexity_button.setEnabled(False)
        self.batch_perplexity_button.setStyleSheet('background-color: #6f42c1; color: white;')
        batch_controls.addWidget(self.batch_perplexity_button)
        
        self.batch_image_prompt_button = QPushButton('🎨 Image Prompts tuần tự (0)')
        self.batch_image_prompt_button.clicked.connect(self.batch_generate_image_prompts)
        self.batch_image_prompt_button.setEnabled(False)
        self.batch_image_prompt_button.setStyleSheet('background-color: #ff6b6b; color: white;')
        batch_controls.addWidget(self.batch_image_prompt_button)
        
        self.batch_runware_button = QPushButton('🖼️ Tạo Images tuần tự (0)')
        self.batch_runware_button.clicked.connect(self.batch_generate_runware_images)
        self.batch_runware_button.setEnabled(False)
        self.batch_runware_button.setStyleSheet('background-color: #28a745; color: white;')
        batch_controls.addWidget(self.batch_runware_button)

        self.batch_srt_button = QPushButton('🎤 Tạo SRT tuần tự (0)')
        self.batch_srt_button.clicked.connect(self.batch_generate_srt)
        self.batch_srt_button.setEnabled(False)
        self.batch_srt_button.setStyleSheet('background-color: #fd7e14; color: white;')
        batch_controls.addWidget(self.batch_srt_button)

        batch_controls.addStretch()
        right_layout.addLayout(batch_controls)
        
        # Chapter list (scrollable)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.chapter_container = QWidget()
        self.chapter_layout = QVBoxLayout()
        self.chapter_layout.addStretch()
        self.chapter_container.setLayout(self.chapter_layout)
        
        scroll_area.setWidget(self.chapter_container)
        right_layout.addWidget(scroll_area)
        
        # Pagination
        pagination_layout = QHBoxLayout()
        
        self.prev_button = QPushButton('◀ Trước')
        self.prev_button.clicked.connect(lambda: self.change_page(self.current_page - 1))
        self.prev_button.setEnabled(False)
        pagination_layout.addWidget(self.prev_button)
        
        self.page_label = QLabel('Trang 1')
        self.page_label.setAlignment(Qt.AlignCenter)
        pagination_layout.addWidget(self.page_label)
        
        self.next_button = QPushButton('Sau ▶')
        self.next_button.clicked.connect(lambda: self.change_page(self.current_page + 1))
        self.next_button.setEnabled(False)
        pagination_layout.addWidget(self.next_button)
        
        right_layout.addLayout(pagination_layout)
        
        right_panel.setLayout(right_layout)
        
        # Add panels to main layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        
        # Status bar
        self.statusBar().showMessage('Sẵn sàng')
    
    def show_login_dialog(self):

    
        """DEPRECATED: Not needed with local database"""

    
        return  # No-op
        """Show login dialog and handle authentication"""
        login_dialog = LoginDialog(self.db_service, self)
        login_dialog.login_successful.connect(self.on_login_successful)
        
        result = login_dialog.exec_()
        
        if result == QDialog.Accepted:
            pass
        else:
            logger.warning("Login cancelled or failed, closing application")
            QMessageBox.warning(
                self,
                'Yêu Cầu Đăng Nhập',
                'Bạn cần đăng nhập để sử dụng ứng dụng.'
            )
            self.close()
    
    def on_login_successful(self, user_data: Dict):
        """Handle successful login"""
        self.statusBar().showMessage(f"Đã đăng nhập: {user_data.get('username', 'User')}")
        self.load_stories()
    
    def load_stories(self):
        """Load list of stories"""
        try:
            self.statusBar().showMessage('Đang tải danh sách truyện...')
            stories = self.db_service.get_stories()

            self.story_list.clear()
            for story in stories:
                # Get language display
                lang_code = story.get('language', 'vi')
                lang_name = config.get_language_name(lang_code)

                # Display format: 📖 Story Name - Author [Language]
                author_part = f" - {story['author']}" if story.get('author') else ""
                item = QListWidgetItem(f"📖 {story['name']}{author_part} [{lang_name}]")
                item.setData(Qt.UserRole, story)
                self.story_list.addItem(item)

            self.statusBar().showMessage(f'Đã tải {len(stories)} truyện')
        except Exception as e:
            QMessageBox.critical(self, 'Lỗi', f'Không thể tải danh sách truyện:\n{str(e)}')
            self.statusBar().showMessage('Lỗi khi tải truyện')
    
    def on_story_selected(self, item: QListWidgetItem):
        """Handle story selection"""
        self.current_story = item.data(Qt.UserRole)
        self.current_page = 1
        self.load_chapters()
    
    def load_chapters(self, story_id: int = None):
        """Load chapters for current story or specified story_id"""
        # If story_id provided, make sure it matches current_story
        if story_id is not None and self.current_story and story_id != self.current_story['id']:
            # Story changed, reload story
            try:
                self.current_story = self.db_service.get_story(story_id)
            except Exception as e:
                logger.error(f"Failed to load story {story_id}: {e}")
                return

        if not self.current_story:
            return
        
        try:
            self.statusBar().showMessage('Đang tải danh sách chương...')
            
            self.chapters_data = self.db_service.get_chapters_by_story(
                self.current_story['id'],
                self.current_page,
                CHAPTERS_PER_PAGE
            )
            
            # Update UI
            lang_code = self.current_story.get('language', 'vi')
            lang_name = config.get_language_name(lang_code)
            author_part = f" - {self.current_story['author']}" if self.current_story.get('author') else ""
            self.story_info_label.setText(
                f"📖 {self.current_story['name']}{author_part}\n"
                f"🌐 Ngôn ngữ: {lang_name} | Tổng số: {self.chapters_data['count']} chương"
            )
            
            # Clear existing chapters
            for widget in self.chapter_widgets:
                self.chapter_layout.removeWidget(widget)
                widget.deleteLater()
            self.chapter_widgets.clear()
            
            # Add chapter widgets
            for chapter in self.chapters_data['results']:
                widget = ChapterWidget(chapter, self.db_service, self.current_story)
                widget.audio_generated.connect(self.on_audio_generated)
                widget.checkbox.stateChanged.connect(self.on_chapter_selection_changed)
                self.chapter_widgets.append(widget)
                self.chapter_layout.insertWidget(self.chapter_layout.count() - 1, widget)
            
            # Update pagination
            total_pages = (self.chapters_data['count'] + CHAPTERS_PER_PAGE - 1) // CHAPTERS_PER_PAGE
            self.page_label.setText(f'Trang {self.current_page}/{total_pages}')
            self.prev_button.setEnabled(self.current_page > 1)
            self.next_button.setEnabled(self.chapters_data.get('next') is not None)
            
            # Enable batch controls
            self.select_all_button.setEnabled(True)

            # Enable add chapter button (can add chapter when story is selected)
            self.add_chapter_button.setEnabled(True)

            # Update chapter management buttons based on selection
            self.on_chapter_selection_changed()

            self.statusBar().showMessage(
                f'Đã tải {len(self.chapters_data["results"])} chương '
                f'(trang {self.current_page}/{total_pages})'
            )
        except Exception as e:
            QMessageBox.critical(self, 'Lỗi', f'Không thể tải danh sách chương:\n{str(e)}')
            self.statusBar().showMessage('Lỗi khi tải chương')
    
    def change_page(self, page: int):
        """Change to different page"""
        self.current_page = page
        self.load_chapters()
    
    def on_audio_generated(self):
        """Handle audio generation completion"""
        # Reload chapters to update audio status
        self.load_chapters()
    
    def select_all_chapters(self):
        """Toggle select all chapters"""
        if not self.chapter_widgets:
            return
        
        # Check if all are selected
        all_selected = all(widget.checkbox.isChecked() for widget in self.chapter_widgets)
        
        # Toggle
        for widget in self.chapter_widgets:
            widget.checkbox.setChecked(not all_selected)
    
    def on_chapter_selection_changed(self):
        """Handle chapter selection change"""
        selected_count = sum(1 for widget in self.chapter_widgets if widget.checkbox.isChecked())

        # Update batch buttons
        self.batch_generate_button.setText(f'🤖 Tạo audio tuần tự ({selected_count})')
        self.batch_generate_button.setEnabled(selected_count > 0)
        self.batch_conversation_button.setText(f'💬 JSON tuần tự Grok ({selected_count})')
        self.batch_conversation_button.setEnabled(selected_count > 0)
        self.batch_perplexity_button.setText(f'🔮 JSON tuần tự Perplexity ({selected_count})')
        self.batch_perplexity_button.setEnabled(selected_count > 0)
        self.batch_image_prompt_button.setText(f'🎨 Image Prompts tuần tự ({selected_count})')
        self.batch_image_prompt_button.setEnabled(selected_count > 0)
        self.batch_runware_button.setText(f'🖼️ Tạo Images tuần tự ({selected_count})')
        self.batch_runware_button.setEnabled(selected_count > 0)
        self.batch_srt_button.setText(f'🎤 Tạo SRT tuần tự ({selected_count})')
        self.batch_srt_button.setEnabled(selected_count > 0)

        # Update chapter management buttons
        # Edit button: only enable when exactly 1 chapter is selected
        self.edit_chapter_button.setEnabled(selected_count == 1)
        # Delete button: enable when at least 1 chapter is selected
        self.delete_chapter_button.setEnabled(selected_count > 0)
    
    def batch_generate_audio(self):
        """Start batch audio generation"""
        selected_chapters = [
            widget.chapter for widget in self.chapter_widgets
            if widget.checkbox.isChecked()
        ]
        
        if not selected_chapters:
            QMessageBox.warning(self, 'Cảnh báo', 'Vui lòng chọn ít nhất một chương')
            return
        
        dialog = BatchAudioGenerationDialog(
            self, 
            self.db_service, 
            selected_chapters,
            current_story=self.current_story
        )
        dialog.exec_()
    
    def batch_generate_conversations(self):
        """Start batch conversation generation"""
        selected_chapters = [
            widget.chapter for widget in self.chapter_widgets
            if widget.checkbox.isChecked()
        ]
        
        if not selected_chapters:
            QMessageBox.warning(self, 'Cảnh báo', 'Vui lòng chọn ít nhất một chương')
            return
        
        dialog = BatchConversationGenerationDialog(
            self,
            selected_chapters,
            current_story=self.current_story
        )
        dialog.exec_()
        # Reload chapters after batch processing
        self.load_chapters()
    
    def batch_generate_perplexity_conversations(self):
        """Start batch Perplexity conversation generation"""
        selected_chapters = [
            widget.chapter for widget in self.chapter_widgets
            if widget.checkbox.isChecked()
        ]
        
        if not selected_chapters:
            QMessageBox.warning(self, 'Cảnh báo', 'Vui lòng chọn ít nhất một chương')
            return
        
        dialog = BatchPerplexityConversationGenerationDialog(
            self,
            selected_chapters,
            current_story=self.current_story
        )
        dialog.exec_()
        # Reload chapters after batch processing
        self.load_chapters()
    
    def batch_generate_image_prompts(self):
        """Start batch image prompt generation"""
        selected_chapters = [
            widget.chapter for widget in self.chapter_widgets
            if widget.checkbox.isChecked()
        ]
        
        if not selected_chapters:
            QMessageBox.warning(self, 'Cảnh báo', 'Vui lòng chọn ít nhất một chương')
            return
        
        dialog = BatchImagePromptGenerationDialog(
            self,
            selected_chapters,
            current_story=self.current_story
        )
        dialog.exec_()
        # Reload chapters after batch processing
        self.load_chapters()
    
    def batch_generate_runware_images(self):
        """Start batch Runware image generation"""
        selected_chapters = [
            widget.chapter for widget in self.chapter_widgets
            if widget.checkbox.isChecked()
        ]
        
        if not selected_chapters:
            QMessageBox.warning(self, 'Cảnh báo', 'Vui lòng chọn ít nhất một chương')
            return
        
        # Check if RUNWARE_API_KEY is configured
        import config
        if not config.RUNWARE_API_KEY:
            QMessageBox.warning(
                self,
                'Thiếu API Key',
                'Vui lòng cấu hình RUNWARE_API_KEY trong file .env hoặc config.py'
            )
            return
        
        dialog = BatchRunwareImageGenerationDialog(
            self,
            selected_chapters,
            current_story=self.current_story
        )
        dialog.exec_()
        # Reload chapters after batch processing
        self.load_chapters()

    def batch_generate_srt(self):
        """Start batch SRT subtitle generation using Whisper"""
        selected_chapters = [
            widget.chapter for widget in self.chapter_widgets
            if widget.checkbox.isChecked()
        ]

        if not selected_chapters:
            QMessageBox.warning(self, 'Cảnh báo', 'Vui lòng chọn ít nhất một chương')
            return

        dialog = BatchSRTGenerationDialog(
            self,
            selected_chapters,
            current_story=self.current_story
        )
        dialog.exec_()
        # Reload chapters after batch processing
        self.load_chapters()

    def logout(self):
        """Handle logout"""
        reply = QMessageBox.question(
            self,
            'Đăng Xuất',
            'Bạn có chắc muốn đăng xuất?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Clear token
            self.db_service.clear_token()
            
            # Clear UI
            self.story_list.clear()
            self.chapter_scroll_layout = QVBoxLayout()
            
            # Show login dialog again
            self.show_login_dialog()
    
    def show_profile_manager(self):
        """Show Chrome profile manager dialog"""
        try:
            dialog = ProfileManagerDialog(self)
            dialog.exec_()
        except Exception as e:
            error_msg = f'Lỗi khi mở quản lý profiles: {str(e)}'
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, 'Lỗi', error_msg)
    
    def show_proxy_manager(self):
        """Show proxy manager dialog"""
        try:
            from proxy_manager import ProxyManagerDialog
            dialog = ProxyManagerDialog(self)
            dialog.exec_()
        except Exception as e:
            error_msg = f'Lỗi khi mở quản lý proxy: {str(e)}'
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, 'Lỗi', error_msg)
    
    def show_settings_manager(self):
        """Show application settings manager dialog"""
        try:
            dialog = SettingsManagerDialog(self)
            result = dialog.exec_()

            # If settings were saved, show confirmation
            if result == QDialog.Accepted:
                logger.info("Settings saved successfully")
                # Optionally reload some settings here if needed

        except Exception as e:
            error_msg = f'Lỗi khi mở quản lý cài đặt: {str(e)}'
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, 'Lỗi', error_msg)

    def show_channel_intro_manager(self):
        """Show channel intro manager dialog"""
        try:
            from channel_intro_manager import ChannelIntroDialog
            dialog = ChannelIntroDialog(self)
            result = dialog.exec_()

            # If intros were modified, reload combo boxes in all chapter widgets
            if result == QDialog.Accepted:
                logger.info("Channel intros updated")
                # Reload intros in all chapter widgets
                self.reload_chapter_intros()

        except Exception as e:
            error_msg = f'Lỗi khi mở quản lý channel intro: {str(e)}'
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, 'Lỗi', error_msg)

    def reload_chapter_intros(self):
        """Reload channel intro comboboxes in all chapter widgets"""
        try:
            from channel_intro_manager import ChannelIntroManager
            manager = ChannelIntroManager()
            intro_names = manager.get_intro_names()

            # Find all ChapterWidget instances and reload their intro combos
            for widget in self.chapter_widgets:
                if widget and hasattr(widget, 'intro_combo'):
                    current_text = widget.intro_combo.currentText()
                    widget.intro_combo.clear()
                    widget.intro_combo.addItems(intro_names)
                    # Try to restore previous selection
                    index = widget.intro_combo.findText(current_text)
                    if index >= 0:
                        widget.intro_combo.setCurrentIndex(index)

        except Exception as e:
            logger.error(f"Error reloading chapter intros: {e}", exc_info=True)


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

        story = current_item.data(Qt.UserRole)
        if not story:
            QMessageBox.warning(self, 'Lỗi', 'Không thể lấy thông tin truyện!')
            return

        try:
            dialog = StoryEditorDialog(self, self.db_service, story)
            if dialog.exec_() == QDialog.Accepted:
                self.load_stories()
                # Reload current story if it was the one edited
                if self.current_story and self.current_story['id'] == story['id']:
                    self.load_chapters(story['id'])
        except Exception as e:
            QMessageBox.critical(self, 'Lỗi', f'Không thể sửa truyện: {str(e)}')

    def delete_story(self):
        """Delete selected story"""
        current_item = self.story_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Lỗi', 'Vui lòng chọn một truyện để xóa!')
            return

        story = current_item.data(Qt.UserRole)
        if not story:
            QMessageBox.warning(self, 'Lỗi', 'Không thể lấy thông tin truyện!')
            return

        reply = QMessageBox.question(
            self, 'Xác nhận xóa',
            f'Bạn có chắc chắn muốn xóa truyện "{story["name"]}"?\n\nTất cả các chương sẽ bị xóa theo!',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.db_service.delete_story(story['id'])
                QMessageBox.information(self, 'Thành công', 'Đã xóa truyện!')
                self.load_stories()
                # Clear current story if it was deleted
                if self.current_story and self.current_story['id'] == story['id']:
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
                selected_chapter = widget.chapter
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
                selected_chapters.append(widget.chapter)

        if not selected_chapters:
            QMessageBox.warning(self, 'Lỗi', 'Vui lòng chọn ít nhất một chương để xóa!')
            return

        # Count chapters with audio
        chapters_with_audio = sum(1 for ch in selected_chapters if ch.get('audio_file'))

        # Build confirmation message
        confirm_msg = f'Bạn có chắc chắn muốn xóa {len(selected_chapters)} chương đã chọn?'
        if chapters_with_audio > 0:
            confirm_msg += f'\n\n⚠️ Cảnh báo: {chapters_with_audio} chương có file audio sẽ bị xóa!'

        # Show chapter list
        confirm_msg += '\n\nDanh sách chương sẽ xóa:'
        for ch in selected_chapters[:5]:  # Show max 5 chapters
            audio_status = '🔊' if ch.get('audio_file') else '📝'
            confirm_msg += f'\n  {audio_status} {ch.get("chapter_number", "?")}. {ch.get("title", "Unknown")}'

        if len(selected_chapters) > 5:
            confirm_msg += f'\n  ... và {len(selected_chapters) - 5} chương khác'

        reply = QMessageBox.question(
            self, 'Xác nhận xóa',
            confirm_msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                deleted_count = 0
                errors = []

                for chapter in selected_chapters:
                    try:
                        self.db_service.delete_chapter(chapter['id'])
                        deleted_count += 1
                    except Exception as e:
                        errors.append(f"Chương {chapter.get('chapter_number', '?')}: {str(e)}")

                # Show result
                if deleted_count == len(selected_chapters):
                    QMessageBox.information(
                        self,
                        'Thành công',
                        f'✅ Đã xóa {deleted_count} chương thành công!'
                    )
                elif deleted_count > 0:
                    error_msg = f'⚠️ Đã xóa {deleted_count}/{len(selected_chapters)} chương\n\n'
                    error_msg += 'Lỗi:\n' + '\n'.join(errors[:3])
                    if len(errors) > 3:
                        error_msg += f'\n... và {len(errors) - 3} lỗi khác'
                    QMessageBox.warning(self, 'Hoàn thành một phần', error_msg)
                else:
                    QMessageBox.critical(self, 'Lỗi', 'Không thể xóa chương:\n' + '\n'.join(errors[:5]))

                # Reload chapters
                self.load_chapters(self.current_story['id'])
            except Exception as e:
                QMessageBox.critical(self, 'Lỗi', f'Không thể xóa chương: {str(e)}')

def main():
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')  # Modern look
        
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec_())
    except Exception as e:
        logger.critical(f"Application crashed: {str(e)}", exc_info=True)
        raise



if __name__ == '__main__':
    main()
