"""
Selenium Audio Generator Module
Xử lý tạo audio bằng Selenium LOCAL (không qua API)
Sử dụng Google AI Studio automation với AI Voice Analysis
"""
import os
import sys
import time
import json
import unicodedata
import re
from typing import Optional, Dict, List, Tuple
from ai_voice_analyzer import AIVoiceAnalyzer
from generate_audio import create_segments_from_speakers
from profile_pool_manager import get_profile_pool_manager

# Import logger configuration
from logger_config import LoggerConfig, LogBlock

# Initialize Selenium logger
logger = LoggerConfig.setup_module_logger('selenium', LoggerConfig.SELENIUM_LOG_FILE)

try:
    from google_aistudio_automation_chrome import GoogleAIStudioAutomation
except ImportError as e:
    logger.error(f"Failed to import GoogleAIStudioAutomation: {e}", exc_info=True)
    GoogleAIStudioAutomation = None

# Import AI Voice Analyzer và audio utilities
AI_ANALYZER_AVAILABLE = True


def convert_to_slug(text: str) -> str:
    """
    Convert Vietnamese text to slug format (no accents, lowercase, underscores)
    
    Example:
        "Phàm nhân tu tiên" -> "pham_nhan_tu_tien"
        "Đấu Phá Thương Khung" -> "dau_pha_thuong_khung"
    
    Args:
        text: Input text with Vietnamese characters
        
    Returns:
        Slug format string
    """
    # Vietnamese character mapping
    vietnamese_map = {
        'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
        'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'đ': 'd',
        'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
    }
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace Vietnamese characters
    for vn_char, latin_char in vietnamese_map.items():
        text = text.replace(vn_char, latin_char)
    
    # Replace uppercase Vietnamese characters
    for vn_char, latin_char in vietnamese_map.items():
        text = text.replace(vn_char.upper(), latin_char.upper())
    
    # Remove any remaining accents using unicodedata
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Replace spaces and special characters with underscores
    text = re.sub(r'[^\w\s-]', '', text)  # Remove special chars except spaces and hyphens
    text = re.sub(r'[-\s]+', '_', text)   # Replace spaces/hyphens with underscores
    
    # Remove leading/trailing underscores
    text = text.strip('_')
    
    # Convert to lowercase
    text = text.lower()
    
    return text
# Import pydub for audio merging
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError as e:
    logger.warning(f"pydub not available: {e}")
    AudioSegment = None
    PYDUB_AVAILABLE = False


