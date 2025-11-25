"""
Video Generator
Tạo video từ ảnh và audio bằng MoviePy
"""

import os
import re
import json
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from difflib import SequenceMatcher

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

    def parse_srt_file(self, srt_path: str) -> List[Dict[str, Any]]:
        """
        Parse file SRT để lấy timestamps và text

        Args:
            srt_path: Đường dẫn đến file SRT

        Returns:
            List các subtitle entries với format:
            [{"index": 1, "start": 0.0, "end": 3.5, "text": "Ngày xưa..."}, ...]
        """
        try:
            if not os.path.exists(srt_path):
                logger.error(f"SRT file not found: {srt_path}")
                return []

            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read()

            subtitles = []
            # Split by double newline to get individual subtitle blocks
            blocks = re.split(r'\n\s*\n', content.strip())

            for block in blocks:
                lines = block.strip().split('\n')
                if len(lines) < 3:
                    continue

                try:
                    # Line 1: Index number
                    index = int(lines[0].strip())

                    # Line 2: Timestamps (00:00:00,000 --> 00:00:03,500)
                    timestamp_line = lines[1].strip()
                    match = re.match(
                        r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})',
                        timestamp_line
                    )
                    if not match:
                        continue

                    # Convert to seconds
                    start_time = (
                        int(match.group(1)) * 3600 +
                        int(match.group(2)) * 60 +
                        int(match.group(3)) +
                        int(match.group(4)) / 1000
                    )
                    end_time = (
                        int(match.group(5)) * 3600 +
                        int(match.group(6)) * 60 +
                        int(match.group(7)) +
                        int(match.group(8)) / 1000
                    )

                    # Lines 3+: Text content
                    text = '\n'.join(lines[2:]).strip()

                    subtitles.append({
                        'index': index,
                        'start': start_time,
                        'end': end_time,
                        'text': text
                    })

                except (ValueError, IndexError) as e:
                    logger.debug(f"Error parsing subtitle block: {e}")
                    continue

            logger.info(f"✓ Parsed {len(subtitles)} subtitles from SRT")
            return subtitles

        except Exception as e:
            logger.error(f"Error parsing SRT file: {e}", exc_info=True)
            return []

    def calculate_image_durations_from_srt(self,
                                           srt_path: str,
                                           image_prompts_json: Dict[str, Any],
                                           total_audio_duration: float) -> List[float]:
        """
        Tính duration cho mỗi ảnh dựa trên file SRT và story_chunk

        Thuật toán:
        1. Parse file SRT để lấy timestamps cho từng đoạn text
        2. Với mỗi story_chunk, tìm các SRT entries tương ứng
        3. Lấy start time của entry đầu tiên và end time của entry cuối cùng

        Args:
            srt_path: Đường dẫn đến file SRT
            image_prompts_json: JSON chứa danh sách prompts với story_chunk
            total_audio_duration: Tổng thời lượng audio (giây)

        Returns:
            List duration cho mỗi ảnh (theo thứ tự)
        """
        try:
            # Parse SRT file
            subtitles = self.parse_srt_file(srt_path)
            if not subtitles:
                logger.warning("No subtitles found in SRT, falling back to equal distribution")
                return []

            # Extract prompts
            prompts = []
            if isinstance(image_prompts_json, dict):
                prompts = image_prompts_json.get('prompts', [])
            elif isinstance(image_prompts_json, list):
                prompts = image_prompts_json

            if not prompts:
                logger.warning("No prompts found in JSON")
                return []

            logger.info(f"Mapping {len(prompts)} story_chunks to {len(subtitles)} SRT entries")

            # Combine all SRT text for searching
            all_srt_text = ' '.join([sub['text'] for sub in subtitles])

            # Calculate timestamps for each image
            image_timestamps = []
            last_end_time = 0.0

            for idx, prompt in enumerate(prompts):
                story_chunk = prompt.get('story_chunk', '')
                last_text = prompt.get('last_text_for_story_chunk', '')

                if not story_chunk:
                    logger.warning(f"Prompt {idx+1} has no story_chunk")
                    continue

                # Find matching SRT entries for this story_chunk
                # Use last_text_for_story_chunk if available for precise end matching
                matching_subs = self._find_matching_subtitles_v2(
                    subtitles,
                    story_chunk,
                    last_text,
                    last_end_time
                )

                if matching_subs:
                    start_time = matching_subs[0]['start']
                    end_time = matching_subs[-1]['end']

                    # Ensure we don't go backwards in time
                    if start_time < last_end_time:
                        start_time = last_end_time

                    image_timestamps.append({
                        'idx': idx,
                        'start': start_time,
                        'end': end_time,
                        'duration': end_time - start_time,
                        'matched_subs': len(matching_subs)
                    })

                    last_end_time = end_time
                    logger.debug(f"Image {idx+1}: {start_time:.2f}s - {end_time:.2f}s ({len(matching_subs)} subs)")
                else:
                    # Couldn't find match, estimate based on position
                    estimated_duration = total_audio_duration / len(prompts)
                    start_time = last_end_time
                    end_time = start_time + estimated_duration

                    image_timestamps.append({
                        'idx': idx,
                        'start': start_time,
                        'end': end_time,
                        'duration': estimated_duration,
                        'matched_subs': 0
                    })

                    last_end_time = end_time
                    logger.debug(f"Image {idx+1}: estimated {start_time:.2f}s - {end_time:.2f}s")

            if not image_timestamps:
                return []

            # Extract durations
            durations = [ts['duration'] for ts in image_timestamps]

            # Ensure minimum duration (at least 2 seconds)
            durations = [max(d, 2.0) for d in durations]

            # Normalize to match total audio duration
            total_calculated = sum(durations)
            if abs(total_calculated - total_audio_duration) > 0.5:
                scale_factor = total_audio_duration / total_calculated
                durations = [d * scale_factor for d in durations]
                logger.info(f"Normalized durations (scale: {scale_factor:.3f})")

            logger.info(f"✓ Calculated durations from SRT for {len(durations)} images")
            logger.info(f"  Range: {min(durations):.2f}s - {max(durations):.2f}s")
            logger.info(f"  Total: {sum(durations):.2f}s (audio: {total_audio_duration:.2f}s)")

            return durations

        except Exception as e:
            logger.error(f"Error calculating durations from SRT: {e}", exc_info=True)
            return []

    def _find_matching_subtitles_v2(self,
                                     subtitles: List[Dict[str, Any]],
                                     story_chunk: str,
                                     last_text: str,
                                     start_after: float = 0.0) -> List[Dict[str, Any]]:
        """
        Tìm các SRT entries khớp với story_chunk (phiên bản cải tiến)

        Thuật toán đơn giản:
        1. START: Lấy subtitle đầu tiên có start >= start_after
        2. END: Tìm subtitle chứa các từ cuối của last_text_for_story_chunk

        Args:
            subtitles: Danh sách subtitles từ SRT
            story_chunk: Text tóm tắt của phân cảnh
            last_text: Text cuối cùng khớp chính xác với SRT (từ last_text_for_story_chunk)
            start_after: Chỉ tìm các subtitles sau thời điểm này

        Returns:
            List các matching subtitles
        """
        # Filter subtitles: start >= start_after (allow small tolerance)
        tolerance = 0.1
        filtered_subs = [s for s in subtitles if s['start'] >= start_after - tolerance]
        if not filtered_subs:
            return []

        # START is always the first subtitle after start_after
        start_idx = 0

        # === Find END subtitle using last_text_for_story_chunk ===
        end_idx = start_idx  # Default to start if we can't find end

        if last_text and last_text.strip():
            last_text_clean = last_text.lower().strip()
            # Remove quotes if present
            last_text_clean = last_text_clean.strip('"').strip("'").strip('"').strip('"').strip('\"')
            last_text_words = last_text_clean.split()

            # Get last 3-5 significant words from last_text
            # Remove common punctuation and get meaningful words
            significant_words = []
            for w in reversed(last_text_words):
                clean_word = w.strip('.,!?;:"\'"')
                if len(clean_word) > 1:  # Skip single characters
                    significant_words.insert(0, clean_word)
                    if len(significant_words) >= 4:
                        break

            logger.debug(f"Looking for end words: {significant_words}")

            # Search for subtitle containing these last words
            found_end = False
            for i in range(len(filtered_subs)):
                sub_text = filtered_subs[i]['text'].lower()

                # Check if ALL significant words appear in this subtitle
                if len(significant_words) >= 2:
                    matches = sum(1 for w in significant_words if w in sub_text)
                    if matches >= len(significant_words) - 1:  # Allow 1 word mismatch
                        end_idx = i
                        found_end = True
                        logger.debug(f"Found end at subtitle {filtered_subs[i]['index']}: '{filtered_subs[i]['text'][:50]}...'")
                        break

                # Also try matching the last 2 words as a phrase
                if len(significant_words) >= 2:
                    last_phrase = ' '.join(significant_words[-2:])
                    if last_phrase in sub_text:
                        end_idx = i
                        found_end = True
                        logger.debug(f"Found end via phrase at subtitle {filtered_subs[i]['index']}")
                        break

            if not found_end:
                logger.warning(f"Could not find end for last_text: '{last_text[:60]}...'")
                # Fallback: estimate based on word count
                estimated_subs = max(3, len(last_text_words) // 3)
                end_idx = min(start_idx + estimated_subs, len(filtered_subs) - 1)

        else:
            # No last_text provided, estimate based on story_chunk
            chunk_words = story_chunk.lower().split()
            estimated_subs = max(3, len(chunk_words) // 5)
            end_idx = min(start_idx + estimated_subs, len(filtered_subs) - 1)

        result = filtered_subs[start_idx:end_idx + 1]
        if result:
            logger.debug(f"Matched {len(result)} subs: {filtered_subs[start_idx]['index']} - {filtered_subs[end_idx]['index']}")
        return result

    def _find_matching_subtitles(self,
                                  subtitles: List[Dict[str, Any]],
                                  story_chunk: str,
                                  start_after: float = 0.0) -> List[Dict[str, Any]]:
        """
        Tìm các SRT entries khớp với story_chunk

        Thuật toán:
        1. Tìm subtitle chứa phần ĐẦU của story_chunk (vài từ đầu tiên)
        2. Tìm subtitle chứa phần CUỐI của story_chunk (vài từ cuối cùng)
        3. Trả về tất cả subtitles từ start đến end

        Args:
            subtitles: Danh sách subtitles từ SRT
            story_chunk: Text của story_chunk cần tìm
            start_after: Chỉ tìm các subtitles sau thời điểm này

        Returns:
            List các matching subtitles
        """
        # Filter subtitles after start_after
        filtered_subs = [s for s in subtitles if s['end'] > start_after]
        if not filtered_subs:
            return []

        # Normalize story_chunk
        chunk_clean = story_chunk.lower().strip()
        chunk_words = chunk_clean.split()

        if len(chunk_words) < 3:
            return []

        # Extract key phrases from story_chunk
        # First few words and last few words
        first_words = ' '.join(chunk_words[:4])  # First 4 words
        last_words = ' '.join(chunk_words[-4:])   # Last 4 words

        # Also get some middle keywords (nouns, verbs - important words)
        # Filter out common stop words
        stop_words = {'và', 'của', 'là', 'có', 'được', 'với', 'trong', 'cho', 'đến', 'từ',
                      'một', 'những', 'các', 'này', 'đó', 'như', 'để', 'khi', 'nếu', 'thì',
                      'nhưng', 'mà', 'vì', 'nên', 'cũng', 'đã', 'sẽ', 'đang', 'rồi', 'lại'}
        key_words = [w for w in chunk_words if w not in stop_words and len(w) > 2]

        # Find start subtitle (contains beginning of story_chunk)
        start_idx = -1
        for i, sub in enumerate(filtered_subs):
            sub_text = sub['text'].lower()

            # Check if first words appear in subtitle
            if self._text_contains_phrase(sub_text, first_words):
                start_idx = i
                break

            # Or check if several key words from beginning appear
            first_key_words = [w for w in chunk_words[:8] if w in key_words][:3]
            if first_key_words and all(w in sub_text for w in first_key_words):
                start_idx = i
                break

        # If still not found, try fuzzy match on first part
        if start_idx == -1:
            for i, sub in enumerate(filtered_subs):
                # Combine this and next few subs
                combined = ' '.join([filtered_subs[j]['text'].lower()
                                    for j in range(i, min(i + 3, len(filtered_subs)))])
                ratio = SequenceMatcher(None, first_words, combined[:len(first_words) * 2]).ratio()
                if ratio > 0.5:
                    start_idx = i
                    break

        if start_idx == -1:
            return []

        # Find end subtitle (contains end of story_chunk)
        end_idx = start_idx
        for i in range(start_idx, len(filtered_subs)):
            sub_text = filtered_subs[i]['text'].lower()

            # Check if last words appear in subtitle
            if self._text_contains_phrase(sub_text, last_words):
                end_idx = i
                break

            # Or check if several key words from end appear
            last_key_words = [w for w in chunk_words[-8:] if w in key_words][-3:]
            if last_key_words and all(w in sub_text for w in last_key_words):
                end_idx = i
                break

            # Keep extending if we find matching keywords
            matching_keys = sum(1 for w in key_words if w in sub_text)
            if matching_keys >= 2:
                end_idx = i

        # Ensure we have at least a few subtitles if chunk is long
        min_subs = max(1, len(chunk_words) // 15)  # Roughly 15 words per subtitle
        if end_idx - start_idx + 1 < min_subs:
            end_idx = min(start_idx + min_subs - 1, len(filtered_subs) - 1)

        # Return the range of subtitles
        return filtered_subs[start_idx:end_idx + 1]

    def _text_contains_phrase(self, text: str, phrase: str) -> bool:
        """
        Kiểm tra text có chứa phrase hay không (cho phép một số sai khác nhỏ)

        Args:
            text: Text để tìm kiếm
            phrase: Phrase cần tìm

        Returns:
            True nếu tìm thấy
        """
        # Direct substring check
        if phrase in text:
            return True

        # Check if most words of phrase appear in text
        phrase_words = phrase.split()
        if len(phrase_words) <= 2:
            return all(w in text for w in phrase_words)

        # Allow 1 word missing for longer phrases
        matches = sum(1 for w in phrase_words if w in text)
        return matches >= len(phrase_words) - 1

    def calculate_image_durations_from_prompts(self,
                                                image_prompts_json: Dict[str, Any],
                                                chapter_content: str,
                                                total_audio_duration: float) -> List[float]:
        """
        Tính duration cho mỗi ảnh dựa trên vị trí của story_chunk trong chapter content

        Thuật toán:
        1. Tìm vị trí của mỗi story_chunk trong chapter_content
        2. Tính tỷ lệ độ dài text mỗi phân cảnh
        3. Phân bổ thời lượng audio theo tỷ lệ đó

        Args:
            image_prompts_json: JSON chứa danh sách prompts với story_chunk
            chapter_content: Nội dung chapter gốc
            total_audio_duration: Tổng thời lượng audio (giây)

        Returns:
            List duration cho mỗi ảnh (theo thứ tự)
        """
        try:
            # Extract prompts from JSON
            prompts = []
            if isinstance(image_prompts_json, dict):
                prompts = image_prompts_json.get('prompts', [])
            elif isinstance(image_prompts_json, list):
                prompts = image_prompts_json

            if not prompts:
                logger.warning("No prompts found in JSON, using equal distribution")
                return []

            logger.info(f"Calculating durations for {len(prompts)} images based on story_chunk positions")

            # Clean chapter content for better matching
            clean_chapter = chapter_content.strip()

            # Find positions and calculate segment lengths
            segments = []
            last_end_pos = 0

            for idx, prompt in enumerate(prompts):
                story_chunk = prompt.get('story_chunk', '')
                if not story_chunk:
                    logger.warning(f"Prompt {idx+1} has no story_chunk")
                    continue

                # Find the position of this story_chunk in chapter content
                # Use fuzzy matching for better results
                best_pos, best_ratio = self._find_best_match_position(
                    clean_chapter,
                    story_chunk,
                    start_from=last_end_pos
                )

                if best_pos >= 0:
                    # Calculate segment as: from last_end_pos to best_pos + chunk_length
                    segment_start = last_end_pos
                    segment_end = best_pos + len(story_chunk)

                    # Estimate this segment's portion of text
                    # Use the midpoint to end of this segment as the "coverage"
                    segment_length = max(segment_end - segment_start, len(story_chunk))

                    segments.append({
                        'idx': idx,
                        'start': segment_start,
                        'end': segment_end,
                        'length': segment_length,
                        'story_chunk': story_chunk[:50] + '...' if len(story_chunk) > 50 else story_chunk
                    })

                    last_end_pos = segment_end
                    logger.debug(f"Segment {idx+1}: pos={best_pos}, len={segment_length}, match={best_ratio:.2f}")
                else:
                    # Couldn't find match, use proportional estimate
                    estimated_length = len(story_chunk)
                    segments.append({
                        'idx': idx,
                        'start': last_end_pos,
                        'end': last_end_pos + estimated_length,
                        'length': estimated_length,
                        'story_chunk': story_chunk[:50] + '...' if len(story_chunk) > 50 else story_chunk
                    })
                    last_end_pos += estimated_length
                    logger.debug(f"Segment {idx+1}: estimated len={estimated_length}")

            if not segments:
                return []

            # Calculate total text length covered
            total_text_length = sum(seg['length'] for seg in segments)

            # Calculate duration for each image based on text proportion
            durations = []
            for seg in segments:
                # Duration proportional to text length
                proportion = seg['length'] / total_text_length
                duration = proportion * total_audio_duration

                # Ensure minimum duration (at least 2 seconds)
                duration = max(duration, 2.0)
                durations.append(duration)

                logger.debug(f"Image {seg['idx']+1}: {duration:.2f}s ({proportion*100:.1f}% of audio)")

            # Normalize durations to match total audio duration
            total_calculated = sum(durations)
            if abs(total_calculated - total_audio_duration) > 0.1:
                scale_factor = total_audio_duration / total_calculated
                durations = [d * scale_factor for d in durations]
                logger.info(f"Normalized durations (scale: {scale_factor:.3f})")

            logger.info(f"✓ Calculated durations for {len(durations)} images")
            logger.info(f"  Range: {min(durations):.2f}s - {max(durations):.2f}s")
            logger.info(f"  Total: {sum(durations):.2f}s (audio: {total_audio_duration:.2f}s)")

            return durations

        except Exception as e:
            logger.error(f"Error calculating durations: {e}", exc_info=True)
            return []

    def _find_best_match_position(self, text: str, pattern: str, start_from: int = 0) -> tuple:
        """
        Tìm vị trí tốt nhất của pattern trong text sử dụng fuzzy matching

        Args:
            text: Text gốc để tìm kiếm
            pattern: Pattern cần tìm
            start_from: Vị trí bắt đầu tìm

        Returns:
            Tuple (position, match_ratio) hoặc (-1, 0) nếu không tìm thấy
        """
        # First try exact match
        search_text = text[start_from:]

        # Clean and normalize for better matching
        pattern_clean = pattern.strip()

        # Try exact substring match first
        pos = search_text.find(pattern_clean)
        if pos >= 0:
            return (start_from + pos, 1.0)

        # Try with first few words (more robust)
        first_words = ' '.join(pattern_clean.split()[:5])
        pos = search_text.find(first_words)
        if pos >= 0:
            return (start_from + pos, 0.9)

        # Fuzzy match using sliding window
        pattern_len = len(pattern_clean)
        window_size = min(pattern_len * 2, len(search_text))

        best_pos = -1
        best_ratio = 0

        # Slide through text with step size
        step = max(1, pattern_len // 4)
        for i in range(0, len(search_text) - pattern_len + 1, step):
            window = search_text[i:i + window_size]
            ratio = SequenceMatcher(None, pattern_clean.lower(), window.lower()).ratio()

            if ratio > best_ratio and ratio > 0.4:  # Threshold for match
                best_ratio = ratio
                best_pos = start_from + i

        return (best_pos, best_ratio)

    def create_video_from_images(self,
                                 image_paths: List[str],
                                 audio_path: str,
                                 output_path: str,
                                 fps: int = 1,
                                 transition_duration: float = 0.5,
                                 image_durations: List[float] = None) -> Dict[str, Any]:
        """
        Tạo video từ danh sách ảnh và audio

        Args:
            image_paths: Danh sách đường dẫn ảnh
            audio_path: Đường dẫn file audio
            output_path: Đường dẫn file video output
            fps: Frames per second (1 = mỗi ảnh hiển thị 1 giây)
            transition_duration: Thời gian chuyển cảnh (giây)
            image_durations: Danh sách duration riêng cho mỗi ảnh (None = chia đều)

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

            # Determine durations for each image
            use_custom_durations = False
            if image_durations and len(image_durations) == len(image_paths):
                use_custom_durations = True
                logger.info(f"Using custom durations for {len(image_durations)} images")
                logger.info(f"  Duration range: {min(image_durations):.2f}s - {max(image_durations):.2f}s")
            else:
                # Calculate equal duration per image
                duration_per_image = total_audio_duration / len(image_paths)
                logger.info(f"Duration per image: {duration_per_image:.2f}s (equal distribution)")

            # Create image clips
            clips = []
            valid_image_idx = 0
            for idx, img_path in enumerate(image_paths):
                if not os.path.exists(img_path):
                    logger.warning(f"Image not found: {img_path}, skipping")
                    continue

                try:
                    # Get duration for this image
                    if use_custom_durations:
                        duration = image_durations[idx]
                    else:
                        duration = duration_per_image

                    # Create image clip with specified duration
                    # MoviePy 2.x uses with_duration() instead of set_duration()
                    img_clip = ImageClip(img_path)
                    try:
                        img_clip = img_clip.with_duration(duration)
                    except AttributeError:
                        # Fallback for MoviePy 1.x
                        img_clip = img_clip.set_duration(duration)
                    clips.append(img_clip)

                    if use_custom_durations:
                        logger.info(f"✓ Added image {idx + 1}/{len(image_paths)}: {os.path.basename(img_path)} ({duration:.2f}s)")
                    else:
                        logger.info(f"✓ Added image {idx + 1}/{len(image_paths)}: {os.path.basename(img_path)}")

                    valid_image_idx += 1
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
            try:
                video = video.with_audio(audio_clip)
            except AttributeError:
                # Fallback for MoviePy 1.x
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
                                    transition_duration: float = 0.5,
                                    image_prompts_path: str = None,
                                    chapter_content: str = None,
                                    srt_path: str = None,
                                    language: str = 'vi') -> Dict[str, Any]:
        """
        Tạo video từ thư mục chứa ảnh và audio

        Args:
            image_dir: Thư mục chứa ảnh
            audio_path: Đường dẫn file audio
            output_path: Đường dẫn file video output (None = auto)
            fps: Frames per second
            transition_duration: Thời gian chuyển cảnh (giây)
            image_prompts_path: Đường dẫn đến file image_prompts.json (để sync với story_chunk)
            chapter_content: Nội dung chapter gốc (fallback nếu không có SRT)
            srt_path: Đường dẫn đến file SRT (ưu tiên cao nhất cho sync)
            language: Mã ngôn ngữ (vi, en, ja, etc.)

        Returns:
            Dict với thông tin kết quả

        Thứ tự ưu tiên sync:
        1. SRT file (chính xác nhất)
        2. chapter_content + image_prompts (ước tính dựa trên text)
        3. Chia đều (fallback)
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
            # Structure: generated_videos/<language>/<video_name>.mp4
            if not output_path:
                video_dir = os.path.join(config.GENERATED_VIDEOS_DIR, language)
                os.makedirs(video_dir, exist_ok=True)

                # Use image directory name as video filename
                dir_name = os.path.basename(image_dir)
                output_path = os.path.join(video_dir, f"{dir_name}.mp4")

            # Calculate custom durations based on available sync data
            # Priority: 1. SRT file, 2. chapter_content + prompts, 3. equal distribution
            image_durations = None

            # Get audio duration first
            audio_clip = AudioFileClip(audio_path)
            total_audio_duration = audio_clip.duration
            audio_clip.close()

            # Method 1: Use SRT file (most accurate)
            if srt_path and image_prompts_path:
                logger.info(f"🎯 Using SRT file for precise sync: {srt_path}")
                try:
                    with open(image_prompts_path, 'r', encoding='utf-8') as f:
                        image_prompts_json = json.load(f)

                    image_durations = self.calculate_image_durations_from_srt(
                        srt_path,
                        image_prompts_json,
                        total_audio_duration
                    )

                    if image_durations and len(image_durations) == len(image_paths):
                        logger.info(f"✓ Calculated {len(image_durations)} durations from SRT (precise sync)")
                    else:
                        logger.warning(f"SRT duration count mismatch ({len(image_durations) if image_durations else 0} vs {len(image_paths)} images)")
                        image_durations = None

                except Exception as e:
                    logger.warning(f"Could not calculate durations from SRT: {e}")
                    image_durations = None

            # Method 2: Use chapter_content + prompts (estimated)
            if not image_durations and image_prompts_path and chapter_content:
                logger.info(f"📝 Using chapter content for estimated sync: {image_prompts_path}")
                try:
                    with open(image_prompts_path, 'r', encoding='utf-8') as f:
                        image_prompts_json = json.load(f)

                    image_durations = self.calculate_image_durations_from_prompts(
                        image_prompts_json,
                        chapter_content,
                        total_audio_duration
                    )

                    if image_durations and len(image_durations) == len(image_paths):
                        logger.info(f"✓ Calculated {len(image_durations)} durations from text (estimated sync)")
                    else:
                        logger.warning(f"Duration count mismatch ({len(image_durations) if image_durations else 0} vs {len(image_paths)} images)")
                        image_durations = None

                except Exception as e:
                    logger.warning(f"Could not calculate durations from text: {e}")
                    image_durations = None

            # Method 3: Equal distribution (fallback)
            if not image_durations:
                if srt_path and not image_prompts_path:
                    logger.warning("srt_path provided but image_prompts_path is missing")
                elif image_prompts_path and not chapter_content and not srt_path:
                    logger.warning("image_prompts_path provided but neither srt_path nor chapter_content available")
                logger.info("📊 Using equal distribution for image durations")

            # Create video
            return self.create_video_from_images(
                image_paths=image_paths,
                audio_path=audio_path,
                output_path=output_path,
                fps=fps,
                transition_duration=transition_duration,
                image_durations=image_durations
            )
            
        except Exception as e:
            logger.error(f"Failed to create video from directory: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


def create_video_sync(image_dir: str, audio_path: str, output_path: str = None,
                      image_prompts_path: str = None, chapter_content: str = None,
                      srt_path: str = None, **kwargs) -> Dict[str, Any]:
    """
    Synchronous wrapper để tạo video từ thư mục ảnh và audio

    Args:
        image_dir: Thư mục chứa ảnh
        audio_path: Đường dẫn file audio
        output_path: Đường dẫn file video output (None = auto)
        image_prompts_path: Đường dẫn đến file image_prompts.json (để sync tốt hơn)
        chapter_content: Nội dung chapter gốc (fallback cho sync)
        srt_path: Đường dẫn đến file SRT (ưu tiên cao nhất cho sync)
        **kwargs: Các tham số bổ sung

    Returns:
        Dict với thông tin kết quả

    Example:
        # Tạo video với sync chính xác từ SRT (khuyến nghị)
        result = create_video_sync(
            image_dir="audio_downloads/vi/tam_cam/images/chapter_1",
            audio_path="audio_downloads/vi/tam_cam/1_1.wav",
            image_prompts_path="audio_downloads/vi/tam_cam/image_prompts/1_chapter_1.json",
            srt_path="audio_downloads/vi/tam_cam/subtitles/1_1.srt"
        )

        # Hoặc với sync ước tính từ text (fallback)
        result = create_video_sync(
            image_dir="audio_downloads/vi/tam_cam/images/chapter_1",
            audio_path="audio_downloads/vi/tam_cam/1_1.wav",
            image_prompts_path="audio_downloads/vi/tam_cam/image_prompts/1_chapter_1.json",
            chapter_content="Ngày xưa có cô Tấm..."
        )
    """
    try:
        generator = VideoGenerator()
        return generator.create_video_from_image_dir(
            image_dir=image_dir,
            audio_path=audio_path,
            output_path=output_path,
            image_prompts_path=image_prompts_path,
            chapter_content=chapter_content,
            srt_path=srt_path,
            **kwargs
        )
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def get_story_subtitles_folder(story_name: str, language: str = 'vi') -> str:
    """
    Lấy đường dẫn folder subtitles cho story

    Args:
        story_name: Tên story
        language: Mã ngôn ngữ

    Returns:
        Đường dẫn đến folder subtitles (đã tạo sẵn)

    Structure:
        audio_downloads/<language>/<story_slug>/subtitles/
    """
    try:
        from selenium_audio_generator import convert_to_slug
        story_slug = convert_to_slug(story_name)
    except ImportError:
        # Fallback slug conversion
        story_slug = re.sub(r'[^\w\s-]', '', story_name.lower())
        story_slug = re.sub(r'[-\s]+', '-', story_slug).strip('-')

    subtitles_dir = os.path.join(
        config.AUDIO_DOWNLOAD_PATH,
        language,
        story_slug,
        'subtitles'
    )
    os.makedirs(subtitles_dir, exist_ok=True)
    logger.info(f"✓ Subtitles folder ready: {subtitles_dir}")
    return subtitles_dir


def get_srt_path_for_chapter(story_name: str, chapter_number: int,
                              language: str = 'vi') -> str:
    """
    Lấy đường dẫn file SRT cho chapter cụ thể

    Args:
        story_name: Tên story
        chapter_number: Số chương
        language: Mã ngôn ngữ

    Returns:
        Đường dẫn đến file SRT (có thể chưa tồn tại)

    Filename format: chapter_{chapter_number}.srt
    """
    subtitles_dir = get_story_subtitles_folder(story_name, language)
    srt_filename = f"chapter_{chapter_number}.srt"
    return os.path.join(subtitles_dir, srt_filename)


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
