"""
Whisper Transcriber - Tạo file SRT từ audio sử dụng OpenAI Whisper
"""

import os
import logging
import whisper
from typing import Optional
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)


def format_timestamp(seconds: float) -> str:
    """
    Chuyển đổi giây sang định dạng SRT timestamp (HH:MM:SS,mmm)

    Args:
        seconds: Thời gian tính bằng giây

    Returns:
        String timestamp theo format SRT
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def transcribe_audio_to_srt(
    audio_path: str,
    output_srt_path: str,
    model_name: str = "large",
    language: str = "vi"
) -> bool:
    """
    Transcribe audio file thành SRT subtitle sử dụng Whisper

    Args:
        audio_path: Đường dẫn đến file audio
        output_srt_path: Đường dẫn output cho file SRT
        model_name: Tên model Whisper (tiny, base, small, medium, large)
        language: Ngôn ngữ của audio (vi, en, ...)

    Returns:
        True nếu thành công, False nếu thất bại
    """
    try:
        # Validate input
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return False

        # Create output directory if needed
        output_dir = os.path.dirname(output_srt_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        logger.info(f"Loading Whisper model '{model_name}'...")
        model = whisper.load_model(model_name)

        logger.info(f"Transcribing audio: {audio_path}")
        logger.info(f"Language: {language}")

        # Transcribe với word-level timestamps
        result = model.transcribe(
            audio_path,
            language=language,
            task="transcribe",
            verbose=False,
            word_timestamps=True
        )

        # Lấy segments từ kết quả
        segments = result.get("segments", [])

        if not segments:
            logger.warning("No segments found in transcription")
            return False

        logger.info(f"Found {len(segments)} segments")

        # Ghi file SRT
        with open(output_srt_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments, 1):
                start_time = segment['start']
                end_time = segment['end']
                text = segment['text'].strip()

                # Bỏ qua segments trống
                if not text:
                    continue

                # Viết entry SRT
                f.write(f"{i}\n")
                f.write(f"{format_timestamp(start_time)} --> {format_timestamp(end_time)}\n")
                f.write(f"{text}\n")
                f.write("\n")

        logger.info(f"✓ SRT file created: {output_srt_path}")
        logger.info(f"  Total segments: {len(segments)}")

        # Log một số thông tin về kết quả
        if segments:
            total_duration = segments[-1]['end']
            logger.info(f"  Total duration: {total_duration:.2f}s")

        return True

    except Exception as e:
        logger.error(f"Error transcribing audio: {e}", exc_info=True)
        return False


def get_srt_path_for_audio(audio_path: str, subtitles_folder: str = None) -> str:
    """
    Tạo đường dẫn SRT tương ứng với file audio

    Args:
        audio_path: Đường dẫn file audio
        subtitles_folder: Thư mục chứa subtitles (optional)

    Returns:
        Đường dẫn file SRT
    """
    audio_name = os.path.splitext(os.path.basename(audio_path))[0]

    if subtitles_folder:
        return os.path.join(subtitles_folder, f"{audio_name}.srt")
    else:
        # Đặt cùng thư mục với audio
        audio_dir = os.path.dirname(audio_path)
        return os.path.join(audio_dir, f"{audio_name}.srt")


def transcribe_chapter_audio(
    story_name: str,
    chapter_number: int,
    language: str = "vi",
    model_name: str = "large",
    audio_downloads_dir: str = "audio_downloads"
) -> Optional[str]:
    """
    Transcribe audio của một chapter cụ thể

    Args:
        story_name: Tên câu chuyện
        chapter_number: Số chapter
        language: Ngôn ngữ
        model_name: Tên model Whisper
        audio_downloads_dir: Thư mục gốc chứa audio

    Returns:
        Đường dẫn file SRT nếu thành công, None nếu thất bại
    """
    from video_generator import slugify

    # Tạo đường dẫn
    story_slug = slugify(story_name)
    story_folder = os.path.join(audio_downloads_dir, language, story_slug)

    # Tìm file audio
    audio_path = os.path.join(story_folder, f"chapter_{chapter_number}.mp3")
    if not os.path.exists(audio_path):
        # Thử với .wav
        audio_path = os.path.join(story_folder, f"chapter_{chapter_number}.wav")
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found for chapter {chapter_number}")
            return None

    # Tạo thư mục subtitles
    subtitles_folder = os.path.join(story_folder, "subtitles")
    os.makedirs(subtitles_folder, exist_ok=True)

    # Đường dẫn output
    srt_path = os.path.join(subtitles_folder, f"chapter_{chapter_number}.srt")

    # Transcribe
    success = transcribe_audio_to_srt(
        audio_path=audio_path,
        output_srt_path=srt_path,
        model_name=model_name,
        language=language
    )

    if success:
        return srt_path
    return None


# Utility function để tích hợp vào workflow
def ensure_srt_exists(
    audio_path: str,
    srt_path: str,
    language: str = "vi",
    model_name: str = "large",
    force_regenerate: bool = False
) -> bool:
    """
    Đảm bảo file SRT tồn tại, tạo mới nếu chưa có

    Args:
        audio_path: Đường dẫn file audio
        srt_path: Đường dẫn file SRT mong muốn
        language: Ngôn ngữ
        model_name: Model Whisper
        force_regenerate: Force tạo lại dù đã có

    Returns:
        True nếu SRT tồn tại/được tạo, False nếu lỗi
    """
    # Check if already exists
    if os.path.exists(srt_path) and not force_regenerate:
        logger.info(f"SRT file already exists: {srt_path}")
        return True

    # Generate new SRT
    return transcribe_audio_to_srt(
        audio_path=audio_path,
        output_srt_path=srt_path,
        model_name=model_name,
        language=language
    )


if __name__ == "__main__":
    # Test transcription
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python whisper_transcriber.py <audio_file> [output_srt] [model] [language]")
        print("Models: tiny, base, small, medium, large")
        print("Example: python whisper_transcriber.py audio.mp3 output.srt base vi")
        sys.exit(1)

    audio_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else audio_file.rsplit('.', 1)[0] + '.srt'
    model = sys.argv[3] if len(sys.argv) > 3 else "base"
    lang = sys.argv[4] if len(sys.argv) > 4 else "vi"

    success = transcribe_audio_to_srt(audio_file, output_file, model, lang)
    sys.exit(0 if success else 1)
