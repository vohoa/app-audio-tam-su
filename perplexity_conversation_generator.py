"""
Perplexity Conversation Generator Module
Xử lý tạo hội thoại thông qua Perplexity AI và chuyển đổi sang định dạng phù hợp cho Gemini TTS
"""

import os
import json
import time
from typing import Optional, Dict, List, Any
from datetime import datetime

from logger_config import LoggerConfig, LogBlock
from perplexity_ai_automation import PerplexityAIAutomation

# Initialize logger
logger = LoggerConfig.get_logger('perplexity_conversation')


class PerplexityConversationGenerator:
    """
    Class xử lý việc tạo hội thoại từ Perplexity AI và chuyển đổi sang format cho Gemini
    """
    
    def __init__(self, 
                 conversation_dir: Optional[str] = None,
                 headless: bool = False,
                 profile_name: str = "perplexity_ai"):
        """
        Khởi tạo Perplexity Conversation Generator
        
        Args:
            conversation_dir: Thư mục lưu các file JSON hội thoại
            headless: Chạy browser ở chế độ headless
            profile_name: Tên profile Chrome để sử dụng
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.conversation_dir = conversation_dir or os.path.join(
            current_dir, 'conversations'
        )
        self.headless = headless
        self.profile_name = profile_name
        
        # Tạo thư mục conversations nếu chưa có
        os.makedirs(self.conversation_dir, exist_ok=True)
        logger.info(f"Conversation directory: {self.conversation_dir}")
        
        # Perplexity automation instance (lazy initialization)
        self._automation = None
    
    def get_automation(self) -> PerplexityAIAutomation:
        """
        Lấy hoặc tạo mới automation instance
        
        Returns:
            PerplexityAIAutomation instance
        """
        if self._automation is None:
            logger.info("Creating new Perplexity automation instance")
            self._automation = PerplexityAIAutomation(
                headless=self.headless,
                profile_name=self.profile_name
            )
        return self._automation
    
    def generate_conversation_from_prompt(self,
                                         chapter_content: str = None,
                                         story_name: str = None,
                                         story_id: int = None,
                                         chapter_number: int = None,
                                         timeout: int = 1800) -> Optional[Dict[str, Any]]:
        """
        Tạo hội thoại từ chapter content sử dụng Perplexity AI

        Args:
            chapter_content: Nội dung chapter (Perplexity sẽ tự tạo prompt)
            story_name: Tên story (BẮT BUỘC)
            story_id: ID story (optional)
            chapter_number: Số chương (for context)
            timeout: Thời gian chờ response (giây)

        Returns:
            Dict chứa conversation data hoặc None nếu thất bại
        """
        with LogBlock(logger, "Generate conversation from Perplexity AI"):
            try:
                automation = self.get_automation()

                if chapter_content and story_name:
                    logger.info("Using chapter_content (Perplexity will create prompt)")
                    json_data = automation.generate_conversation_json(
                        chapter_content=chapter_content,
                        story_name=story_name,
                        story_id=story_id,
                        chapter_number=chapter_number,
                        timeout=timeout,
                        save_to_file=False  # We'll save it ourselves
                    )
                else:
                    logger.error("chapter_content and story_name must be provided")
                    return None
                
                if not json_data:
                    logger.error("Failed to get JSON from Perplexity")
                    return None
                
                # Validate JSON structure
                if not self.validate_conversation_json(json_data):
                    logger.error("Invalid conversation JSON structure")
                    logger.info("Attempting to provide debugging info...")
                    
                    # Check if it's a parse error
                    if "raw_content" in json_data:
                        raw_content = json_data.get("raw_content", "")
                        logger.info(f"Raw content length: {len(raw_content)} chars")
                        logger.info(f"Raw content preview (first 500 chars):\n{raw_content[:500]}")
                        
                        # Try to manually extract JSON from raw content
                        logger.info("Attempting manual JSON extraction...")
                        try:
                            # Save raw content for debugging
                            debug_file = os.path.join(self.conversation_dir, f"debug_raw_{int(time.time())}.txt")
                            with open(debug_file, 'w', encoding='utf-8') as f:
                                f.write(raw_content)
                            logger.info(f"Saved raw content to: {debug_file}")
                        except Exception as save_error:
                            logger.debug(f"Could not save debug file: {save_error}")
                    
                    return None
                
                # Normalize JSON to standard format
                normalized_json = self.normalize_conversation_json(json_data)
                if not normalized_json:
                    logger.warning("Could not normalize JSON, using original")
                    normalized_json = json_data
                
                logger.info("✓ Successfully generated conversation")
                return normalized_json
                
            except Exception as e:
                logger.error(f"Error generating conversation: {e}", exc_info=True)
                return None
    
    def validate_conversation_json(self, json_data: Dict[str, Any]) -> bool:
        """
        Kiểm tra tính hợp lệ của conversation JSON
        
        Expected format:
        {
            "speakers": [
                {"speaker": "A", "text": "..."},
                {"speaker": "B", "text": "..."}
            ]
        }
        
        Args:
            json_data: JSON data cần validate
            
        Returns:
            True nếu hợp lệ, False nếu không
        """
        try:
            # Check if JSON parse failed (has raw_content or error)
            if "raw_content" in json_data or "error" in json_data:
                logger.error("JSON contains parsing errors")
                if "error" in json_data:
                    logger.error(f"Parse error: {json_data.get('error')}")
                if "raw_content" in json_data:
                    raw_content = json_data.get('raw_content', '')
                    logger.debug(f"Raw content (first 200 chars): {raw_content[:200]}")
                return False
            
            # Check for "conversation" or "speakers" key
            if "speakers" in json_data:
                conversation = json_data["speakers"]
                logger.info("Found 'speakers' key (Perplexity format)")
            elif "conversation" in json_data:
                conversation = json_data["conversation"]
                logger.info("Found 'conversation' key (alternative format)")
            else:
                logger.error("Missing 'speakers' or 'conversation' key in JSON")
                logger.debug(f"Available keys: {list(json_data.keys())}")
                return False
            
            # Check if conversation is a list
            if not isinstance(conversation, list):
                logger.error(f"'conversation'/'speakers' must be a list, got {type(conversation)}")
                return False
            
            # Check if list is not empty
            if len(conversation) == 0:
                logger.error("'conversation'/'speakers' list is empty")
                return False
            
            # Validate each dialogue entry
            required_fields = ["speaker", "text"]  # Basic required fields
            for i, entry in enumerate(conversation):
                if not isinstance(entry, dict):
                    logger.error(f"Entry {i} is not a dict, got {type(entry)}")
                    return False
                
                # Check for required fields (flexible - either 'speaker' or 'name')
                has_speaker = any(key in entry for key in ["speaker", "name", "speaker_id"])
                has_text = any(key in entry for key in ["text", "dialogue", "content"])
                
                if not has_speaker:
                    logger.error(f"Entry {i} missing speaker field (tried: speaker, name, speaker_id)")
                    logger.debug(f"Entry {i} keys: {list(entry.keys())}")
                    return False
                
                if not has_text:
                    logger.error(f"Entry {i} missing text field (tried: text, dialogue, content)")
                    logger.debug(f"Entry {i} keys: {list(entry.keys())}")
                    return False
            
            logger.info(f"✓ Validated conversation with {len(conversation)} entries")
            return True
            
        except Exception as e:
            logger.error(f"Error validating JSON: {e}", exc_info=True)
            return False
    
    def normalize_conversation_json(self, json_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normalize conversation JSON to standard format
        Handles different field names (speaker/name, text/dialogue/content)
        
        Args:
            json_data: Raw JSON data
            
        Returns:
            Normalized JSON with standard field names or None if failed
        """
        try:
            if not self.validate_conversation_json(json_data):
                logger.error("Cannot normalize invalid JSON")
                return None
            
            # Get conversation array
            if "speakers" in json_data:
                conversation = json_data["speakers"]
            elif "conversation" in json_data:
                conversation = json_data["conversation"]
            else:
                return None
            
            # Normalize each entry
            normalized = []
            for entry in conversation:
                # 🔥 CRITICAL: Keep ALL original fields first
                normalized_entry = entry.copy()  # Copy all original fields
                normalized.append(normalized_entry)
            
            result = {"speakers": normalized}
            logger.info(f"✓ Normalized {len(normalized)} conversation entries")
            return result
            
        except Exception as e:
            logger.error(f"Error normalizing JSON: {e}", exc_info=True)
            return None
    
    def save_conversation_json(self, 
                              json_data: Dict[str, Any], 
                              filename: Optional[str] = None) -> Optional[str]:
        """
        Lưu conversation JSON xuống file
        
        Args:
            json_data: Data cần lưu
            filename: Tên file (không bao gồm extension), tự động tạo nếu None
            
        Returns:
            Đường dẫn file đã lưu hoặc None nếu thất bại
        """
        try:
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"conversation_perplexity_{timestamp}"
            
            # Ensure .json extension
            if not filename.endswith('.json'):
                filename += '.json'
            
            filepath = os.path.join(self.conversation_dir, filename)
            
            # Save JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✓ Saved conversation to: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving conversation JSON: {e}", exc_info=True)
            return None
    
    def load_conversation_json(self, filepath: str) -> Optional[Dict[str, Any]]:
        """
        Đọc conversation JSON từ file
        
        Args:
            filepath: Đường dẫn file cần đọc
            
        Returns:
            Dict chứa data hoặc None nếu thất bại
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            logger.info(f"✓ Loaded conversation from: {filepath}")
            return json_data
            
        except Exception as e:
            logger.error(f"Error loading conversation JSON: {e}", exc_info=True)
            return None
    
    def convert_to_gemini_format(self, 
                                 conversation_json: Dict[str, Any],
                                 voice_mapping: Optional[Dict[str, str]] = None) -> List[Dict[str, str]]:
        """
        Chuyển đổi conversation JSON sang format phù hợp cho Gemini TTS
        
        Args:
            conversation_json: Conversation data từ Perplexity
            voice_mapping: Mapping từ speaker name sang voice name
                          Ví dụ: {"A": "Puck", "B": "Charon"}
            
        Returns:
            List of segments ready for Gemini TTS
            Format: [{"speaker": "A", "voice": "Puck", "text": "..."}, ...]
        """
        try:
            if not self.validate_conversation_json(conversation_json):
                logger.error("Invalid conversation JSON")
                return []
            
            conversation = conversation_json.get("conversation", conversation_json.get("speakers", []))
            
            # Default voice mapping if not provided
            if not voice_mapping:
                voice_mapping = self._get_default_voice_mapping(conversation)
            
            # Convert to Gemini format
            gemini_segments = []
            for entry in conversation:
                speaker = entry["speaker"]
                text = entry["text"]
                
                # Get voice for speaker
                voice = voice_mapping.get(speaker, "Puck")  # Default voice
                
                gemini_segments.append({
                    "speaker": speaker,
                    "voice": voice,
                    "text": text
                })
            
            logger.info(f"✓ Converted {len(gemini_segments)} segments to Gemini format")
            return gemini_segments
            
        except Exception as e:
            logger.error(f"Error converting to Gemini format: {e}", exc_info=True)
            return []
    
    def _get_default_voice_mapping(self, conversation: List[Dict[str, str]]) -> Dict[str, str]:
        """
        Tạo default voice mapping từ conversation
        Tự động assign voices cho các speakers
        
        Args:
            conversation: List of conversation entries
            
        Returns:
            Dict mapping speaker to voice
        """
        # Available voices (based on Gemini TTS)
        available_voices = [
            "Puck", "Charon", "Kore", "Fenrir", "Aoede",
            "Orbit", "Arcas", "Pegasus", "Atlas", "Lyra"
        ]
        
        # Get unique speakers
        speakers = list(set(entry["speaker"] for entry in conversation))
        speakers.sort()  # Sort for consistency
        
        # Create mapping
        voice_mapping = {}
        for i, speaker in enumerate(speakers):
            voice_mapping[speaker] = available_voices[i % len(available_voices)]
        
        logger.info(f"Created default voice mapping: {voice_mapping}")
        return voice_mapping
    
    def create_conversation_full_workflow(self,
                                         chapter_content: str = None,
                                         story_name: str = None,
                                         story_id: int = None,
                                         chapter_number: int = None,
                                         voice_mapping: Optional[Dict[str, str]] = None,
                                         save_to_file: bool = True,
                                         filename: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Quy trình đầy đủ: Tạo conversation từ Perplexity → Validate → Save → Convert

        Args:
            chapter_content: Nội dung chapter (Perplexity sẽ tự tạo prompt)
            story_name: Tên story (BẮT BUỘC)
            story_id: ID story (optional)
            chapter_number: Số chương (for context)
            voice_mapping: Mapping speaker to voice
            save_to_file: Có lưu JSON xuống file không
            filename: Tên file để lưu (optional)

        Returns:
            Dict chứa:
            {
                "raw_json": {...},  # JSON gốc từ Perplexity
                "gemini_segments": [...],  # Segments cho Gemini
                "filepath": "..."  # Đường dẫn file đã lưu (nếu có)
            }
        """
        with LogBlock(logger, "Full conversation workflow"):
            result = {
                "raw_json": None,
                "gemini_segments": [],
                "filepath": None
            }

            try:
                # Step 1: Generate conversation from Perplexity
                logger.info("Step 1: Generating conversation from Perplexity")

                if chapter_content and story_name:
                    logger.info("Using chapter_content (Perplexity will create its own prompt)")
                    raw_json = self.generate_conversation_from_prompt(
                        chapter_content=chapter_content,
                        story_name=story_name,
                        story_id=story_id,
                        chapter_number=chapter_number
                    )
                else:
                    logger.error("chapter_content and story_name must be provided")
                    return None
                
                if not raw_json:
                    logger.error("Failed to generate conversation")
                    return None
                
                result["raw_json"] = raw_json
                
                # Step 2: Save to file (optional)
                if save_to_file:
                    logger.info("Step 2: Saving conversation to file")
                    filepath = self.save_conversation_json(raw_json, filename)
                    result["filepath"] = filepath
                
                logger.info("✓ Full workflow completed successfully")
                return result
                
            except Exception as e:
                logger.error(f"Error in full workflow: {e}", exc_info=True)
                return None
    
    def list_saved_conversations(self) -> List[str]:
        """
        Liệt kê tất cả các conversation đã lưu
        
        Returns:
            List of conversation filenames
        """
        try:
            files = [f for f in os.listdir(self.conversation_dir) 
                    if f.endswith('.json') and 'perplexity' in f.lower()]
            files.sort(reverse=True)  # Newest first
            return files
        except Exception as e:
            logger.error(f"Error listing conversations: {e}")
            return []
    
    def generate_image_prompts_from_chapter(self,
                                             chapter_content: str = None,
                                             story_name: str = None,
                                             story_id: int = None,
                                             chapter_number: int = None,
                                             timeout: int = 1800) -> Optional[Dict[str, Any]]:
        """
        Tạo image prompts từ chapter content sử dụng Perplexity AI
        Lưu vào story folder: audio_downloads/<story_name>/image_prompts/

        Args:
            chapter_content: Nội dung chapter
            story_name: Tên story (BẮT BUỘC)
            story_id: ID của story
            chapter_number: Số chương
            timeout: Thời gian chờ response (giây)

        Returns:
            Dict chứa image prompts data hoặc None nếu thất bại
        """
        with LogBlock(logger, f"Generate image prompts for chapter {chapter_number}"):
            try:
                automation = self.get_automation()

                if not chapter_content or not story_name:
                    logger.error("chapter_content and story_name must be provided")
                    return None

                logger.info(f"Using chapter_content for image prompts (story {story_id}, chapter {chapter_number})")
                json_data = automation.generate_image_prompts(
                    chapter_content=chapter_content,
                    story_name=story_name,
                    story_id=story_id,
                    chapter_number=chapter_number,
                    timeout=timeout,
                    save_to_file=True  # Auto-save to story folder
                )
                
                if not json_data:
                    logger.error("Failed to get image prompts from Perplexity")
                    return None
                
                logger.info("✓ Image prompts generated successfully")
                return json_data
                
            except Exception as e:
                logger.error(f"Error generating image prompts: {e}", exc_info=True)
                return None
    
    def generate_image_prompts_batch(self,
                                      chapters: List[Dict[str, Any]],
                                      story_name: str,
                                      story_id: int,
                                      delay_between_chapters: int = 3,
                                      stop_on_error: bool = False) -> List[Dict[str, Any]]:
        """
        Tạo image prompts cho nhiều chapters tuần tự (batch processing)
        
        Args:
            chapters: List of chapter dicts với keys 'content' và 'number'
            story_id: ID của story
            delay_between_chapters: Delay giữa các chapters (giây)
            stop_on_error: Dừng khi gặp lỗi hay tiếp tục
            
        Returns:
            List of results cho từng chapter
        """
        with LogBlock(logger, f"Generate image prompts batch: {len(chapters)} chapters"):
            results = []
            
            for idx, chapter in enumerate(chapters, 1):
                chapter_number = chapter.get('number')
                chapter_content = chapter.get('content')
                
                logger.info(f"Processing chapter {idx}/{len(chapters)}: Chapter {chapter_number}")
                
                try:
                    result = self.generate_image_prompts_from_chapter(
                        chapter_content=chapter_content,
                        story_name=story_name,
                        story_id=story_id,
                        chapter_number=chapter_number
                    )
                    
                    results.append({
                        'chapter_number': chapter_number,
                        'success': result is not None,
                        'data': result,
                        'error': None if result else 'Failed to generate'
                    })
                    
                    if result:
                        logger.info(f"✓ Chapter {chapter_number}: Success")
                    else:
                        logger.error(f"✗ Chapter {chapter_number}: Failed")
                        if stop_on_error:
                            logger.warning("Stopping batch due to error")
                            break
                    
                    # Delay between chapters
                    if idx < len(chapters):
                        logger.info(f"Waiting {delay_between_chapters}s before next chapter...")
                        time.sleep(delay_between_chapters)
                    
                except Exception as e:
                    logger.error(f"Error processing chapter {chapter_number}: {e}", exc_info=True)
                    results.append({
                        'chapter_number': chapter_number,
                        'success': False,
                        'data': None,
                        'error': str(e)
                    })
                    
                    if stop_on_error:
                        logger.warning("Stopping batch due to error")
                        break
            
            # Summary
            success_count = sum(1 for r in results if r['success'])
            logger.info(f"Batch complete: {success_count}/{len(results)} successful")
            
            return results
    
    def close(self):
        """Đóng automation và cleanup"""
        if self._automation:
            logger.info("Closing Perplexity automation")
            self._automation.close()
            self._automation = None
