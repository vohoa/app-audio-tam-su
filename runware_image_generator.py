"""
Runware Image Generator
Tạo hình ảnh từ prompts sử dụng Runware API
"""

import os
import json
import asyncio
import logging
import re
from typing import Optional, Dict, Any, List, Union
from pathlib import Path

try:
    from runware import Runware, IImageInference, IInstantID, ILora
except ImportError:
    print("⚠️ Runware SDK chưa được cài đặt. Chạy: pip install runware")
    Runware = None
    IImageInference = None
    IInstantID = None
    ILora = None

try:
    from unidecode import unidecode
except ImportError:
    # Fallback nếu không cài unidecode
    def unidecode(text):
        return text

import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def convert_lora_to_objects(lora_list: Optional[List[Dict[str, Any]]]) -> Optional[List]:
    """
    Convert LoRA dictionary list to ILora object list

    Args:
        lora_list: List of LoRA dicts [{"model": "...", "weight": 1.0}, ...]

    Returns:
        List of ILora objects or None
    """
    if not lora_list or not ILora:
        return None

    try:
        lora_objects = []
        for lora_dict in lora_list:
            if isinstance(lora_dict, dict):
                lora_obj = ILora(
                    model=lora_dict.get("model"),
                    weight=lora_dict.get("weight", 1.0)
                )
                lora_objects.append(lora_obj)
        return lora_objects if lora_objects else None
    except Exception as e:
        logger.error(f"Failed to convert LoRA to objects: {e}")
        return None


class CharacterManager:
    """Quản lý character database và reference images để đồng bộ nhân vật qua các cảnh"""

    def __init__(self, characters_json_path: Optional[str] = None):
        """
        Khởi tạo CharacterManager

        Args:
            characters_json_path: Đường dẫn đến file characters.json
        """
        self.characters_json_path = characters_json_path
        self.characters_data = {}

        if characters_json_path and os.path.exists(characters_json_path):
            self.load_characters(characters_json_path)

    def load_characters(self, json_path: str) -> bool:
        """Load character database từ JSON file"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.characters_data = data.get('characters', {})
                logger.info(f"✓ Loaded {len(self.characters_data)} characters from {json_path}")
                return True
        except Exception as e:
            logger.error(f"Failed to load characters: {e}")
            return False

    def get_character_info(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Lấy thông tin của nhân vật"""
        return self.characters_data.get(character_id)

    def get_reference_image(self, character_id: str, base_path: str = None) -> Optional[str]:
        """
        Lấy đường dẫn đến reference image của nhân vật

        Args:
            character_id: ID của nhân vật (vd: "han_lap")
            base_path: Thư mục gốc (mặc định: cùng folder với characters.json)

        Returns:
            Đường dẫn tuyệt đối đến reference image hoặc None
        """
        char_info = self.get_character_info(character_id)
        if not char_info or 'reference_image' not in char_info:
            return None

        ref_path = char_info['reference_image']

        # Nếu là đường dẫn tuyệt đối
        if os.path.isabs(ref_path):
            return ref_path if os.path.exists(ref_path) else None

        # Nếu là đường dẫn tương đối
        if base_path is None and self.characters_json_path:
            base_path = os.path.dirname(self.characters_json_path)

        if base_path:
            full_path = os.path.join(base_path, ref_path)
            return full_path if os.path.exists(full_path) else None

        return None

    def detect_characters_in_text(self, text: str) -> List[str]:
        """
        Tự động phát hiện nhân vật trong text dựa trên tên và aliases

        Args:
            text: Text cần phân tích (prompt)

        Returns:
            List các character IDs được tìm thấy
        """
        found_characters = []
        text_lower = text.lower()
        text_normalized = unidecode(text_lower)

        for char_id, char_info in self.characters_data.items():
            # Check full name
            full_name = char_info.get('full_name', '')
            if full_name and full_name.lower() in text_lower:
                found_characters.append(char_id)
                continue

            # Check aliases
            aliases = char_info.get('aliases', [])
            for alias in aliases:
                if alias.lower() in text_lower:
                    found_characters.append(char_id)
                    break

            # Check normalized version
            if char_id.replace('_', ' ') in text_normalized:
                if char_id not in found_characters:
                    found_characters.append(char_id)

        return found_characters

    def extract_characters_from_metadata(self, prompt_data: Dict[str, Any]) -> List[str]:
        """
        Lấy danh sách nhân vật từ metadata của prompt

        Args:
            prompt_data: Dict chứa thông tin prompt (từ JSON)

        Returns:
            List các character IDs
        """
        if isinstance(prompt_data, dict) and 'characters' in prompt_data:
            return prompt_data['characters']
        return []


