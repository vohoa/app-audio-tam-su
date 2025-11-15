"""
Conversation Manager Module
Quản lý và xử lý các conversation JSON files
Cung cấp utilities để lưu, đọc, validate và quản lý conversations
"""

import os
import json
import shutil
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime

from logger_config import LoggerConfig

# Initialize logger
logger = LoggerConfig.get_logger('conversation_manager')


class ConversationManager:
    """
    Class quản lý conversations JSON
    - Lưu/đọc/xóa conversations
    - Validate format
    - Export/import
    - Metadata tracking
    """
    
    def __init__(self, conversations_dir: Optional[str] = None):
        """
        Khởi tạo Conversation Manager
        
        Args:
            conversations_dir: Thư mục chứa conversation files
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.conversations_dir = conversations_dir or os.path.join(
            current_dir, 'conversations'
        )
        
        # Tạo thư mục nếu chưa có
        os.makedirs(self.conversations_dir, exist_ok=True)
        logger.info(f"Conversations directory: {self.conversations_dir}")
    
    def save_conversation(self, 
                         conversation_data: Dict[str, Any],
                         filename: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Lưu conversation với metadata
        
        Args:
            conversation_data: Conversation JSON data
            filename: Tên file (optional, tự động tạo nếu None)
            metadata: Metadata bổ sung (optional)
            
        Returns:
            Đường dẫn file đã lưu hoặc None nếu thất bại
        """
        try:
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"conversation_{timestamp}.json"
            
            # Ensure .json extension
            if not filename.endswith('.json'):
                filename += '.json'
            
            filepath = os.path.join(self.conversations_dir, filename)
            
            # Prepare data with metadata
            save_data = {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "filename": filename,
                    **(metadata or {})
                },
                "conversation": conversation_data
            }
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✓ Saved conversation: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving conversation: {e}", exc_info=True)
            return None
    
    def load_conversation(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Đọc conversation từ file
        
        Args:
            filename: Tên file hoặc đường dẫn đầy đủ
            
        Returns:
            Dict chứa conversation data hoặc None nếu thất bại
        """
        try:
            # Handle both filename and full path
            if not os.path.isabs(filename):
                filepath = os.path.join(self.conversations_dir, filename)
            else:
                filepath = filename
            
            if not os.path.exists(filepath):
                logger.error(f"File not found: {filepath}")
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"✓ Loaded conversation: {filepath}")
            return data
            
        except Exception as e:
            logger.error(f"Error loading conversation: {e}", exc_info=True)
            return None
    
    def list_conversations(self, sort_by: str = "date", reverse: bool = True) -> List[Dict[str, Any]]:
        """
        Liệt kê tất cả conversations
        
        Args:
            sort_by: Sắp xếp theo "date" hoặc "name"
            reverse: Sắp xếp ngược (newest first)
            
        Returns:
            List of conversation info dicts
        """
        try:
            conversations = []
            
            for filename in os.listdir(self.conversations_dir):
                if not filename.endswith('.json'):
                    continue
                
                filepath = os.path.join(self.conversations_dir, filename)
                
                try:
                    # Load basic info
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Extract metadata
                    metadata = data.get("metadata", {})
                    conversation = data.get("conversation", {})
                    
                    # Count dialogues
                    dialogue_count = 0
                    if isinstance(conversation, dict) and "conversation" in conversation:
                        dialogue_count = len(conversation["conversation"])
                    
                    # Get speakers
                    speakers = set()
                    if isinstance(conversation, dict) and "conversation" in conversation:
                        for entry in conversation["conversation"]:
                            if "speaker" in entry:
                                speakers.add(entry["speaker"])
                    
                    info = {
                        "filename": filename,
                        "filepath": filepath,
                        "created_at": metadata.get("created_at", "Unknown"),
                        "dialogue_count": dialogue_count,
                        "speakers": list(speakers),
                        "metadata": metadata
                    }
                    
                    conversations.append(info)
                    
                except Exception as e:
                    logger.warning(f"Error reading {filename}: {e}")
                    continue
            
            # Sort
            if sort_by == "date":
                conversations.sort(key=lambda x: x["created_at"], reverse=reverse)
            else:  # by name
                conversations.sort(key=lambda x: x["filename"], reverse=reverse)
            
            logger.info(f"Found {len(conversations)} conversations")
            return conversations
            
        except Exception as e:
            logger.error(f"Error listing conversations: {e}", exc_info=True)
            return []
    
    def delete_conversation(self, filename: str) -> bool:
        """
        Xóa conversation file
        
        Args:
            filename: Tên file cần xóa
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            filepath = os.path.join(self.conversations_dir, filename)
            
            if not os.path.exists(filepath):
                logger.error(f"File not found: {filepath}")
                return False
            
            os.remove(filepath)
            logger.info(f"✓ Deleted conversation: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}", exc_info=True)
            return False
    
    def validate_conversation_format(self, conversation_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate conversation data format
        
        Args:
            conversation_data: Data cần validate
            
        Returns:
            Tuple (is_valid, error_message)
        """
        try:
            # Check if it has conversation key
            if "conversation" not in conversation_data:
                return False, "Missing 'conversation' key"
            
            conv = conversation_data["conversation"]
            
            # Check if conversation is dict with conversation array
            if isinstance(conv, dict):
                if "conversation" not in conv:
                    return False, "Missing nested 'conversation' array"
                conv = conv["conversation"]
            
            # Check if it's a list
            if not isinstance(conv, list):
                return False, "'conversation' must be a list"
            
            # Check if not empty
            if len(conv) == 0:
                return False, "'conversation' list is empty"
            
            # Validate each entry
            for i, entry in enumerate(conv):
                if not isinstance(entry, dict):
                    return False, f"Entry {i} is not a dict"
                
                if "speaker" not in entry:
                    return False, f"Entry {i} missing 'speaker'"
                
                if "text" not in entry:
                    return False, f"Entry {i} missing 'text'"
                
                if not entry["text"].strip():
                    return False, f"Entry {i} has empty text"
            
            return True, "Valid"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def get_conversation_stats(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lấy thống kê về conversation
        
        Args:
            conversation_data: Conversation data
            
        Returns:
            Dict chứa các thống kê
        """
        try:
            stats = {
                "total_dialogues": 0,
                "speakers": {},
                "avg_text_length": 0,
                "total_characters": 0
            }
            
            # Get conversation array
            conv = conversation_data.get("conversation", {})
            if isinstance(conv, dict):
                conv = conv.get("conversation", [])
            
            if not isinstance(conv, list):
                return stats
            
            stats["total_dialogues"] = len(conv)
            
            total_length = 0
            for entry in conv:
                speaker = entry.get("speaker", "Unknown")
                text = entry.get("text", "")
                
                # Count by speaker
                if speaker not in stats["speakers"]:
                    stats["speakers"][speaker] = {
                        "count": 0,
                        "total_chars": 0
                    }
                
                stats["speakers"][speaker]["count"] += 1
                stats["speakers"][speaker]["total_chars"] += len(text)
                
                total_length += len(text)
            
            stats["total_characters"] = total_length
            if stats["total_dialogues"] > 0:
                stats["avg_text_length"] = total_length / stats["total_dialogues"]
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}", exc_info=True)
            return {}
    
    def export_conversation(self, 
                          filename: str, 
                          export_path: str,
                          format: str = "json") -> bool:
        """
        Export conversation sang định dạng khác
        
        Args:
            filename: Conversation file cần export
            export_path: Đường dẫn export
            format: Định dạng export ("json", "txt")
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            # Load conversation
            data = self.load_conversation(filename)
            if not data:
                return False
            
            conv = data.get("conversation", {})
            if isinstance(conv, dict):
                conv = conv.get("conversation", [])
            
            if format == "json":
                # Export as clean JSON
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump({"conversation": conv}, f, ensure_ascii=False, indent=2)
            
            elif format == "txt":
                # Export as readable text
                with open(export_path, 'w', encoding='utf-8') as f:
                    for entry in conv:
                        speaker = entry.get("speaker", "Unknown")
                        text = entry.get("text", "")
                        f.write(f"{speaker}: {text}\n\n")
            
            else:
                logger.error(f"Unsupported format: {format}")
                return False
            
            logger.info(f"✓ Exported to: {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting conversation: {e}", exc_info=True)
            return False
    
    def import_conversation(self, 
                          import_path: str,
                          filename: Optional[str] = None) -> Optional[str]:
        """
        Import conversation từ file external
        
        Args:
            import_path: Đường dẫn file cần import
            filename: Tên file đích (optional)
            
        Returns:
            Đường dẫn file đã import hoặc None nếu thất bại
        """
        try:
            # Load and validate
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            is_valid, error_msg = self.validate_conversation_format(data)
            if not is_valid:
                logger.error(f"Invalid format: {error_msg}")
                return None
            
            # Save to conversations dir
            if not filename:
                filename = os.path.basename(import_path)
            
            return self.save_conversation(data, filename)
            
        except Exception as e:
            logger.error(f"Error importing conversation: {e}", exc_info=True)
            return None
    
    def search_conversations(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Tìm kiếm conversations theo keyword
        
        Args:
            keyword: Từ khóa tìm kiếm
            
        Returns:
            List of matching conversations
        """
        try:
            keyword_lower = keyword.lower()
            results = []
            
            for conv_info in self.list_conversations():
                # Search in filename
                if keyword_lower in conv_info["filename"].lower():
                    results.append(conv_info)
                    continue
                
                # Search in metadata
                metadata = conv_info.get("metadata", {})
                metadata_str = json.dumps(metadata, ensure_ascii=False).lower()
                if keyword_lower in metadata_str:
                    results.append(conv_info)
                    continue
                
                # Search in conversation content
                data = self.load_conversation(conv_info["filename"])
                if data:
                    conv = data.get("conversation", {})
                    if isinstance(conv, dict):
                        conv = conv.get("conversation", [])
                    
                    for entry in conv:
                        text = entry.get("text", "").lower()
                        if keyword_lower in text:
                            results.append(conv_info)
                            break
            
            logger.info(f"Found {len(results)} conversations matching '{keyword}'")
            return results
            
        except Exception as e:
            logger.error(f"Error searching conversations: {e}", exc_info=True)
            return []


# Example usage
if __name__ == "__main__":
    manager = ConversationManager()
    
    # Test save and load
    test_conversation = {
        "conversation": {
            "conversation": [
                {"speaker": "A", "text": "Hello, how are you?"},
                {"speaker": "B", "text": "I'm fine, thank you!"}
            ]
        }
    }
    
    # Save
    filepath = manager.save_conversation(
        test_conversation, 
        "test_conversation.json",
        metadata={"topic": "greeting"}
    )
    print(f"Saved: {filepath}")
    
    # List
    conversations = manager.list_conversations()
    print(f"\nFound {len(conversations)} conversations:")
    for conv in conversations:
        print(f"  - {conv['filename']} ({conv['dialogue_count']} dialogues)")
    
    # Load and stats
    data = manager.load_conversation("test_conversation.json")
    if data:
        stats = manager.get_conversation_stats(data)
        print(f"\nStats: {stats}")
    
    # Search
    results = manager.search_conversations("hello")
    print(f"\nSearch results: {len(results)} found")
