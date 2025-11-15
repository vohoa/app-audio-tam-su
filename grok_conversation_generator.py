"""
Grok Conversation Generator Module
Xử lý tạo hội thoại thông qua Grok AI và chuyển đổi sang định dạng phù hợp cho Gemini TTS
"""

import os
import json
import time
from typing import Optional, Dict, List, Any
from datetime import datetime

from logger_config import LoggerConfig, LogBlock
from grok_ai_automation import GrokAIAutomation

# Initialize logger
logger = LoggerConfig.get_logger('grok_conversation')


class GrokConversationGenerator:
    """
    Class xử lý việc tạo hội thoại từ Grok AI và chuyển đổi sang format cho Gemini
    """
    
    def __init__(self, 
                 conversation_dir: Optional[str] = None,
                 headless: bool = False,
                 profile_name: str = "grok_ai"):
        """
        Khởi tạo Grok Conversation Generator
        
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
        
        # Grok automation instance (lazy initialization)
        self._automation = None
    
    def get_automation(self) -> GrokAIAutomation:
        """
        Lấy hoặc tạo mới automation instance
        
        Returns:
            GrokAIAutomation instance
        """
        if self._automation is None:
            logger.info("Creating new Grok automation instance")
            self._automation = GrokAIAutomation(
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
        Tạo hội thoại từ chapter content sử dụng Grok AI

        Args:
            chapter_content: Nội dung chapter (Grok sẽ tự tạo prompt)
            story_name: Tên story (BẮT BUỘC nếu save_to_file=True)
            story_id: ID story (optional)
            chapter_number: Số chương (for context)
            timeout: Thời gian chờ response (giây)

        Returns:
            Dict chứa conversation data hoặc None nếu thất bại
        """
        with LogBlock(logger, "Generate conversation from Grok AI"):
            try:
                automation = self.get_automation()

                # Prefer chapter_content over prompt
                if chapter_content and story_name:
                    logger.info("Using chapter_content (Grok will create prompt)")
                    # Use the new generate_conversation_json method that accepts chapter_content
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
                    logger.error("Failed to get JSON from Grok")
                    return None
                
                # Validate JSON structure
                if not self.validate_conversation_json(json_data):
                    logger.error("Invalid conversation JSON structure")
                    return None
                
                logger.info("✓ Successfully generated conversation")
                return json_data
                
            except Exception as e:
                logger.error(f"Error generating conversation: {e}", exc_info=True)
                return None
    
    def validate_conversation_json(self, json_data: Dict[str, Any]) -> bool:
        """
        Kiểm tra tính hợp lệ của conversation JSON
        
        Expected format:
        {
            "conversation": [
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
            # Check for "conversation" or "speakers" key (support both formats)
            if "speakers" in json_data:
                conversation = json_data["speakers"]
                logger.info("Found 'speakers' key (Grok format)")
            else:
                logger.error("Missing 'conversation' or 'speakers' key in JSON")
                return False
            
            # Check if conversation is a list
            if not isinstance(conversation, list):
                logger.error("'conversation'/'speakers' must be a list")
                return False
            
            # Check if list is not empty
            if len(conversation) == 0:
                logger.error("'conversation'/'speakers' list is empty")
                return False
            
            # Validate each dialogue entry
            for i, entry in enumerate(conversation):
                if not isinstance(entry, dict):
                    logger.error(f"Entry {i} is not a dict")
                    return False
            
            logger.info(f"✓ Validated conversation with {len(conversation)} entries")
            return True
            
        except Exception as e:
            logger.error(f"Error validating JSON: {e}", exc_info=True)
            return False
    
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
                filename = f"conversation_{timestamp}"
            
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
            conversation_json: Conversation data từ Grok
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
            
            conversation = conversation_json["conversation"]
            
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
        Quy trình đầy đủ: Tạo conversation từ Grok → Validate → Save → Convert

        Args:
            chapter_content: Nội dung chapter (Grok sẽ tự tạo prompt)
            story_name: Tên story (BẮT BUỘC)
            story_id: ID story (optional)
            chapter_number: Số chương (for context)
            voice_mapping: Mapping speaker to voice
            save_to_file: Có lưu JSON xuống file không
            filename: Tên file để lưu (optional)

        Returns:
            Dict chứa:
            {
                "raw_json": {...},  # JSON gốc từ Grok
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
                # Step 1: Generate conversation from Grok
                logger.info("Step 1: Generating conversation from Grok")

                if chapter_content and story_name:
                    logger.info("Using chapter_content (Grok will create its own prompt)")
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
                    if f.endswith('.json')]
            files.sort(reverse=True)  # Newest first
            return files
        except Exception as e:
            logger.error(f"Error listing conversations: {e}")
            return []
    
    def close(self):
        """Đóng automation và cleanup"""
        if self._automation:
            logger.info("Closing Grok automation")
            self._automation.close()
            self._automation = None