class RunwareImageGenerator:
    """
    Class để tạo hình ảnh từ prompts sử dụng Runware API
    """
    
    def __init__(self, api_key: str = None):
        """
        Khởi tạo Runware Image Generator

        Args:
            api_key: Runware API key (None = lấy từ config)
        """
        if Runware is None or IImageInference is None:
            raise ImportError("Runware SDK chưa được cài đặt. Chạy: pip install runware")

        self.api_key = api_key or getattr(config, 'RUNWARE_API_KEY', None)

        if not self.api_key:
            raise ValueError("RUNWARE_API_KEY không được tìm thấy trong config")

        self.runware = None
        self.is_connected = False

        # Validate API key format
        if not self.api_key or len(self.api_key.strip()) < 10:
            logger.warning("⚠️ API key format may be invalid")

        logger.info("✓ RunwareImageGenerator initialized")
    
    async def connect(self, timeout: int = 30, max_retries: int = 3):
        """
        Kết nối đến Runware API với timeout và retry logic

        Args:
            timeout: Timeout cho mỗi lần thử kết nối (giây)
            max_retries: Số lần thử lại tối đa
        """
        for attempt in range(max_retries):
            try:
                if not self.runware:
                    self.runware = Runware(api_key=self.api_key)

                if not self.is_connected:
                    logger.info(f"Attempting to connect to Runware API (attempt {attempt + 1}/{max_retries})...")

                    # Add timeout to connect operation
                    await asyncio.wait_for(
                        self.runware.connect(),
                        timeout=timeout
                    )

                    self.is_connected = True
                    logger.info("✓ Connected to Runware API")

                return True

            except asyncio.TimeoutError:
                logger.warning(f"Connection timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Failed to connect: All retry attempts exhausted")

            except Exception as e:
                logger.error(f"Failed to connect to Runware on attempt {attempt + 1}: {e}", exc_info=True)
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Failed to connect: All retry attempts exhausted")

        return False
    
    async def disconnect(self):
        """Ngắt kết nối Runware API"""
        try:
            if self.runware and self.is_connected:
                await self.runware.disconnect()
                self.is_connected = False
                logger.info("✓ Disconnected from Runware API")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")

    def validate_api_key(self) -> bool:
        """
        Validate API key format

        Returns:
            True if API key appears valid
        """
        if not self.api_key:
            logger.error("API key is empty")
            return False

        if len(self.api_key) < 10:
            logger.error("API key seems too short")
            return False

        logger.info("API key format appears valid")
        return True
    
    async def generate_image(self,
                            prompt: str,
                            model: str = "runware:101@1",
                            width: int = 1024,
                            height: int = 1024,
                            max_retries: int = 2,
                            character_references: Optional[List[str]] = None,
                            instant_id_strength: float = 0.8,
                            lora: Optional[List[Dict[str, Any]]] = None,
                            **kwargs) -> Optional[List[Dict[str, Any]]]:
        """
        Tạo hình ảnh từ prompt với retry logic và hỗ trợ character consistency

        Args:
            prompt: Prompt text
            model: Model ID (default: runware:101@1)
            width: Chiều rộng ảnh
            height: Chiều cao ảnh
            max_retries: Số lần thử lại tối đa
            character_references: List đường dẫn đến reference images của nhân vật
            instant_id_strength: Độ mạnh InstantID (0.0-1.0), cao hơn = giống reference hơn
            lora: List LoRA models với format [{"model": "civitai:xxx@xxx", "weight": 1.0}, ...]
            **kwargs: Các tham số bổ sung

        Returns:
            List of image data hoặc None
        """
        for attempt in range(max_retries):
            try:
                # Ensure connection
                if not self.is_connected:
                    logger.info("Not connected, attempting to connect...")
                    connected = await self.connect()
                    if not connected:
                        logger.error("Failed to establish connection")
                        return None

                logger.info(f"Generating image with prompt: {prompt[:100]}...")

                # Prepare request parameters
                request_params = {
                    "positivePrompt": prompt,
                    "model": model,
                    "width": width,
                    "height": height,
                    **kwargs
                }

                # Add LoRA if provided
                if lora and len(lora) > 0:
                    logger.info(f"Using {len(lora)} LoRA model(s)")
                    # Convert dict to ILora objects
                    lora_objects = convert_lora_to_objects(lora)
                    if lora_objects:
                        request_params["lora"] = lora_objects

                # Add InstantID if character references provided
                if character_references and len(character_references) > 0 and IInstantID:
                    ref_image = character_references[0]  # Dùng reference đầu tiên
                    if os.path.exists(ref_image):
                        logger.info(f"Using character reference: {ref_image} (strength: {instant_id_strength})")
                        request_params["instantID"] = IInstantID(
                            faceImage=ref_image,
                            strength=instant_id_strength
                        )
                    else:
                        logger.warning(f"Character reference not found: {ref_image}")

                # Create inference request
                request = IImageInference(**request_params)

                # Generate image with timeout
                images = await asyncio.wait_for(
                    self.runware.imageInference(requestImage=request),
                    timeout=60  # 60 second timeout for image generation
                )

                if images:
                    logger.info(f"✓ Generated {len(images)} image(s)")
                    return images
                else:
                    logger.warning("No images returned")
                    return None

            except asyncio.TimeoutError:
                logger.error(f"Image generation timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    logger.info("Retrying image generation...")
                    # Mark as disconnected to force reconnect
                    self.is_connected = False
                    await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Failed to generate image on attempt {attempt + 1}: {e}", exc_info=True)

                # Check if it's a connection error
                if "connect" in str(e).lower() or "websocket" in str(e).lower():
                    logger.warning("Connection lost, marking as disconnected")
                    self.is_connected = False

                    if attempt < max_retries - 1:
                        logger.info("Attempting to reconnect...")
                        await asyncio.sleep(2)
                    else:
                        return None
                else:
                    # Non-connection error, don't retry
                    return None

        logger.error("Failed to generate image after all retries")
        return None
    
    async def generate_images_from_json(self,
                                       json_path: str,
                                       output_dir: str = None,
                                       story_name: str = None,
                                       story_id: int = None,
                                       chapter_number: int = None,
                                       model: str = "civitai:118441@162380",
                                       width: int = 768,
                                       height: int = 1344,
                                       characters_json_path: Optional[str] = None,
                                       instant_id_strength: float = 0.8,
                                       lora: Optional[List[Dict[str, Any]]] = None,
                                       auto_create_characters_template: bool = False,
                                       language: str = 'vi') -> Dict[str, Any]:
        """
        Tạo hình ảnh từ file JSON chứa prompts với hỗ trợ character consistency

        Args:
            json_path: Đường dẫn đến file JSON
            output_dir: Thư mục lưu ảnh (None = auto, sẽ dùng story folder nếu có story_name)
            story_name: Tên story (để tạo folder trong audio_downloads)
            story_id: ID story (fallback nếu không có story_name)
            chapter_number: Số chương (để tạo tên folder)
            model: Model ID
            width: Chiều rộng ảnh
            height: Chiều cao ảnh
            characters_json_path: Đường dẫn đến file characters.json (None = tự tìm)
            instant_id_strength: Độ mạnh InstantID (0.0-1.0)
            lora: List LoRA models với format [{"model": "civitai:xxx@xxx", "weight": 1.0}, ...] (None = dùng config từ .env)
            auto_create_characters_template: Tự động tạo template nếu không tìm thấy

        Returns:
            Dict với thông tin kết quả
        """
        try:
            # Use LoRA from config if not provided
            if lora is None:
                lora = config.RUNWARE_LORA_CONFIG
                if lora and len(lora) > 0:
                    logger.info(f"Using LoRA config from .env: {lora}")

            # Read JSON file
            logger.info(f"Reading prompts from: {json_path}")

            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract prompts
            prompts = []

            if isinstance(data, dict):
                if "prompts" in data:
                    prompts = data["prompts"]
                else:
                    logger.error("Không tìm thấy prompts trong JSON")
                    return {"success": False, "error": "Invalid JSON structure"}
            elif isinstance(data, list):
                prompts = data
            else:
                logger.error("JSON format không hợp lệ")
                return {"success": False, "error": "Invalid JSON format"}

            logger.info(f"Found {len(prompts)} prompts")

            # Initialize CharacterManager nếu có characters.json
            char_manager = None
            if characters_json_path is None:
                # Tự tìm characters.json trong cùng thư mục với prompts
                json_dir = os.path.dirname(json_path) or "."
                auto_char_path = os.path.join(json_dir, 'characters.json')

                if os.path.exists(auto_char_path):
                    characters_json_path = auto_char_path
                    logger.info(f"Auto-detected characters.json: {auto_char_path}")
                else:
                    # Tạo template nếu được yêu cầu
                    if auto_create_characters_template:
                        logger.info(f"Creating characters.json template at: {auto_char_path}")
                        create_characters_json_template(auto_char_path, story_name or "Your Story")
                        logger.info("📝 Please edit characters.json to add your character info")
                    else:
                        logger.warning(f"⚠️ No characters.json found at: {auto_char_path}")
                        logger.info("💡 To enable character consistency:")
                        logger.info("   1. Create characters.json with your character info")
                        logger.info("   2. Add character references (e.g., characters/han_lap_ref.jpg)")
                        logger.info("   3. See characters.json.example for template")
                        logger.info("   OR run with auto_create_characters_template=True")

            if characters_json_path and os.path.exists(characters_json_path):
                char_manager = CharacterManager(characters_json_path)
                logger.info(f"✓ Character manager initialized with {len(char_manager.characters_data)} characters")
            else:
                logger.info("ℹ️ Generating images WITHOUT character consistency (normal mode)")

            # Setup output directory with language support
            # Structure: audio_downloads/<language>/<story_slug>/images/chapter_X/
            if not output_dir:
                # Auto-create output dir in story folder if story info provided
                if story_name or story_id:
                    from selenium_audio_generator import convert_to_slug

                    safe_story_name = convert_to_slug(story_name) if story_name else f"story_{story_id}"
                    chapter_folder = f"chapter_{chapter_number}" if chapter_number else "images"

                    output_dir = os.path.join(
                        config.AUDIO_DOWNLOAD_PATH,
                        language,
                        safe_story_name,
                        'images',
                        chapter_folder
                    )
                else:
                    # Fallback: Auto-create output dir based on JSON filename
                    json_filename = Path(json_path).stem
                    output_dir = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        'generated_images',
                        language,
                        json_filename
                    )
            
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Output directory: {output_dir}")
            
            # Check if images already exist
            existing_images = {}
            image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif'}
            if os.path.exists(output_dir):
                for filename in os.listdir(output_dir):
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in image_extensions:
                        # Parse filename: prompt_{id}_{idx}.png
                        if filename.startswith('prompt_'):
                            parts = filename.replace('.png', '').replace('.jpg', '').replace('.jpeg', '').split('_')
                            if len(parts) >= 3:
                                try:
                                    prompt_id = int(parts[1])
                                    if prompt_id not in existing_images:
                                        existing_images[prompt_id] = []
                                    existing_images[prompt_id].append(os.path.join(output_dir, filename))
                                except ValueError:
                                    pass
            
            # Check if all images already exist
            all_prompts_have_images = True
            for idx, prompt_data in enumerate(prompts):
                if isinstance(prompt_data, dict):
                    prompt_id = prompt_data.get('id', idx + 1)
                else:
                    prompt_id = idx + 1
                
                if prompt_id not in existing_images or len(existing_images[prompt_id]) == 0:
                    all_prompts_have_images = False
                    break
            
            # If all images exist, return success without calling API
            if all_prompts_have_images and len(existing_images) == len(prompts):
                logger.info(f"✓ All {len(prompts)} images already exist, skipping API calls")
                
                results = []
                for idx, prompt_data in enumerate(prompts):
                    if isinstance(prompt_data, dict):
                        prompt_text = prompt_data.get('content') or prompt_data.get('prompt') or prompt_data.get('text')
                        prompt_id = prompt_data.get('id', idx + 1)
                    else:
                        prompt_text = str(prompt_data)
                        prompt_id = idx + 1
                    
                    # Add existing images to results
                    for img_path in existing_images.get(prompt_id, []):
                        results.append({
                            "prompt_id": prompt_id,
                            "prompt_text": prompt_text,
                            "image_path": img_path,
                            "success": True,
                            "cached": True
                        })
                
                success_count = len(results)
                logger.info(f"✓ Returned {success_count} existing images")
                
                return {
                    "success": True,
                    "total_prompts": len(prompts),
                    "generated_images": success_count,
                    "output_dir": output_dir,
                    "results": results,
                    "cached": True
                }
            
            # Connect to Runware (only if we need to generate new images)
            logger.info(f"Generating {len(prompts) - len(existing_images)} new images...")
            await self.connect()
            
            # Generate images for each prompt
            results = []
            for idx, prompt_data in enumerate(prompts):
                try:
                    # Extract prompt text
                    if isinstance(prompt_data, dict):
                        prompt_text = prompt_data.get('content') or prompt_data.get('prompt') or prompt_data.get('text')
                        prompt_id = prompt_data.get('id', idx + 1)
                    else:
                        prompt_text = str(prompt_data)
                        prompt_id = idx + 1
                    
                    if not prompt_text:
                        logger.warning(f"Prompt {idx + 1} is empty, skipping")
                        continue
                    
                    # Check if this prompt already has images
                    if prompt_id in existing_images and len(existing_images[prompt_id]) > 0:
                        logger.info(f"✓ Prompt {idx + 1}/{len(prompts)} (ID: {prompt_id}) already has images, skipping")
                        for img_path in existing_images[prompt_id]:
                            results.append({
                                "prompt_id": prompt_id,
                                "prompt_text": prompt_text,
                                "image_path": img_path,
                                "success": True,
                                "cached": True
                            })
                        continue
                    
                    logger.info(f"Generating image {idx + 1}/{len(prompts)} (ID: {prompt_id})...")

                    # Detect characters và lấy references
                    character_refs = []
                    if char_manager:
                        # Ưu tiên lấy từ metadata
                        detected_chars = char_manager.extract_characters_from_metadata(prompt_data) if isinstance(prompt_data, dict) else []

                        # Nếu không có metadata, auto-detect từ text
                        if not detected_chars:
                            detected_chars = char_manager.detect_characters_in_text(prompt_text)

                        if detected_chars:
                            logger.info(f"Detected characters: {', '.join(detected_chars)}")

                            # Lấy reference images
                            for char_id in detected_chars:
                                ref_img = char_manager.get_reference_image(char_id)
                                if ref_img:
                                    character_refs.append(ref_img)

                            if character_refs:
                                logger.info(f"Using {len(character_refs)} character reference(s)")

                    # Generate image
                    images = await self.generate_image(
                        prompt=prompt_text,
                        model=model,
                        width=width,
                        height=height,
                        character_references=character_refs if character_refs else None,
                        instant_id_strength=instant_id_strength,
                        lora=lora
                    )
                    
                    if images:
                        # Save image data
                        for img_idx, image in enumerate(images):
                            image_filename = f"prompt_{prompt_id}_{img_idx}.png"
                            image_path = os.path.join(output_dir, image_filename)
                            
                            # Download and save image
                            if hasattr(image, 'imageURL'):
                                import aiohttp
                                async with aiohttp.ClientSession() as session:
                                    async with session.get(image.imageURL) as resp:
                                        if resp.status == 200:
                                            with open(image_path, 'wb') as f:
                                                f.write(await resp.read())
                                            logger.info(f"✓ Saved: {image_filename}")
                            
                            results.append({
                                "prompt_id": prompt_id,
                                "prompt_text": prompt_text,
                                "image_path": image_path,
                                "success": True
                            })
                    else:
                        results.append({
                            "prompt_id": prompt_id,
                            "prompt_text": prompt_text,
                            "error": "No image generated",
                            "success": False
                        })
                    
                    # Small delay between requests
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error generating image {idx + 1}: {e}")
                    results.append({
                        "prompt_id": prompt_id if 'prompt_id' in locals() else idx + 1,
                        "error": str(e),
                        "success": False
                    })
            
            # Disconnect
            await self.disconnect()
            
            # Summary
            success_count = sum(1 for r in results if r.get('success'))
            cached_count = sum(1 for r in results if r.get('cached'))
            new_count = success_count - cached_count
            
            if cached_count > 0:
                logger.info(f"✓ Total: {success_count} images ({cached_count} cached, {new_count} newly generated)")
            else:
                logger.info(f"✓ Generated {success_count}/{len(results)} images")
            
            return {
                "success": True,
                "total_prompts": len(prompts),
                "generated_images": success_count,
                "cached_images": cached_count,
                "new_images": new_count,
                "output_dir": output_dir,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Failed to generate images from JSON: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()


def create_characters_json_template(output_path: str, story_name: str = "Your Story") -> bool:
    """
    Tạo file characters.json template

    Args:
        output_path: Đường dẫn output file
        story_name: Tên story

    Returns:
        True nếu tạo thành công
    """
    template = {
        "story_name": story_name,
        "description": "Character database for consistent character generation across scenes",
        "characters": {
            "character_1": {
                "full_name": "Character Name",
                "aliases": ["Nickname 1", "Nickname 2"],
                "reference_image": "characters/character_1_ref.jpg",
                "first_appearance_chapter": 1,
                "description": "Character description",
                "notes": "Save best generated image as reference for future scenes"
            }
        },
        "_instructions": {
            "step_1": "Replace 'character_1' with your character ID (e.g., 'han_lap')",
            "step_2": "Update full_name, aliases, and description",
            "step_3": "Generate first image, pick best one as reference",
            "step_4": "Save reference to characters/character_id_ref.jpg",
            "step_5": "Update reference_image path",
            "step_6": "Add more characters as needed"
        }
    }

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ Created characters.json template at: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create template: {e}")
        return False


def generate_images_from_json_sync(json_path: str, **kwargs) -> Dict[str, Any]:
    """
    Synchronous wrapper cho generate_images_from_json

    Args:
        json_path: Đường dẫn đến file JSON
        **kwargs: Các tham số bổ sung

    Returns:
        Dict với thông tin kết quả
    """
    try:
        generator = RunwareImageGenerator()
        return asyncio.run(generator.generate_images_from_json(json_path, **kwargs))
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# Example usage
if __name__ == "__main__":
    # Test with a sample prompt
    async def test():
        generator = RunwareImageGenerator()

        async with generator:
            # Test 1: Generate image with LoRA from config
            print("\n=== Test 1: Generate image with LoRA from .env config ===")
            print(f"LoRA Config from .env: {config.RUNWARE_LORA_CONFIG}")

            images = await generator.generate_image(
                prompt="A cute cartoon child reading a book under a tree, children's book illustration style",
                model=config.RUNWARE_DEFAULT_MODEL,
                width=config.RUNWARE_DEFAULT_WIDTH,
                height=config.RUNWARE_DEFAULT_HEIGHT,
                lora=config.RUNWARE_LORA_CONFIG  # Using LoRA from .env
            )

            if images:
                print(f"✓ Generated {len(images)} image(s) with LoRA")
                for idx, img in enumerate(images):
                    print(f"  Image {idx + 1}: {img}")

            # Test 2: Generate without LoRA
            print("\n=== Test 2: Generate image without LoRA ===")
            images2 = await generator.generate_image(
                prompt="A bustling city street at night",
                model="runware:101@1",
                width=1024,
                height=1024
            )

            if images2:
                print(f"✓ Generated {len(images2)} image(s) without LoRA")

    # Run test
    asyncio.run(test())