class SeleniumAudioGenerator:
    """
    Xử lý tạo audio bằng Selenium LOCAL
    Không cần gọi API backend
    """
    
    def __init__(self, 
                 chrome_binary_path: Optional[str] = None,
                 chromedriver_path: Optional[str] = None,
                 download_path: Optional[str] = None,
                 headless: bool = False,
                 profile_name: Optional[str] = None,
                 use_random_profile: bool = True):
        """
        Khởi tạo Selenium Audio Generator
        
        Args:
            chrome_binary_path: Đường dẫn đến Chrome binary
            chromedriver_path: Đường dẫn đến ChromeDriver
            download_path: Đường dẫn lưu audio files
            headless: Chạy Chrome ở chế độ headless
            profile_name: Tên profile Chrome để sử dụng (None = auto select)
            use_random_profile: True = random từ pool, False = dùng default/specified profile
        """
        if GoogleAIStudioAutomation is None:
            raise ImportError(
                "Không thể import GoogleAIStudioAutomation. "
                "Vui lòng kiểm tra file google_aistudio_automation_chrome.py"
            )
        current_dir = os.getcwd()
        self.chrome_binary_path = chrome_binary_path
        self.chromedriver_path = chromedriver_path
        self.download_path = download_path or os.path.join(
            current_dir, 'audio_downloads'
        )
        self.headless = headless
        self.automation = None
        self.use_random_profile = use_random_profile
        
        # Get profile name with new random selection support
        if profile_name:
            # User specified profile
            self.profile_name = profile_name
            logger.info(f"📌 Using specified profile: {self.profile_name}")
        elif use_random_profile:
            # Random selection from pool
            try:
                pool_manager = get_profile_pool_manager()
                random_profile = pool_manager.get_random_profile(only_active=True)
                
                if random_profile:
                    self.profile_name = random_profile
                    logger.info(f"🎲 Randomly selected profile: {self.profile_name}")
                else:
                    logger.warning("⚠️ No active profiles in pool, using fallback")
                    self.profile_name = self._get_fallback_profile()
            except Exception as e:
                logger.warning(f"⚠️ Failed to get random profile: {e}")
                self.profile_name = self._get_fallback_profile()
        else:
            # Legacy behavior: get default from ProfileManager
            self.profile_name = self._get_fallback_profile()
        
        # Tạo download directory
        os.makedirs(self.download_path, exist_ok=True)
    
    def _get_default_voice(self, voice_gender: str) -> str:
        """
        Map voice gender to default voice name

        Args:
            voice_gender: 'male' or 'female'

        Returns:
            Voice name string (e.g., 'Charon', 'Leda')
        """
        # Voice mapping based on Google Chirp 3 HD voices
        # Male voices: Puck, Charon, Fenrir, Orus
        # Female voices: Aoede, Kore, Leda, Leda
        # Extended voices: Puck, Kochab, Pavo, etc. (gender varies)
        voice_map = {
            'male': 'Puck',    # Male voice (deep, mature)
            'female': 'Leda'   # Female voice (clear, expressive)
        }
        return voice_map.get(voice_gender.lower(), 'Leda')

    def _get_fallback_profile(self) -> str:
        """
        Get fallback profile name

        Returns:
            Profile name from ProfileManager or hardcoded fallback
        """
        try:
            from profile_manager import ProfileManagerDialog
            profile_name = ProfileManagerDialog.get_default_profile_name()
            logger.info(f"📋 Using default profile from ProfileManager: {profile_name}")
            return profile_name
        except Exception as e:
            logger.warning(f"⚠️ Failed to get profile from ProfileManager: {e}")
            return "vothienhoait"  # Hardcoded fallback
    
    def initialize_automation(self) -> bool:
        """
        Khởi tạo Google AI Studio Automation
        
        Returns:
            True nếu thành công, False nếu thất bại
        """
        with LogBlock(logger, "Initialize Google AI Studio Automation"):
            try:
                # 🔍 Check if we can reuse existing automation
                if self.automation:
                    self.automation.cleanup()
                    self.automation = None
                
                # Get proxy configuration for this profile if available
                use_proxy = False
                proxy_data = None
                
                try:
                    from profile_manager import ProfileManagerDialog
                    proxy_manager = ProfileManagerDialog(None)
                    proxy_obj = proxy_manager.get_proxy_for_profile(self.profile_name)
                    if proxy_obj:
                        use_proxy = True
                        proxy_data = {
                            "host": proxy_obj.host,
                            "port": proxy_obj.port,
                            "username": proxy_obj.username,
                            "password": proxy_obj.password,
                            "protocol": proxy_obj.protocol
                        }
                        logger.info(f"🌐 Using proxy for profile {self.profile_name}: {proxy_obj.host}:{proxy_obj.port}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to get proxy configuration: {e}")
                
                # Khởi tạo automation với các tùy chọn
                # NOTE: GoogleAIStudioAutomation chỉ khởi tạo configs trong __init__
                # PHẢI gọi setup_driver() để thực sự khởi động Chrome
                self.automation = GoogleAIStudioAutomation(
                    headless=False,
                    use_profile=True,
                    profile_name=self.profile_name,
                    auto_clear_data_on_startup=False,
                    extensions=[],  # Thêm extensions nếu cần
                    auto_install_extensions=False,
                    download_path=self.download_path,
                    use_proxy=use_proxy,
                    proxy_data=proxy_data
                )
                
                # ⭐ CRITICAL: Setup Chrome driver (bắt buộc!)
                # __init__() chỉ khởi tạo configs, KHÔNG setup driver
                logger.info("🚀 Setting up Chrome driver...")
                if not self.automation.setup_driver():
                    logger.error("❌ Failed to setup Chrome driver")
                    return False
                
                logger.info("✅ Chrome driver setup successfully")
                return True
                
            except Exception as e:
                logger.error(f"❌ Automation initialization failed: {e}", exc_info=True)
                return False
    
    # ============================================
    # Cache Management Methods
    # ============================================
    
    def _get_cache_path(self, story_name: str, story_id: int, chapter_number: int, language: str = 'vi') -> str:
        """
        Get cache file path for speaker analysis (stored in story's conversations folder)

        Args:
            story_name: Tên story
            story_id: ID story
            chapter_number: Số chương
            language: Mã ngôn ngữ (vi, en, ja, etc.)

        Returns:
            Path to cache file in audio_downloads/<language>/<story_name>/conversations/
        """
        # Convert story name to slug
        story_folder = convert_to_slug(story_name)

        # Use story's conversations directory for cache with language structure
        lang_folder = os.path.join(self.download_path, language)
        cache_dir = os.path.join(lang_folder, story_folder, 'conversations')
        os.makedirs(cache_dir, exist_ok=True)
        cache_filename = f"{story_id}_{chapter_number}.json"
        return os.path.join(cache_dir, cache_filename)
    
    def _get_cached_analysis(self, story_name: str, story_id: int, chapter_number: int, language: str = 'vi') -> Optional[Dict]:
        """
        Load cached speaker analysis from story's conversations folder if exists

        Args:
            story_name: Tên story
            story_id: ID của story
            chapter_number: Số thứ tự chương
            language: Mã ngôn ngữ (vi, en, ja, etc.)

        Returns:
            Dict chứa analysis results hoặc None
        """
        try:
            cache_path = self._get_cache_path(story_name, story_id, chapter_number, language)

            if os.path.exists(cache_path):
                with open(cache_path, 'r', encoding='utf-8') as f:
                    analysis = json.load(f)
                logger.info(f"📦 Loaded cached analysis from: {cache_path}")
                return analysis
            else:
                logger.debug(f"No cache found at: {cache_path}")
                return None

        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            return None
    
    def _save_cached_analysis(self, story_name: str, story_id: int, chapter_number: int, analysis: Dict, language: str = 'vi'):
        """
        Save speaker analysis to cache in story's conversations folder

        Args:
            story_name: Tên story
            story_id: ID của story
            chapter_number: Số thứ tự chương
            analysis: Analysis results to cache
            language: Mã ngôn ngữ (vi, en, ja, etc.)
        """
        try:
            cache_path = self._get_cache_path(story_name, story_id, chapter_number, language)

            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)

            logger.info(f"💾 Saved cache to: {cache_path}")

        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    # ============================================
    # Speaker Analysis Methods
    # ============================================
    
    def _analyze_speakers(self, chapter_content: str, story_name: str, story_id: int, chapter_number: int, language: str = 'vi') -> Dict:
        """
        Analyze speakers in chapter content using AI

        Args:
            chapter_content: Nội dung chương
            story_name: Tên story
            story_id: ID của story
            chapter_number: Số thứ tự chương
            language: Mã ngôn ngữ (vi, en, ja, etc.)

        Returns:
            Dict chứa speaker analysis
        """
        # Check cache first
        cached = self._get_cached_analysis(story_name, story_id, chapter_number, language)
        if cached:
            return cached

        # Check if AI Analyzer available
        if not AI_ANALYZER_AVAILABLE or AIVoiceAnalyzer is None:
            logger.warning("⚠️ AI Voice Analyzer not available, returning empty analysis")
            return {'speakers': []}

        # Analyze

        try:
            with LogBlock(logger, "AI Speaker Analysis"):
                analyzer = AIVoiceAnalyzer()
                analysis = analyzer.create_analysis_prompt(chapter_content)

            # Save to cache
            self._save_cached_analysis(story_name, story_id, chapter_number, analysis, language)
            
            speakers_count = len(analysis.get('speakers', []))
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Speaker analysis failed: {e}", exc_info=True)
            return {'speakers': []}
    
    # ============================================
    # Segment Audio Generation Methods
    # ============================================
    
    def _generate_segment_audio(self, segment_pair: Tuple, order_in_story: int) -> Optional[str]:
        """
        Generate audio for a single segment
        
        Args:
            segment_pair: Tuple of (text, voice_name, characteristics, role) for 1-2 speakers
            order_in_story: Segment number
            
        Returns:
            Path to generated audio file or None
        """
        try:
            # Extract segment data
            segment_text_1, voice_name_1, characteristics_1, role1 = segment_pair[0]
            
            if len(segment_pair) > 1:
                segment_text_2, voice_name_2, characteristics_2, role2 = segment_pair[1]
            else:
                segment_text_2, voice_name_2, characteristics_2, role2 = "", "Puck", "", "narrator"
            
            # Format prompt
            def get_action_word(role):
                return "Read" if role.lower() == "narrator" else "Make"

            # Chuẩn hóa đặc điểm giọng cho narrator
            def normalize_narrator_characteristics(characteristics, role):
                if role.lower() == "narrator":
                    return "Giọng kể chuyện truyền cảm, chân thực, rõ ràng và cuốn hút dành cho người lớn. Giọng ấm áp, sâu lắng, giàu cảm xúc như đang chia sẻ câu chuyện của chính mình."
                return characteristics

            action_word_1 = get_action_word(role1)
            action_word_2 = get_action_word(role2)

            # Chuẩn hóa characteristics cho narrator
            characteristics_1 = normalize_narrator_characteristics(characteristics_1, role1)
            characteristics_2 = normalize_narrator_characteristics(characteristics_2, role2)

            # Capitalize voice names
            def capitalize_first_letter(text):
                return text[:1].upper() + text[1:] if text else text

            voice_name_1 = capitalize_first_letter(voice_name_1)
            voice_name_2 = capitalize_first_letter(voice_name_2)
            
            # Build prompt
            if segment_text_2.strip():
                prompt_text = (
                    f"Speaker 1 {action_word_1} aloud in a {characteristics_1}, "
                    f"Speaker 2 {action_word_2} aloud in a {characteristics_2}\n"
                    f"Speaker 1: {segment_text_1}\n"
                    f"Speaker 2: {segment_text_2}"
                )
            else:
                prompt_text = (
                    f"Speaker 1 {action_word_1} aloud in a {characteristics_1}\n"
                    f"Speaker 1: {segment_text_1}"
                )
            
            
            # Generate audio
            with LogBlock(logger, f"Generate segment {order_in_story}"):
                result = self.automation.generate_audio_from_text(
                    text=prompt_text,
                    wait_for_auth=True,
                    voice_name_1=voice_name_1,
                    voice_name_2=voice_name_2,
                    order_in_story=order_in_story,
                    use_fast_paste=True
                )
            
            if result.get('success'):
                audio_path = result.get('audio_path')
                return audio_path
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.error(f"❌ Segment {order_in_story} failed: {error_msg}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Exception generating segment {order_in_story}: {e}", exc_info=True)
            return None

    def _split_into_chunks(self, text: str, max_words_per_chunk: int) -> List[str]:
        """
        Split long text into smaller chunks at natural breakpoints

        Args:
            text: Text to split
            max_words_per_chunk: Maximum words per chunk

        Returns:
            List of text chunks
        """
        # Split by sentences first (Vietnamese and English sentence endings)
        sentence_endings = ['. ', '! ', '? ', '.\n', '!\n', '?\n', '." ', '!" ', '?" ']

        # Simple sentence splitter
        sentences = []
        current_sentence = ""

        i = 0
        while i < len(text):
            current_sentence += text[i]

            # Check if we hit a sentence ending
            found_ending = False
            for ending in sentence_endings:
                if current_sentence.endswith(ending):
                    sentences.append(current_sentence.strip())
                    current_sentence = ""
                    found_ending = True
                    break

            i += 1

        # Add remaining text as last sentence
        if current_sentence.strip():
            sentences.append(current_sentence.strip())

        logger.info(f"📝 Split into {len(sentences)} sentences")

        # Group sentences into chunks
        chunks = []
        current_chunk = ""
        current_word_count = 0

        for sentence in sentences:
            sentence_word_count = len(sentence.split())

            # If adding this sentence would exceed limit, start new chunk
            if current_word_count > 0 and (current_word_count + sentence_word_count) > max_words_per_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
                current_word_count = sentence_word_count
            else:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                current_word_count += sentence_word_count

        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # Log chunk statistics
        for idx, chunk in enumerate(chunks, 1):
            chunk_words = len(chunk.split())
            logger.debug(f"  Chunk {idx}: {chunk_words} words, {len(chunk)} chars")

        return chunks

    def _merge_segments(self, segment_files: List[str], output_path: str) -> bool:
        """
        Merge audio segments with 1s silence between each
        
        Args:
            segment_files: List of audio file paths
            output_path: Output merged audio file path
            
        Returns:
            True if successful
        """
        if not PYDUB_AVAILABLE or AudioSegment is None:
            logger.error("❌ pydub not available, cannot merge segments")
            return False
        
        try:
            
            combined_audio = AudioSegment.empty()
            one_sec_silence = AudioSegment.silent(duration=1000)  # 1 second
            
            merged_count = 0
            for idx, audio_file in enumerate(segment_files):
                if os.path.exists(audio_file):
                    audio_segment = AudioSegment.from_wav(audio_file)
                    combined_audio += audio_segment
                    merged_count += 1
                    
                    # Add silence between segments (not after last)
                    if idx < len(segment_files) - 1:
                        combined_audio += one_sec_silence
                else:
                    logger.warning(f"⚠️ Segment not found, skipping: {audio_file}")
            
            if merged_count == 0:
                logger.error("❌ No segments to merge")
                return False
            
            # Export merged audio
            combined_audio.export(output_path, format="wav")
            
            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            
            # Cleanup segment files
            for audio_file in segment_files:
                try:
                    if os.path.exists(audio_file):
                        os.remove(audio_file)
                except Exception as e:
                    logger.warning(f"  Failed to delete {audio_file}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to merge segments: {e}", exc_info=True)
            return False
    
    def generate_audio(self, 
                      text: str, 
                      output_filename: Optional[str] = None,
                      voice_name_1: str = "Puck",
                      voice_name_2: str = "Puck",
                      speaking_rate: float = 1.0,
                      story_id: Optional[int] = None) -> Dict:
        """
        Tạo audio từ text bằng Selenium
        
        Args:
            text: Nội dung text cần chuyển thành audio
            output_filename: Tên file output (không bắt buộc)
            voice_name_1: Tên voice cho người 1 (default: Puck)
            voice_name_2: Tên voice cho người 2 (default: Puck)
        
        Returns:
            Dict chứa thông tin kết quả:
            {
                'success': bool,
                'audio_path': str hoặc None,
                'message': str
            }
        """
        try:
            # Khởi tạo automation nếu chưa có
            if self.automation is None:
                if not self.initialize_automation():
                    logger.error("Failed to initialize automation for audio generation")
                    return {
                        'success': False,
                        'audio_path': None,
                        'message': 'Không thể khởi tạo automation'
                    }
            
            
            # Generate audio
            with LogBlock(logger, f"Generate speech for text (length={len(text)})"):
                result = self.automation.generate_audio_from_text(
                    text=text,
                    wait_for_auth=True,
                    voice_name_1=voice_name_1,
                    voice_name_2=voice_name_2,
                    order_in_story=None,  # Will use default naming
                    use_fast_paste=True,
                    output_filename= output_filename
                )
            
            if result and result.get('success'):
                audio_path = result.get('audio_path')
                file_size = os.path.getsize(audio_path) if audio_path and os.path.exists(audio_path) else 0
                
                return {
                    'success': True,
                    'audio_path': audio_path,
                    'message': 'Tạo audio thành công'
                }
            else:
                error_msg = result.get('message', 'Unknown error') if result else 'No result'
                logger.error(f"❌ Audio generation failed: {error_msg}")
                
                return {
                    'success': False,
                    'audio_path': None,
                    'message': f'Tạo audio thất bại: {error_msg}'
                }
        
        except Exception as e:
            logger.error(f"❌ Exception during audio generation: {str(e)}", exc_info=True)
            return {
                'success': False,
                'audio_path': None,
                'message': f'Lỗi: {str(e)}'
            }
    
    def generate_audio_for_chapter(self,
                                   chapter_content: str,
                                   chapter_id: int,
                                   chapter_title: str,
                                   story_id: Optional[int] = None,
                                   story_name: Optional[str] = None,
                                   chapter_number: Optional[int] = None,
                                   use_segments: bool = True,
                                   cleanup_after: bool = True,
                                   voice_gender: str = 'male',
                                   channel_intro: str = '',
                                   language: str = 'vi') -> Dict:
        """
        Tạo audio cho một chương truyện

        Supports 2 modes:
        - Advanced (use_segments=True): AI speaker analysis → segments → merge
        - Simple (use_segments=False): Direct full chapter generation

        Args:
            chapter_content: Nội dung chương
            chapter_id: ID của chương
            chapter_title: Tiêu đề chương
            story_id: ID của story (để tổ chức files)
            story_name: Tên story (để tạo tên file rõ ràng)
            chapter_number: Số thứ tự chương (để phân tích và cache)
            use_segments: True = advanced mode, False = simple mode
            cleanup_after: True = cleanup automation sau khi hoàn thành chapter (default: True)
            language: Mã ngôn ngữ (vi, en, ja, etc.) để tổ chức thư mục

        Returns:
            Dict chứa kết quả
        """
        result = None
        try:
            # Sử dụng chapter_number nếu được cung cấp, nếu không dùng chapter_id
            chapter_num = chapter_number if chapter_number is not None else chapter_id
            
            
            # Khởi tạo automation nếu chưa có
            if self.automation is None:
                if not self.initialize_automation():
                    logger.error("Failed to initialize automation")
                    return {
                        'success': False,
                        'audio_path': None,
                        'message': 'Không thể khởi tạo automation'
                    }
            
            # Tạo thư mục theo ngôn ngữ và tên truyện
            # Cấu trúc: audio_downloads/<language>/<story_slug>/chuong_xx.mp3
            if story_id and story_name:
                # Tạo tên thư mục slug (không dấu, lowercase, underscore)
                # Ví dụ: "Phàm nhân tu tiên" -> "pham_nhan_tu_tien"
                safe_story = convert_to_slug(story_name)

                # Tạo cấu trúc thư mục theo ngôn ngữ
                lang_folder = os.path.join(self.download_path, language)
                story_folder = os.path.join(lang_folder, safe_story)

                # Kiểm tra và tạo thư mục nếu chưa có
                if not os.path.exists(story_folder):
                    os.makedirs(story_folder, exist_ok=True)
                    logger.info(f"📁 Created story folder: {story_folder}")

                # Tên file đơn giản: chuong_xx.mp3
                output_filename = f"chuong_{chapter_num:02d}.mp3"
                output_path = os.path.join(story_folder, output_filename)
            else:
                # Fallback: lưu trực tiếp vào download_path/<language> với tên chapter
                lang_folder = os.path.join(self.download_path, language)
                os.makedirs(lang_folder, exist_ok=True)
                safe_title = "".join(c for c in chapter_title if c.isalnum() or c in (' ', '-', '_')).strip()
                output_filename = f"chuong_{chapter_num}_{safe_title}.mp3"
                output_path = os.path.join(lang_folder, output_filename)
            
            # ============================================
            # ADVANCED MODE: Segment-based generation
            # ============================================
            cache = self._get_cached_analysis(story_name=story_name, story_id=story_id, chapter_number=chapter_number, language=language)
            if cache is None:
                with LogBlock(logger, "Generate full chapter audio (no cache)"):
                    # Map voice_gender to voice_name
                    default_voice = self._get_default_voice(voice_gender)

                    # Format channel intro with story name and chapter title
                    formatted_intro = ""
                    if channel_intro:
                        formatted_intro = channel_intro.format(
                            story_name=story_name or "Truyện",
                            chapter_title=chapter_title
                        )

                    # Combine intro with chapter content
                    full_content = formatted_intro + chapter_content.strip()

                    # Check if content is too long and needs chunking
                    # Estimate: ~150 words/minute, 10min = 1500 words ≈ 7500 chars (Vietnamese)
                    MAX_CHUNK_SIZE = 1500  # words per chunk (safe limit for ~8-9 minutes)

                    # Count words in full_content
                    word_count = len(full_content.split())
                    logger.info(f"📊 Content stats: {word_count} words, {len(full_content)} chars")

                    # If content is short enough, generate directly
                    if word_count <= MAX_CHUNK_SIZE:
                        logger.info("✅ Content fits in single chunk, generating directly...")
                        narrator_prompt = (
                            "Giọng kể chuyện sâu lắng, chân thành và đầy cảm xúc dành cho người trưởng thành. Giọng ấm áp, gần gũi, thấu hiểu những câu chuyện tình yêu và tâm sự của người lớn tuổi 18+.\n"
                            f"Speaker 1: {full_content}"
                        )

                        result = self.generate_audio(
                            text=narrator_prompt,
                            output_filename=output_filename,
                            voice_name_1=default_voice,
                            voice_name_2=default_voice,
                            story_id=story_id
                        )
                    else:
                        # Content too long - split into chunks
                        logger.info(f"⚠️ Content too long ({word_count} words), splitting into chunks...")
                        chunks = self._split_into_chunks(full_content, MAX_CHUNK_SIZE)
                        logger.info(f"📦 Split into {len(chunks)} chunks")

                        # Generate audio for each chunk
                        chunk_files = []
                        for idx, chunk_text in enumerate(chunks, start=1):
                            chunk_word_count = len(chunk_text.split())
                            logger.info(f"🎯 Generating chunk {idx}/{len(chunks)} ({chunk_word_count} words)...")

                            chunk_prompt = (
                                "Giọng kể chuyện sâu lắng, chân thành và đầy cảm xúc dành cho người trưởng thành. Giọng ấm áp, gần gũi, thấu hiểu những câu chuyện tình yêu và tâm sự của người lớn tuổi 18+.\n"
                                f"Speaker 1: {chunk_text}"
                            )

                            chunk_filename = f"chunk_{idx:03d}_{output_filename}"
                            chunk_result = self.generate_audio(
                                text=chunk_prompt,
                                output_filename=chunk_filename,
                                voice_name_1=default_voice,
                                voice_name_2=default_voice,
                                story_id=story_id
                            )

                            if chunk_result and chunk_result.get('success'):
                                chunk_path = chunk_result.get('audio_path')
                                if chunk_path and os.path.exists(chunk_path):
                                    chunk_files.append(chunk_path)
                                    logger.info(f"✅ Chunk {idx}/{len(chunks)} generated: {chunk_path}")
                                else:
                                    logger.error(f"❌ Chunk {idx} file not found")
                            else:
                                logger.error(f"❌ Chunk {idx} generation failed")

                        # Merge chunks into final file
                        if chunk_files:
                            logger.info(f"🔗 Merging {len(chunk_files)} chunks...")
                            merge_success = self._merge_segments(chunk_files, output_path)

                            if merge_success:
                                result = {
                                    'success': True,
                                    'audio_path': output_path,
                                    'message': f'Generated from {len(chunk_files)} chunks'
                                }
                            else:
                                result = {
                                    'success': False,
                                    'audio_path': None,
                                    'message': 'Failed to merge chunks'
                                }
                        else:
                            result = {
                                'success': False,
                                'audio_path': None,
                                'message': 'No chunks generated successfully'
                            }

                    # Move generated file to correct output path (for single chunk case)
                    if result and result.get('success') and word_count <= MAX_CHUNK_SIZE:
                        generated_path = result.get('audio_path')
                        if generated_path and os.path.exists(generated_path):
                            # If generated path is different from output path, move it
                            if os.path.abspath(generated_path) != os.path.abspath(output_path):
                                try:
                                    import shutil
                                    shutil.move(generated_path, output_path)
                                    logger.info(f"✅ Moved audio file to: {output_path}")
                                    result['audio_path'] = output_path
                                except Exception as e:
                                    logger.error(f"❌ Failed to move file: {e}")
                                    # Keep original path if move fails
                            else:
                                logger.info(f"✅ Audio already at correct path: {output_path}")

                    # Cleanup automation after chapter completion
                    if cleanup_after:
                        logger.info("🔄 Cleanup automation after chapter completion...")
                        self.cleanup_automation()

                return result
                
            if use_segments and AI_ANALYZER_AVAILABLE and PYDUB_AVAILABLE and cache:
                logger.info("🎯 Using ADVANCED mode: Segment-based generation")
                
                # Step 1: Analyze speakers
                with LogBlock(logger, "Step 1: Speaker Analysis"):
                    analysis = self._analyze_speakers(
                        chapter_content=chapter_content,
                        story_name=story_name,
                        story_id=story_id or 0,
                        chapter_number=chapter_num,
                        language=language
                    )
                
                speakers = analysis.get('speakers', [])
                if not speakers:
                    logger.warning("⚠️ No speakers found, falling back to simple mode")
                    use_segments = False  # Fallback
                else:
                    # Step 2: Create segments
                    with LogBlock(logger, "Step 2: Create Segments"):
                        try:
                            segments = create_segments_from_speakers(speakers)
                        except Exception as e:
                            logger.error(f"❌ Segment creation failed: {e}", exc_info=True)
                            use_segments = False  # Fallback
                            segments = []
                    
                    if segments:
                        # Step 3: Generate audio for each segment
                        segment_files = []
                        with LogBlock(logger, f"Step 3: Generate {len(segments)} segments"):
                            for idx, segment_pair in enumerate(segments, start=1):
                                audio_path = self._generate_segment_audio(
                                    segment_pair=segment_pair,
                                    order_in_story=idx
                                )
                                
                                if audio_path:
                                    segment_files.append(audio_path)
                                else:
                                    logger.warning(f"⚠️ Segment {idx} failed, continuing...")
                        
                        if not segment_files:
                            logger.error("❌ No segments generated successfully, falling back to simple mode")
                            use_segments = False  # Fallback
                        else:
                            # Step 4: Merge segments
                            with LogBlock(logger, "Step 4: Merge Segments"):
                                merge_success = self._merge_segments(
                                    segment_files=segment_files,
                                    output_path=output_path
                                )
                            
                            if merge_success:
                                file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
                                result = {
                                    'success': True,
                                    'audio_path': output_path,
                                    'message': f'Tạo audio thành công (Advanced: {len(segment_files)} segments)'
                                }
                                # Cleanup automation after chapter completion
                                if cleanup_after:
                                    logger.info("🔄 Cleanup automation after chapter completion...")
                                    self.cleanup_automation()
                                return result
                            else:
                                logger.error("❌ Merge failed, falling back to simple mode")
                                use_segments = False  # Fallback
            else:
                # ⭐ CRITICAL: If advanced mode not available, force simple mode
                if use_segments:
                    if not AI_ANALYZER_AVAILABLE:
                        logger.warning("⚠️ AI Analyzer not available, using SIMPLE mode")
                    elif not PYDUB_AVAILABLE:
                        logger.warning("⚠️ pydub not available, using SIMPLE mode")
                    use_segments = False  # Force simple mode
            
            # ============================================
            # SIMPLE MODE: Full chapter generation
            # ============================================
            if not use_segments:
                logger.info("🎯 Using SIMPLE mode: Full chapter generation")

                # Map voice_gender to voice_name
                default_voice = self._get_default_voice(voice_gender)

                # Format channel intro with story name and chapter title
                formatted_intro = ""
                if channel_intro:
                    formatted_intro = channel_intro.format(
                        story_name=story_name or "Truyện",
                        chapter_title=chapter_title
                    )

                # Combine intro with chapter content
                full_content = formatted_intro + chapter_content.strip()

                # Check if content is too long and needs chunking
                MAX_CHUNK_SIZE = 1500  # words per chunk (safe limit for ~8-9 minutes)

                # Count words in full_content
                word_count = len(full_content.split())
                logger.info(f"📊 Content stats: {word_count} words, {len(full_content)} chars")

                # If content is short enough, generate directly
                if word_count <= MAX_CHUNK_SIZE:
                    logger.info("✅ Content fits in single chunk, generating directly...")
                    narrator_prompt = (
                        "Giọng kể chuyện sâu lắng, chân thành và đầy cảm xúc dành cho người trưởng thành. Giọng ấm áp, gần gũi, thấu hiểu những câu chuyện tình yêu và tâm sự của người lớn tuổi 18+.\n"
                        f"Speaker 1: {full_content}"
                    )

                    with LogBlock(logger, "Generate full chapter audio"):
                        result = self.generate_audio(
                            text=narrator_prompt,
                            output_filename=output_filename,
                            voice_name_1=default_voice,
                            voice_name_2=default_voice,
                            story_id=story_id
                        )
                else:
                    # Content too long - split into chunks
                    logger.info(f"⚠️ Content too long ({word_count} words), splitting into chunks...")
                    chunks = self._split_into_chunks(full_content, MAX_CHUNK_SIZE)
                    logger.info(f"📦 Split into {len(chunks)} chunks")

                    # Generate audio for each chunk
                    chunk_files = []
                    for idx, chunk_text in enumerate(chunks, start=1):
                        chunk_word_count = len(chunk_text.split())
                        logger.info(f"🎯 Generating chunk {idx}/{len(chunks)} ({chunk_word_count} words)...")

                        chunk_prompt = (
                            "Giọng kể chuyện sâu lắng, chân thành và đầy cảm xúc dành cho người trưởng thành. Giọng ấm áp, gần gũi, thấu hiểu những câu chuyện tình yêu và tâm sự của người lớn tuổi 18+.\n"
                            f"Speaker 1: {chunk_text}"
                        )

                        chunk_filename = f"chunk_{idx:03d}_{output_filename}"
                        chunk_result = self.generate_audio(
                            text=chunk_prompt,
                            output_filename=chunk_filename,
                            voice_name_1=default_voice,
                            voice_name_2=default_voice,
                            story_id=story_id
                        )

                        if chunk_result and chunk_result.get('success'):
                            chunk_path = chunk_result.get('audio_path')
                            if chunk_path and os.path.exists(chunk_path):
                                chunk_files.append(chunk_path)
                                logger.info(f"✅ Chunk {idx}/{len(chunks)} generated: {chunk_path}")
                            else:
                                logger.error(f"❌ Chunk {idx} file not found")
                        else:
                            logger.error(f"❌ Chunk {idx} generation failed")

                    # Merge chunks into final file
                    if chunk_files:
                        logger.info(f"🔗 Merging {len(chunk_files)} chunks...")
                        merge_success = self._merge_segments(chunk_files, output_path)

                        if merge_success:
                            result = {
                                'success': True,
                                'audio_path': output_path,
                                'message': f'Generated from {len(chunk_files)} chunks'
                            }
                        else:
                            result = {
                                'success': False,
                                'audio_path': None,
                                'message': 'Failed to merge chunks'
                            }
                    else:
                        result = {
                            'success': False,
                            'audio_path': None,
                            'message': 'No chunks generated successfully'
                        }

                # Move generated file to correct output path (for single chunk case)
                if result and result.get('success') and word_count <= MAX_CHUNK_SIZE:
                    generated_path = result.get('audio_path')
                    if generated_path and os.path.exists(generated_path):
                        # If generated path is different from output path, move it
                        if os.path.abspath(generated_path) != os.path.abspath(output_path):
                            try:
                                import shutil
                                shutil.move(generated_path, output_path)
                                logger.info(f"✅ Moved audio file to: {output_path}")
                                result['audio_path'] = output_path
                            except Exception as e:
                                logger.error(f"❌ Failed to move file: {e}")
                                # Keep original path if move fails
                        else:
                            logger.info(f"✅ Audio already at correct path: {output_path}")

                # Cleanup automation after chapter completion
                if cleanup_after:
                    logger.info("🔄 Cleanup automation after chapter completion...")
                    self.cleanup_automation()
                return result
            
            # Should not reach here
            result = {
                'success': False,
                'audio_path': None,
                'message': 'Unknown error in generation flow'
            }
            # Cleanup on error
            if cleanup_after:
                logger.info("🔄 Cleanup automation after error...")
                self.cleanup_automation()
            return result
            
        except Exception as e:
            logger.error(f"❌ Error generating audio for chapter {chapter_id}: {str(e)}", exc_info=True)
            # Cleanup on exception
            if cleanup_after:
                logger.info("🔄 Cleanup automation after exception...")
                self.cleanup_automation()
            return {
                'success': False,
                'audio_path': None,
                'message': f'Lỗi: {str(e)}'
            }
    
    def cleanup_automation(self):
        """
        Đóng và cleanup automation instance hiện tại
        Dùng để dọn dẹp sau mỗi chapter
        """
        import time
        
        try:
            if self.automation:
                logger.info("🧹 Cleaning up automation session...")
                
                # ⭐ NEW: Clear cache (except cookies) before closing
                try:
                    if self.automation.driver:
                        logger.info("🗑️ Clearing browser cache (keeping cookies)...")
                        
                        # Clear cache using Chrome DevTools Protocol
                        self.automation.driver.execute_cdp_cmd('Network.clearBrowserCache', {})
                        logger.info("✅ Browser cache cleared")
                        
                        # Optional: Clear localStorage and sessionStorage (không xóa cookies)
                        try:
                            self.automation.driver.execute_script("window.localStorage.clear();")
                            self.automation.driver.execute_script("window.sessionStorage.clear();")
                            logger.info("✅ Local/Session storage cleared")
                        except Exception as storage_error:
                            logger.debug(f"Storage clear failed (non-critical): {storage_error}")
                        
                        # Reload trang để refresh state
                        try:
                            logger.info("🔄 Reloading page...")
                            self.automation.driver.refresh()
                            time.sleep(2)  # Wait for page reload
                            logger.info("✅ Page reloaded")
                        except Exception as reload_error:
                            logger.debug(f"Page reload failed (non-critical): {reload_error}")
                            
                except Exception as cache_error:
                    logger.warning(f"⚠️ Cache cleanup failed (non-critical): {cache_error}")
                
                # Close automation (calls driver.quit())
                self.automation.close()
                self.automation = None
                
                # ⭐ CRITICAL: Wait for Chrome to fully exit
                logger.info("⏳ Waiting for Chrome processes to exit...")
                time.sleep(3)  # Give Chrome time to cleanup
                
                # Kill any zombie Chrome processes related to our profile (optional, requires psutil)
                try:
                    import psutil
                    
                    profile_path = os.path.join(os.path.dirname(self.download_path), 'chrome_profiles', self.profile_name)
                    logger.debug(f"Checking for zombie processes using profile: {profile_path}")
                    
                    killed_count = 0
                    # Find and kill Chrome processes using our profile
                    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                        try:
                            if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                                cmdline = proc.info['cmdline']
                                if cmdline and any(profile_path in str(arg) for arg in cmdline):
                                    logger.warning(f"🔪 Killing zombie Chrome process: PID {proc.info['pid']}")
                                    proc.kill()
                                    proc.wait(timeout=2)
                                    killed_count += 1
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                            pass
                    
                    if killed_count > 0:
                        logger.info(f"Killed {killed_count} zombie Chrome process(es)")
                        time.sleep(1)  # Extra wait after killing processes
                        
                except ImportError:
                    logger.debug("psutil not available, skipping zombie process cleanup")
                except Exception as cleanup_ex:
                    logger.debug(f"Process cleanup check failed (non-critical): {cleanup_ex}")
                
                # Remove profile lock file if exists
                try:
                    profile_path = os.path.join(os.path.dirname(self.download_path), 'chrome_profiles', self.profile_name)
                    lock_file = os.path.join(profile_path, 'SingletonLock')
                    if os.path.exists(lock_file):
                        os.remove(lock_file)
                        logger.debug(f"Removed profile lock: {lock_file}")
                except Exception as lock_ex:
                    logger.debug(f"Lock file removal failed (non-critical): {lock_ex}")
                
                logger.info("✅ Automation cleanup completed")
            else:
                logger.debug("No automation to cleanup")
        except Exception as e:
            logger.error(f"❌ Cleanup error: {str(e)}", exc_info=True)
            # Force set to None even if cleanup fails
            self.automation = None
            # Still wait a bit to let any processes die
            try:
                import time
                time.sleep(2)
            except:
                pass
    
    def cleanup(self):
        """Đóng và cleanup automation (alias for backward compatibility)"""
        self.cleanup_automation()
    
    def __del__(self):
        """Destructor để cleanup khi object bị xóa"""
        self.cleanup()
