"""
Video Generator
Tạo video từ ảnh và audio bằng MoviePy
"""

import os
import re
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

try:
    # Try MoviePy 2.x import path first
    try:
        from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
    except ImportError:
        # Fallback to MoviePy 1.x import path
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
except ImportError:
    print("⚠️ MoviePy chưa được cài đặt. Chạy: pip install moviepy imageio-ffmpeg")
    ImageClip = None
    AudioFileClip = None
    concatenate_videoclips = None

import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoGenerator:
    """
    Class để tạo video từ danh sách ảnh và file audio
    """
    
    def __init__(self):
        """Khởi tạo VideoGenerator"""
        if ImageClip is None or AudioFileClip is None:
            raise ImportError("MoviePy chưa được cài đặt. Chạy: pip install moviepy imageio-ffmpeg")
        
        logger.info("✓ VideoGenerator initialized")
    
    def create_video_from_images(self,
                                 image_paths: List[str],
                                 audio_path: str,
                                 output_path: str,
                                 fps: int = 1,
                                 transition_duration: float = 0.5) -> Dict[str, Any]:
        """
        Tạo video từ danh sách ảnh và audio
        
        Args:
            image_paths: Danh sách đường dẫn ảnh
            audio_path: Đường dẫn file audio
            output_path: Đường dẫn file video output
            fps: Frames per second (1 = mỗi ảnh hiển thị 1 giây)
            transition_duration: Thời gian chuyển cảnh (giây)
            
        Returns:
            Dict với thông tin kết quả
        """
        try:
            if not image_paths:
                return {"success": False, "error": "Không có ảnh nào"}
            
            if not os.path.exists(audio_path):
                return {"success": False, "error": f"File audio không tồn tại: {audio_path}"}
            
            logger.info(f"Creating video from {len(image_paths)} images...")
            logger.info(f"Audio: {audio_path}")
            logger.info(f"Output: {output_path}")
            
            # Load audio
            audio_clip = AudioFileClip(audio_path)
            total_audio_duration = audio_clip.duration
            logger.info(f"Audio duration: {total_audio_duration:.2f}s")
            
            # Calculate duration per image
            duration_per_image = total_audio_duration / len(image_paths)
            logger.info(f"Duration per image: {duration_per_image:.2f}s")
            
            # Create image clips
            clips = []
            for idx, img_path in enumerate(image_paths):
                if not os.path.exists(img_path):
                    logger.warning(f"Image not found: {img_path}, skipping")
                    continue
                
                try:
                    # Create image clip with calculated duration
                    img_clip = ImageClip(img_path).set_duration(duration_per_image)
                    clips.append(img_clip)
                    logger.info(f"✓ Added image {idx + 1}/{len(image_paths)}: {os.path.basename(img_path)}")
                except Exception as e:
                    logger.error(f"Error loading image {img_path}: {e}")
                    continue
            
            if not clips:
                return {"success": False, "error": "Không có ảnh nào hợp lệ"}
            
            # Concatenate all clips
            logger.info("Concatenating video clips...")
            video = concatenate_videoclips(clips, method="compose")
            
            # Set audio
            logger.info("Adding audio to video...")
            video = video.set_audio(audio_clip)
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write video file
            logger.info("Writing video file (this may take a while)...")
            video.write_videofile(
                output_path,
                fps=24,  # Standard FPS for smooth playback
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                logger=None  # Suppress MoviePy's verbose logging
            )
            
            # Cleanup
            audio_clip.close()
            video.close()
            for clip in clips:
                clip.close()
            
            logger.info(f"✓ Video created successfully: {output_path}")
            
            return {
                "success": True,
                "output_path": output_path,
                "duration": total_audio_duration,
                "num_images": len(clips)
            }
            
        except Exception as e:
            logger.error(f"Failed to create video: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def create_video_from_image_dir(self,
                                    image_dir: str,
                                    audio_path: str,
                                    output_path: str = None,
                                    fps: int = 1,
                                    transition_duration: float = 0.5) -> Dict[str, Any]:
        """
        Tạo video từ thư mục chứa ảnh và audio
        
        Args:
            image_dir: Thư mục chứa ảnh
            audio_path: Đường dẫn file audio
            output_path: Đường dẫn file video output (None = auto)
            fps: Frames per second
            transition_duration: Thời gian chuyển cảnh (giây)
            
        Returns:
            Dict với thông tin kết quả
        """
        try:
            # Find all images in directory
            image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif'}
            image_files = []

            # Collect all image files
            for filename in os.listdir(image_dir):
                ext = os.path.splitext(filename)[1].lower()
                if ext in image_extensions:
                    image_files.append(filename)

            if not image_files:
                return {"success": False, "error": f"Không tìm thấy ảnh nào trong: {image_dir}"}

            # Natural sort to handle numeric ordering correctly
            # e.g., prompt_1, prompt_2, ..., prompt_10 (not prompt_1, prompt_10, prompt_2)
            def natural_sort_key(filename):
                """Sort key that handles numbers naturally"""
                return [int(text) if text.isdigit() else text.lower()
                        for text in re.split(r'(\d+)', filename)]

            image_files.sort(key=natural_sort_key)

            # Create full paths
            image_paths = [os.path.join(image_dir, filename) for filename in image_files]

            logger.info(f"Found {len(image_paths)} images in {image_dir}")
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Image files order: {image_files[:5]}...")  # Show first 5
            
            # Auto-generate output path if not provided
            if not output_path:
                video_dir = config.GENERATED_VIDEOS_DIR
                os.makedirs(video_dir, exist_ok=True)
                
                # Use image directory name as video filename
                dir_name = os.path.basename(image_dir)
                output_path = os.path.join(video_dir, f"{dir_name}.mp4")
            
            # Create video
            return self.create_video_from_images(
                image_paths=image_paths,
                audio_path=audio_path,
                output_path=output_path,
                fps=fps,
                transition_duration=transition_duration
            )
            
        except Exception as e:
            logger.error(f"Failed to create video from directory: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


def create_video_sync(image_dir: str, audio_path: str, output_path: str = None, **kwargs) -> Dict[str, Any]:
    """
    Synchronous wrapper để tạo video từ thư mục ảnh và audio
    
    Args:
        image_dir: Thư mục chứa ảnh
        audio_path: Đường dẫn file audio
        output_path: Đường dẫn file video output (None = auto)
        **kwargs: Các tham số bổ sung
        
    Returns:
        Dict với thông tin kết quả
    """
    try:
        generator = VideoGenerator()
        return generator.create_video_from_image_dir(
            image_dir=image_dir,
            audio_path=audio_path,
            output_path=output_path,
            **kwargs
        )
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# Example usage
if __name__ == "__main__":
    # Test video generation
    generator = VideoGenerator()
    
    # Example: Create video from images in a directory
    result = generator.create_video_from_image_dir(
        image_dir="generated_images/test_chapter",
        audio_path="audio_downloads/test_story/chuong_1.wav",
        output_path="generated_videos/test_video.mp4"
    )
    
    if result.get('success'):
        print(f"✓ Video created: {result['output_path']}")
        print(f"  Duration: {result['duration']:.2f}s")
        print(f"  Images: {result['num_images']}")
    else:
        print(f"✗ Error: {result.get('error')}")
