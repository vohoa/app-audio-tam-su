"""
This module handles the audio generation from Google's Gemini API using streaming.
Supports both single audio generation and multi-segment audio generation with merging.
"""
import mimetypes
import os
import struct
import logging
import wave
from google import genai
from google.genai import types

# Optional import for audio merging
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    AudioSegment = None

logger = logging.getLogger(__name__)

def save_binary_file(file_name, data):
    """Helper function to save binary data to a file"""
    with open(file_name, "wb") as f:
        f.write(data)

def save_wave_file_with_path_dir(filename, pcm_data, path_dir, channels=1, rate=24000, sample_width=2):
  """
  Save PCM audio data to WAV file in the specified directory with given parameters.

  Args:
    filename: Output WAV filename (not full path)
    pcm_data: Raw PCM audio data
    path_dir: Directory to save the file in
    channels: Number of audio channels (default: 1)
    rate: Sample rate (default: 24000)
    sample_width: Sample width in bytes (default: 2)
  """
  try:
    # Ensure the directory exists
    os.makedirs(path_dir, exist_ok=True)
    full_path = os.path.join(path_dir, filename)
    with wave.open(full_path, "wb") as wf:
      wf.setnchannels(channels)
      wf.setsampwidth(sample_width)
      wf.setframerate(rate)
      wf.writeframes(pcm_data)
  except Exception as e:
    logger.error(f"Error saving WAV file {full_path}: {str(e)}")
    raise e
      
def save_wave_file(filename, pcm_data, channels=1, rate=24000, sample_width=2):
    """
    Save PCM audio data to WAV file with specified parameters
    
    Args:
        filename: Output WAV filename
        pcm_data: Raw PCM audio data
        channels: Number of audio channels (default: 1)
        rate: Sample rate (default: 24000)
        sample_width: Sample width in bytes (default: 2)
    """
    try:
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm_data)
    except Exception as e:
        logger.error(f"Error saving WAV file {filename}: {str(e)}")
        raise e

def generate_segment_single_audio(segment, voice_name, characteristics, role):
    """
    Generate audio for a single segment text
    
    Args:
        segment: Formatted text content for TTS
        voice_name: Name of the voice to use for TTS
        
    Returns:
        bytes: Generated audio data
    """
    try:
        # Get API key
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        
        # Generate audio
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=segment,
            config=types.GenerateContentConfig(
                temperature=1,
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name,
                        )
                    )
                )
            )
        )
        
        # Extract audio data
        audio_data = response.candidates[0].content.parts[0].inline_data.data
        return audio_data
        
    except Exception as e:
        logger.error(f"Error generating segment audio: {str(e)}")
        raise e

def generate_segment_two_people_audio_with_text_and_voice(text, voice_name_1, voice_name_2):
    """
    Generate audio for a single segment_pair
    
    Args:
        segment_pair: Formatted text content for TTS
        
    Returns:
        bytes: Generated audio data
    """
    try:
        # Get API key
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        contents = [
            types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=text),
            ],
            ),
        ]
        # Generate audio for two speakers by providing multi_speaker_voice_config
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=contents,
            config=types.GenerateContentConfig(
            temperature=1,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                speaker_voice_configs=[
                    types.SpeakerVoiceConfig(
                    speaker='Speaker 1',
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name_1,
                        )
                    )
                    ),
                    types.SpeakerVoiceConfig(
                    speaker='Speaker 2',
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name_2,
                        )
                    )
                    ),
                ]
                )
            )
            )
        )
        
        # Extract audio data
        audio_data = response.candidates[0].content.parts[0].inline_data.data
        return audio_data
        
    except Exception as e:
        logger.error(f"Error generating segment audio: {str(e)}")
        raise e
      
def generate_segment_two_people_audio(segment_pair):
    """
    Generate audio for a single segment_pair
    
    Args:
        segment_pair: Formatted text content for TTS
        
    Returns:
        bytes: Generated audio data
    """
    try:
        # Get API key
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        
        # Trường hợp 2 người - dùng generate_segment_two_people_audio
        segment_text_1, voice_name_1, characteristics_1, role1 = segment_pair[0]
        segment_text_2, voice_name_2, characteristics_2, role2 = segment_pair[1]
        # Format contents theo yêu cầu mới
        def get_action_word(role):
            return "Read" if role.lower() == "narrator" else "Make"

        action_word_1 = get_action_word(role1)
        action_word_2 = get_action_word(role2)
        prompt_text = (
            f"Speaker 1 {action_word_1} aloud in a {characteristics_1}, Speaker 2 {action_word_2} aloud in a {characteristics_2}\n"
            f"Speaker 1: {segment_text_1}\n"
            f"Speaker 2: {segment_text_2}"
        )
        contents = [
            types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt_text),
            ],
            ),
        ]
        # Generate audio for two speakers by providing multi_speaker_voice_config
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=contents,
            config=types.GenerateContentConfig(
            temperature=1,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                speaker_voice_configs=[
                    types.SpeakerVoiceConfig(
                    speaker='Speaker1',
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name_1,
                        )
                    )
                    ),
                    types.SpeakerVoiceConfig(
                    speaker='Speaker2',
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name_2,
                        )
                    )
                    ),
                ]
                )
            )
            )
        )
        
        # Extract audio data
        audio_data = response.candidates[0].content.parts[0].inline_data.data
        return audio_data
        
    except Exception as e:
        logger.error(f"Error generating segment audio: {str(e)}")
        raise e
    
def create_segments_from_speakers(speakers):
    """
    Chia speakers list thành các cặp hội thoại (tối đa 2 đoạn một cặp) để sinh audio từng cặp.
    Chấp nhận trường hợp đoạn cuối chỉ có 1 người nói.

    Args:
        speakers: List of speaker dictionaries
    Returns:
        list: List các tuple [(formatted_text1, voice1), (formatted_text2, voice2)] cho mỗi cặp
              hoặc [(formatted_text1, voice1)] cho đoạn cuối có 1 người
    """
    segments = []
    
    # Validate input
    if not speakers:
        logger.error("Speakers data is empty or None")
        return segments
        
    if not isinstance(speakers, list):
        logger.error(f"Speakers data is not a list, got type: {type(speakers)}")
        return segments
    
    # Log speakers data for debugging
    for i, speaker in enumerate(speakers):
        if not isinstance(speaker, dict):
            logger.error(f"Speaker at index {i} is not a dictionary, got type: {type(speaker)}")
            continue
    
    # Sắp xếp theo thứ tự trong truyện
    try:
        sorted_speakers = sorted(speakers, key=lambda x: x.get('order_in_story', 0) if isinstance(x, dict) else 0)
    except Exception as e:
        logger.error(f"Error sorting speakers: {str(e)}")
        sorted_speakers = speakers
        
    # Gom thành từng cặp (tối đa 2 đoạn, chấp nhận 1 đoạn cho phần cuối)
    i = 0
    n = len(sorted_speakers)
    while i < n:
        pair = []
        processed_count = 0  # Đếm số speaker đã xử lý thực tế
        
        for j in range(2):
            if i + processed_count >= n:
                break
            speaker = sorted_speakers[i + processed_count]
            
            # Validate speaker is a dictionary
            if not isinstance(speaker, dict):
                logger.error(f"Speaker at position {i + processed_count} is not a dictionary: {type(speaker)}")
                processed_count += 1
                continue
                
            dialogue = speaker.get('dialogue') or ''
            dialogue = dialogue.strip() if dialogue else ''
            
            # Tăng processed_count trước khi kiểm tra dialogue
            processed_count += 1
            
            if not dialogue:
                # Nếu dialogue rỗng, tiếp tục với speaker tiếp theo nhưng không thêm vào pair
                continue

            name = speaker.get('name') or ''
            role = speaker.get('role') or ''
            context = speaker.get('context') or ''
            emotion = speaker.get('emotion') or 'bình thường'
            voice = speaker.get('voice') or ''
            characteristics = speaker.get('characteristics') or ''
            age_category = speaker.get('age_category') or ''
            gender = speaker.get('gender') or ''

            character_info = ""
            if name:
                character_info = f"Tên nhân vật là {name}, {age_category}, {gender}."

            formatted_line = (
                f"Hãy đọc đoạn thoại sau với vai trò là {role}, ngữ cảnh: {context}, cảm xúc: {emotion}. "
                f"Sử dụng giọng {characteristics}.\n"
                f"{character_info}\n"
                f"Đoạn thoại: \"{dialogue}\""
            )
            pair.append((dialogue.strip(), voice, characteristics, role))
        
        # Chấp nhận cả trường hợp có 1 hoặc 2 đoạn trong pair
        if pair:
            segments.append(pair)
        
        # Tăng i theo số speaker đã xử lý thực tế, nhưng tối thiểu là 1
        i += max(processed_count, 1)
    return segments

def generate_and_merge_multi_segment_audio(speakers_data, output_filename="output_dialogue.wav"):
    """
    Generate audio from multiple speakers and merge into single file
    
    Args:
        speakers_data: List of speaker dictionaries with 'name' and 'dialogue' keys
        output_filename: Output filename for merged audio
        
    Returns:
        str: Path to the generated audio file
    """
    try:
        # Create segments
        segments = create_segments_from_speakers(speakers_data)
        
        # Generate audio for each segment
        audio_files = []
        for segment_pair in segments:
            # Kiểm tra số lượng người trong segment_pair
            if len(segment_pair) == 1:
                # Trường hợp 1 người - dùng generate_segment_single_audio
                dialogue, voice, characteristics, role = segment_pair[0]
                audio_data = generate_segment_single_audio(dialogue, voice, characteristics, role)
                segment_filename = f"segment_{len(audio_files)+1}.wav"
                save_wave_file(segment_filename, audio_data)
                audio_files.append(segment_filename)
            elif len(segment_pair) == 2:
                audio_data = generate_segment_two_people_audio(segment_pair)
                segment_filename = f"segment_{len(audio_files)+1}.wav"
                save_wave_file(segment_filename, audio_data)
                audio_files.append(segment_filename)
            else:
                # Handle case where segment_pair has 0 or more than 2 speakers
                logger.warning(f"Skipping segment with {len(segment_pair)} speakers - not supported")
                continue
        
        # Merge audio files using pydub (if available)
        if PYDUB_AVAILABLE:
            try:
                combined_audio = AudioSegment.empty()
                for audio_file in audio_files:
                    audio_segment = AudioSegment.from_wav(audio_file)
                    combined_audio += audio_segment
                
                # Export merged audio
                combined_audio.export(output_filename, format="wav")
                
                # Cleanup temporary files
                for audio_file in audio_files:
                    try:
                        os.remove(audio_file)
                    except:
                        pass
                        
                return output_filename
                        
            except Exception as e:
                logger.error(f"Error merging audio with pydub: {str(e)}")
                return audio_files
        else:
            logger.warning("pydub not available - keeping separate segment files")
            return audio_files
        
    except Exception as e:
        logger.error(f"Error in multi-segment audio generation: {str(e)}")
        raise e

# Example usage and test data
def test_multi_segment_generation():
    """Test function for multi-segment audio generation"""
    test_speakers = [
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Đầu óc Lăng Tiếu như bị một nhát kiếm vô hình xé toạc, cơn đau buốt nhói chạy dọc sống lưng, khiến anh khẽ rên lên. Cảm giác cơ thể đang nằm trên một tấm nệm êm ái, mềm mại, khác hẳn nền đất lạnh lẽo mà anh từng nghĩ mình sẽ vĩnh viễn nằm lại.",
      "context": "Mô tả trạng thái đau đớn và cảm giác của Lăng Tiếu khi vừa tỉnh lại.",
      "emotion": "tường thuật",
      "order_in_story": 1,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 2,
      "name": "Lăng Tiếu",
      "age_category": "young",
      "gender": "male",
      "role": "child",
      "dialogue": "Mình đang ở đâu vậy? Sao đầu mình đau như búa bổ thế này? Chẳng lẽ... mình vẫn chưa chết?",
      "context": "Suy nghĩ nội tâm của Lăng Tiếu khi vừa tỉnh dậy, cảm thấy đau đớn và hoang mang.",
      "emotion": "lo lắng",
      "order_in_story": 2,
      "voice": "zephyr",
      "characteristics": "Giọng nam trẻ, khàn đặc, thể hiện sự hoang mang, đau đớn và ngạc nhiên."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Anh cố gắng mở nặng trĩu mi mắt. Trước tầm nhìn còn đang lờ mờ, nhòe đi vì cơn đau là bóng dáng một người phụ nữ. Bà mặc bộ trang phục giản dị, vải thô mộc, nhưng từng cử chỉ, từng nét mặt đều toát lên khí chất thanh tao, dịu dàng, không hề che giấu. Bà đang vội vàng lau đi những giọt nước mắt còn vương trên gò má hốc hác, đôi bàn tay gầy guộc run rẩy vuốt ve khuôn mặt anh.",
      "context": "Mô tả hành động của Lăng Tiếu và sự xuất hiện của người phụ nữ (mẹ anh).",
      "emotion": "tường thuật",
      "order_in_story": 3,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 3,
      "name": "Mộng Tích Vân",
      "age_category": "adult",
      "gender": "female",
      "role": "parent",
      "dialogue": "Tiếu nhi, con tỉnh rồi! Trời ơi, mẹ lo lắng muốn chết đi được!",
      "context": "Bày tỏ sự vui mừng và nhẹ nhõm khi thấy con trai tỉnh lại sau cơn nguy kịch.",
      "emotion": "vui",
      "order_in_story": 4,
      "voice": "autonoe",
      "characteristics": "Giọng nữ trung niên, run rẩy, vỡ òa vì vui mừng và nhẹ nhõm, thể hiện tình yêu thương và sự lo lắng sâu sắc."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Lăng Tiếu nhìn người phụ nữ xa lạ trước mắt, trong lòng dấy lên một cảm giác kỳ lạ, khó tả, vừa hoang mang vừa xen lẫn chút bối rối.",
      "context": "Mô tả cảm xúc hoang mang, bối rối của Lăng Tiếu khi nhìn thấy người phụ nữ lạ.",
      "emotion": "tường thuật",
      "order_in_story": 5,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 2,
      "name": "Lăng Tiếu",
      "age_category": "young",
      "gender": "male",
      "role": "child",
      "dialogue": "Đây là đâu? Sao mọi thứ lại... Mình tuy có chút tài lẻ trong việc ứng xử với phái nữ, nhưng tình cảnh này xem ra lại hơi vượt quá tầm kiểm soát của mình rồi...",
      "context": "Suy nghĩ nội tâm hoang mang, bối rối và có chút tự trào khi đối mặt với tình huống bất ngờ.",
      "emotion": "lo lắng",
      "order_in_story": 6,
      "voice": "zephyr",
      "characteristics": "Giọng nam trẻ, thể hiện sự bối rối, hoang mang và một chút hài hước nội tâm."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Anh còn chưa kịp suy nghĩ hết câu, một cơn đau đầu dữ dội hơn nữa lại ập đến, mạnh mẽ như một dòng lũ bất ngờ tràn vào não bộ. Những mảnh ký ức rời rạc, vụn vặt, hỗn loạn xô đẩy mọi thứ vốn đã mơ hồ trong tâm trí anh, khiến anh choáng váng.",
      "context": "Mô tả cơn đau đầu dữ dội và sự hỗn loạn ký ức ập đến với Lăng Tiếu.",
      "emotion": "tường thuật",
      "order_in_story": 7,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 3,
      "name": "Mộng Tích Vân",
      "age_category": "adult",
      "gender": "female",
      "role": "parent",
      "dialogue": "Tiếu nhi, con sao vậy? Còn thấy khó chịu ở đâu không? Con đừng dọa mẹ!",
      "context": "Hốt hoảng hỏi han khi thấy biểu hiện đau đớn, bất thường của con trai.",
      "emotion": "lo lắng",
      "order_in_story": 8,
      "voice": "autonoe",
      "characteristics": "Giọng nữ trung niên, gấp gáp, thể hiện sự lo lắng, hoảng hốt tột độ."
    },
    {
      "speaker_id": 2,
      "name": "Lăng Tiếu",
      "age_category": "young",
      "gender": "male",
      "role": "child",
      "dialogue": "Không, không, con không sao cả. Mẹ, con không sao cả.",
      "context": "Cố gắng trấn an mẹ mình dù bản thân đang rất đau đớn và bối rối.",
      "emotion": "bình thường",
      "order_in_story": 9,
      "voice": "zephyr",
      "characteristics": "Giọng nam trẻ, cố gắng tỏ ra trấn tĩnh, có chút gấp gáp và hổn hển."
    },
    {
      "speaker_id": 2,
      "name": "Lăng Tiếu",
      "age_category": "young",
      "gender": "male",
      "role": "child",
      "dialogue": "Chết tiệt! Mình... mình lại xuyên không rồi sao?",
      "context": "Suy nghĩ nội tâm thể hiện sự bàng hoàng, khó tin khi nhận ra mình đã xuyên không.",
      "emotion": "tức giận",
      "order_in_story": 10,
      "voice": "zephyr",
      "characteristics": "Giọng nam trẻ, nói thầm, thể hiện sự bực tức, bất lực và khó tin."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Lăng Tiếu thầm rủa trong lòng, một cảm giác vừa bất lực vừa khó tin. Anh hoàn toàn ý thức được mình không còn ở Trái Đất quen thuộc nữa, mà đã lạc bước đến một thế giới hoàn toàn xa lạ mang tên Huyền Linh Đại Lục. Anh nhớ lại trận chiến sinh tử khốc liệt với bốn cao thủ đỉnh phong của Quỷ Môn, nhớ đến khoảnh khắc liều lĩnh tự bạo Đan Điền để bảo toàn mạng sống, và rồi... anh đã có một cơ hội thứ hai. Vận may của anh đúng là không tồi chút nào. Và người phụ nữ đang đứng trước mặt anh, không ai khác chính là mẫu thân của thân thể này, Mộng Tích Vân.",
      "context": "Giải thích về việc Lăng Tiếu nhận ra mình đã xuyên không, hồi tưởng về kiếp trước và xác nhận thân phận của người mẹ.",
      "emotion": "tường thuật",
      "order_in_story": 11,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 3,
      "name": "Mộng Tích Vân",
      "age_category": "adult",
      "gender": "female",
      "role": "parent",
      "dialogue": "Không sao là tốt rồi. Từ giờ con đừng đi luyện võ nữa nhé, để tránh bị người ta bắt nạt. Nhìn con giờ đây, mẹ thấy con giống hệt cha con ngày xưa, thật khiến mẹ đau lòng.",
      "context": "Dặn dò con trai trong sự xót xa và đau lòng khi nghĩ về quá khứ của chồng và con.",
      "emotion": "buồn",
      "order_in_story": 12,
      "voice": "autonoe",
      "characteristics": "Giọng nữ trung niên, nhẹ nhàng, đầy xót xa và đau buồn, thể hiện sự lo lắng của người mẹ."
    },
    {
      "speaker_id": 2,
      "name": "Lăng Tiếu",
      "age_category": "young",
      "gender": "male",
      "role": "child",
      "dialogue": "Vâng, con nghe lời mẹ. Mẹ, mẹ ra ngoài một chút được không ạ? Con cảm thấy hơi mệt, muốn nghỉ ngơi thêm một lát.",
      "context": "Vâng lời mẹ và muốn có không gian riêng để sắp xếp lại suy nghĩ, ký ức hỗn loạn.",
      "emotion": "bình thường",
      "order_in_story": 13,
      "voice": "zephyr",
      "characteristics": "Giọng nam trẻ, ngoan ngoãn nhưng có chút xa cách, cố gắng tỏ ra mệt mỏi."
    },
    {
      "speaker_id": 3,
      "name": "Mộng Tích Vân",
      "age_category": "adult",
      "gender": "female",
      "role": "parent",
      "dialogue": "Được, mẹ không làm phiền con nữa. Con cứ ngủ thêm đi.",
      "context": "Đồng ý để con trai nghỉ ngơi, thể hiện sự quan tâm và yêu thương.",
      "emotion": "buồn",
      "order_in_story": 14,
      "voice": "autonoe",
      "characteristics": "Giọng nữ trung niên, nghẹn ngào nhưng vẫn cố gắng dịu dàng, đầy trìu mến."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Mộng Tích Vân lau vội những giọt nước mắt còn vương trên má, giọng nói vẫn còn nghẹn ngào. Bà nhẹ nhàng kéo chăn đắp cẩn thận cho con trai, đôi mắt trìu mến nhìn anh thêm một lúc, rồi mới rời khỏi phòng, không quên khép hờ cánh cửa lại, tạo một khoảng không yên tĩnh cho anh.",
      "context": "Mô tả hành động chăm sóc và tình yêu thương của Mộng Tích Vân dành cho Lăng Tiếu trước khi rời đi.",
      "emotion": "tường thuật",
      "order_in_story": 15,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Lăng Tiếu cố tình bảo mẹ ra ngoài để có thời gian sắp xếp lại mớ ký ức hỗn loạn đang quay cuồng trong đầu mình. Anh nhắm mắt lại, hít thở sâu, từng chút một gỡ rối những sợi tơ vò trong tâm trí.",
      "context": "Mô tả hành động của Lăng Tiếu khi ở một mình, cố gắng sắp xếp lại ký ức.",
      "emotion": "tường thuật",
      "order_in_story": 16,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Sau gần một canh giờ tĩnh lặng, khi ánh chiều tà bắt đầu len lỏi qua khe cửa, anh mới chậm rãi mở mắt ra, thở phào nhẹ nhõm.",
      "context": "Mô tả khung cảnh và hành động của Lăng Tiếu sau khi đã sắp xếp xong ký ức.",
      "emotion": "tường thuật",
      "order_in_story": 17,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 2,
      "name": "Lăng Tiếu",
      "age_category": "young",
      "gender": "male",
      "role": "child",
      "dialogue": "Tình hình còn tốt hơn mình tưởng tượng nhiều. Ít nhất thì mình vẫn còn sống.",
      "context": "Tự nhủ sau khi đã bình tĩnh và sắp xếp lại ký ức, cảm thấy nhẹ nhõm vì có cơ hội sống lại.",
      "emotion": "bình thường",
      "order_in_story": 18,
      "voice": "zephyr",
      "characteristics": "Giọng nam trẻ, trầm ngâm, thể hiện sự nhẹ nhõm và chấp nhận thực tại."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Anh bắt đầu tập trung sắp xếp lại những ký ức của thân thể nguyên chủ. Hóa ra, anh đã trọng sinh vào một thiếu niên tên Lăng Tiếu, thuộc Lăng gia tại Vẫn Thạch thành. Lý do anh có được thân thể này, có lẽ là do \"trong minh minh sớm đã chú định\", một sự sắp đặt kỳ diệu của số phận.",
      "context": "Giải thích về quá trình Lăng Tiếu tiếp nhận ký ức của thân thể mới và sự thật về việc trọng sinh.",
      "emotion": "tường thuật",
      "order_in_story": 19,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Nguyên lai, \"Lăng Tiếu\" vốn là thiên tài tu luyện xuất sắc nhất của Lăng gia đời thứ mười tám. Năm mới mười lăm tuổi, cậu đã xuất sắc đột phá đến Huyền Giả giai, trở thành một Huyền Sĩ cấp thấp, vang danh khắp Vẫn Thạch thành với biệt danh \"Đệ nhất thiên tài\". Thế nhưng, \"cây cao gió lớn\", tài năng xuất chúng của cậu không tránh khỏi tai ương. Không lâu sau khi trở thành Huyền Sĩ, \"Lăng Tiếu\" đã bị kẻ gian ám hại, toàn bộ kinh mạch trên cơ thể đều bị phế bỏ. Từ một Huyền Sĩ đang trên đỉnh cao phong quang vô hạn, cậu bỗng chốc trở thành một phế nhân bình thường, ngay cả một Võ Đồ cũng không bằng. Danh tiếng \"đệ nhất thiên tài\" giờ đây biến thành \"phế vật\", bị người đời xa lánh, khinh miệt, thậm chí là chà đạp. Trong một thế giới nơi võ đạo được tôn sùng tuyệt đối, nơi \"võ là vương\", lại còn sống trong Lăng gia – gia tộc quyền lực đứng đầu Vẫn Thạch thành, việc không thể luyện võ đồng nghĩa với một tương lai mờ mịt, tầm thường, thậm chí là vô vọng. Tuy nhiên, \"Lăng Tiếu\" nguyên bản lại sở hữu một ý chí kiên cường phi thường. Cậu bắt đầu lại từ đầu, cố gắng tu luyện không ngừng nghỉ, nhưng hai năm trôi qua, mọi nỗ lực của cậu đều trở nên vô ích. Suốt hai năm dài đằng đẵng ấy, cậu chỉ có thể nhẫn nhịn những lời châm chọc, cười nhạo từ những người trong Lăng gia và cả những người dân bên ngoài, những ánh mắt khinh bỉ như mũi dao đâm vào tim. Chỉ hai ngày trước, cháu trai của Lăng gia ngũ trưởng lão, Lăng Duệ, đã cố tình khiêu khích \"Lăng Tiếu\" ngay trước mặt mọi người. Đỉnh điểm của sự sỉ nhục là khi Lăng Duệ dám buông lời xúc phạm cha mẹ cậu. Dù hổ sa cơ, \"Lăng Tiếu\" có thể chịu đựng mọi lời chế giễu về bản thân mình, nhưng cậu không thể dung thứ cho kẻ dám nhục mạ cha mẹ. Nén giận, cậu đã xuất thủ với Lăng Duệ. Nhưng với một thân thể phế bỏ, làm sao cậu có thể là đối thủ của một Huyền Giả cấp thấp như Lăng Duệ? Kết quả là cậu bị đánh cho một trận thập tử nhất sinh, và giờ đây, Lăng Tiếu đã nằm trên giường này, đón nhận một linh hồn mới.",
      "context": "Kể lại chi tiết quá khứ của thân thể nguyên chủ - từ một thiên tài trở thành phế vật, sự kiên trì và lý do bị trọng thương dẫn đến cái chết.",
      "emotion": "tường thuật",
      "order_in_story": 20,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 2,
      "name": "Lăng Tiếu",
      "age_category": "young",
      "gender": "male",
      "role": "child",
      "dialogue": "Thế giới của cường giả sao? Thật sự rất hợp ý ta!",
      "context": "Bày tỏ sự hào hứng và thích thú với thế giới mới, một thế giới tôn sùng sức mạnh.",
      "emotion": "hào hứng",
      "order_in_story": 21,
      "voice": "zephyr",
      "characteristics": "Giọng nam trẻ, đầy tự tin, có chút ngạo nghễ và tàn nhẫn."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Lăng Tiếu nói, đôi mắt lóe lên tia sáng tự tin, pha chút tàn nhẫn của kẻ từng đứng trên đỉnh cao. Anh bước xuống giường, sờ nắn thân thể vốn đã suy nhược, cảm nhận vết thương trên ót vẫn còn sưng tấy, nhức nhối.",
      "context": "Mô tả hành động và thần thái của Lăng Tiếu sau khi chấp nhận thế giới mới.",
      "emotion": "tường thuật",
      "order_in_story": 22,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 2,
      "name": "Lăng Tiếu",
      "age_category": "young",
      "gender": "male",
      "role": "child",
      "dialogue": "Mối thù của ngươi, ta sẽ thay ngươi báo đáp, Lăng Tiếu!",
      "context": "Hứa hẹn với linh hồn của thân thể nguyên chủ rằng mình sẽ báo thù cho cậu.",
      "emotion": "hào hứng",
      "order_in_story": 23,
      "voice": "zephyr",
      "characteristics": "Giọng nam trẻ, kiên định, lạnh lùng, thể hiện quyết tâm báo thù."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Anh bắt đầu quan sát căn phòng. Căn phòng khá rộng rãi, nhưng cách bài trí lại vô cùng đơn giản, gần như thô sơ. Ngoài chiếc giường lớn anh vừa nằm, chỉ có vài chiếc ghế gỗ sần sùi và một bàn trà nhỏ đã sờn cũ. Ở một góc phòng, một cây cọc gỗ đã xơ xác, đầy vết chém được dựng lên, chứng tỏ \"Lăng Tiếu\" nguyên bản đã từng khổ luyện đến nhường nào, dù cuối cùng mọi nỗ lực đều tan thành mây khói, biến thành nỗi thất vọng cùng cực.",
      "context": "Mô tả căn phòng đơn sơ của Lăng Tiếu và những dấu vết về sự khổ luyện trong vô vọng của nguyên chủ.",
      "emotion": "tường thuật",
      "order_in_story": 24,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Cánh cửa \"kẽo kẹt\" vang lên, rồi từ từ mở ra. Một người đàn ông trung niên với vẻ ngoài hào sảng nhưng ẩn chứa nét ưu tư bước vào, ước chừng ngoài ba mươi. Khuôn mặt góc cạnh rõ ràng, sống mũi cao thẳng, đôi mắt thoáng nét u buồn sâu thẳm. Ông ta mặc một bộ áo bào xám đơn giản, trên tay cầm một chai rượu. Nếu ở kiếp trước, hình tượng này có lẽ thuộc về những kẻ sát thủ bí ẩn trong truyền thuyết, mang vẻ lạnh lùng và nguy hiểm, nhưng ở thế giới này, ông chỉ là một trung niên nhân có vẻ ngoài chán chường, dường như đã bị cuộc đời vùi dập.",
      "context": "Mô tả sự xuất hiện và ngoại hình ưu tư, chán chường của Lăng Chiến, cha của Lăng Tiếu.",
      "emotion": "tường thuật",
      "order_in_story": 25,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Đây chính là phụ thân của Lăng Tiếu, Lăng Chiến. Ông cũng là một phế nhân, kinh mạch đã bị hủy hoại. Hai cha con \"phế vật\" này nổi danh khắp Vẫn Thạch thành không phải vì tài năng, mà vì hoàn cảnh đáng thương của mình, trở thành đề tài cho những lời đàm tiếu. Mười mấy năm trước, Lăng Chiến cũng là một thiên tài hiếm có của Vẫn Thạch thành. Dù không đến mức \"biến thái\" như Lăng Tiếu nguyên bản, nhưng ở tuổi mười tám, ông đã xuất sắc đột phá đến Huyền Giả giai, trở thành một Huyền Sĩ. Đến năm hai mươi lăm tuổi, ông đã đạt đến đỉnh phong Huyền Sĩ, chỉ còn cách Linh Sư cảnh giới – những cao thủ được liệt vào hàng tối cao của Vẫn Thạch thành. Đáng tiếc, dự định phấn đấu vươn lên của ông cũng kết thúc bằng một bi kịch tàn phế, giống hệt hoàn cảnh của Lăng Tiếu hiện tại, thật khiến người ta cảm khái về sự trớ trêu của số phận.",
      "context": "Giới thiệu thân phận và quá khứ bi kịch của Lăng Chiến, từ một thiên tài trở thành phế nhân.",
      "emotion": "tường thuật",
      "order_in_story": 26,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 4,
      "name": "Lăng Chiến",
      "age_category": "adult",
      "gender": "male",
      "role": "parent",
      "dialogue": "Cảm giác thế nào rồi, con trai?",
      "context": "Hỏi thăm tình hình sức khỏe của con trai với giọng điệu trầm, mệt mỏi.",
      "emotion": "bình thường",
      "order_in_story": 27,
      "voice": "schedar",
      "characteristics": "Giọng nam trung niên, trầm, chứa đựng sự mệt mỏi và ưu tư."
    },
    {
      "speaker_id": 2,
      "name": "Lăng Tiếu",
      "age_category": "young",
      "gender": "male",
      "role": "child",
      "dialogue": "Vẫn còn sống!",
      "context": "Trả lời câu hỏi của cha một cách ngắn gọn, có chút bất cần.",
      "emotion": "bình thường",
      "order_in_story": 28,
      "voice": "zephyr",
      "characteristics": "Giọng nam trẻ, cộc lốc, thể hiện một chút thái độ xa cách."
    },
    {
      "speaker_id": 4,
      "name": "Lăng Chiến",
      "age_category": "adult",
      "gender": "male",
      "role": "parent",
      "dialogue": "Vậy thì tốt!",
      "context": "Đáp lại câu trả lời của con trai, không thể hiện nhiều cảm xúc.",
      "emotion": "bình thường",
      "order_in_story": 29,
      "voice": "schedar",
      "characteristics": "Giọng nam trung niên, trầm, ngắn gọn."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Lăng Chiến ngồi xuống mép giường, rồi đột nhiên đưa chai rượu ra, hỏi:",
      "context": "Mô tả hành động của Lăng Chiến trước khi mời con trai uống rượu.",
      "emotion": "tường thuật",
      "order_in_story": 30,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 4,
      "name": "Lăng Chiến",
      "age_category": "adult",
      "gender": "male",
      "role": "parent",
      "dialogue": "Muốn uống một ngụm không?",
      "context": "Mời con trai uống rượu, một hành động bất ngờ.",
      "emotion": "bình thường",
      "order_in_story": 31,
      "voice": "schedar",
      "characteristics": "Giọng nam trung niên, trầm, như một lời đề nghị giữa những người đàn ông."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Lăng Tiếu không khách khí, giật lấy chai rượu, ngửa đầu uống một ngụm lớn. Vị cay nóng lan tỏa khắp cơ thể, khiến anh khẽ thở phào một cách thoải mái, xua đi phần nào sự nặng nề trong lòng. Anh tiếp tục uống thêm vài ngụm nữa. Ở kiếp trước, anh cũng không ít lần thử qua những loại rượu mạnh như Thiêu Đao Tử, Nữ Nhi Hồng, Trần Niên Lão Tứ...",
      "context": "Mô tả hành động uống rượu của Lăng Tiếu và suy nghĩ về các loại rượu ở kiếp trước.",
      "emotion": "tường thuật",
      "order_in_story": 32,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 4,
      "name": "Lăng Chiến",
      "age_category": "adult",
      "gender": "male",
      "role": "parent",
      "dialogue": "Ta không ngờ ngươi lại thích uống rượu mạnh như vậy,",
      "context": "Bày tỏ sự ngạc nhiên nhưng cũng có chút đồng cảm khi thấy con trai uống rượu.",
      "emotion": "bình thường",
      "order_in_story": 33,
      "voice": "schedar",
      "characteristics": "Giọng nam trung niên, trầm, có chút ngạc nhiên và thấu hiểu."
    },
    {
      "speaker_id": 2,
      "name": "Lăng Tiếu",
      "age_category": "young",
      "gender": "male",
      "role": "child",
      "dialogue": "Chỉ là cảm thấy... nó giúp ta quên đi một chút chuyện thôi,",
      "context": "Giải thích lý do uống rượu một cách qua loa, không muốn tiết lộ sự thật.",
      "emotion": "bình thường",
      "order_in_story": 34,
      "voice": "zephyr",
      "characteristics": "Giọng nam trẻ, có chút lảng tránh, bình thản."
    },
    {
      "speaker_id": 4,
      "name": "Lăng Chiến",
      "age_category": "adult",
      "gender": "male",
      "role": "parent",
      "dialogue": "Ta hiểu. Ta cũng từng trải qua những ngày tháng như vậy. Con có biết, ta đã luôn mong chờ ngày này.",
      "context": "Bày tỏ sự đồng cảm sâu sắc với con trai và tiết lộ nỗi lòng mong chờ bấy lâu.",
      "emotion": "buồn",
      "order_in_story": 35,
      "voice": "schedar",
      "characteristics": "Giọng nam trung niên, trầm buồn, nghẹn ngào, chất chứa nhiều tâm sự."
    },
    {
      "speaker_id": 2,
      "name": "Lăng Tiếu",
      "age_category": "young",
      "gender": "male",
      "role": "child",
      "dialogue": "Mong chờ ngày gì ạ?",
      "context": "Hỏi lại cha mình để làm rõ ý, thể hiện sự tò mò.",
      "emotion": "bình thường",
      "order_in_story": 36,
      "voice": "zephyr",
      "characteristics": "Giọng nam trẻ, thể hiện sự tò mò, thắc mắc."
    },
    {
      "speaker_id": 4,
      "name": "Lăng Chiến",
      "age_category": "adult",
      "gender": "male",
      "role": "parent",
      "dialogue": "Mong chờ ngày con tỉnh lại. Dù là bất cứ ai, dù là con hay là một ai đó khác, chỉ cần con tỉnh lại, đó đã là điều ta mong chờ nhất rồi. Mẹ con, bà ấy vì quá lo lắng cho con mà bệnh tình càng thêm nặng. Ta không muốn mất thêm bất kỳ ai nữa.",
      "context": "Giải thích nỗi lòng, sự tuyệt vọng và tình yêu thương vô bờ bến dành cho gia đình.",
      "emotion": "buồn",
      "order_in_story": 37,
      "voice": "schedar",
      "characteristics": "Giọng nam trung niên, nghẹn ngào, đau đớn, thể hiện sự bất lực và lo sợ mất mát."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Lăng Tiếu im lặng, anh cảm nhận được sự chân thành và tình yêu thương vô bờ bến trong lời nói của Lăng Chiến. Dù sao thì, đây cũng là cha mẹ ruột của thân thể này, những người đã chịu đựng quá nhiều đau khổ.",
      "context": "Mô tả sự cảm động và thấu hiểu của Lăng Tiếu trước tình cảm của người cha.",
      "emotion": "tường thuật",
      "order_in_story": 38,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 2,
      "name": "Lăng Tiếu",
      "age_category": "young",
      "gender": "male",
      "role": "child",
      "dialogue": "Con hiểu rồi. Con sẽ cố gắng để mẹ mau khỏe lại.",
      "context": "Hứa với cha sẽ chăm sóc cho mẹ, thể hiện sự chấp nhận và trách nhiệm.",
      "emotion": "bình thường",
      "order_in_story": 39,
      "voice": "zephyr",
      "characteristics": "Giọng nam trẻ, kiên định, chân thành."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Lăng Chiến nhìn con trai, trong mắt ông hiện lên một tia hy vọng mong manh nhưng rực sáng.",
      "context": "Mô tả phản ứng của Lăng Chiến, cho thấy ông tìm thấy hy vọng từ lời nói của con trai.",
      "emotion": "tường thuật",
      "order_in_story": 40,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 4,
      "name": "Lăng Chiến",
      "age_category": "adult",
      "gender": "male",
      "role": "parent",
      "dialogue": "Tốt lắm. Giờ con nghỉ ngơi đi. Ta đi xem mẹ con thế nào.",
      "context": "Bảo con trai nghỉ ngơi và thể hiện sự quan tâm đến vợ.",
      "emotion": "bình thường",
      "order_in_story": 41,
      "voice": "schedar",
      "characteristics": "Giọng nam trung niên, có chút nhẹ nhõm, dặn dò."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Ông đứng dậy, bước ra khỏi phòng, để lại Lăng Tiếu một mình với những suy nghĩ miên man, nhưng không còn hỗn loạn nữa.",
      "context": "Mô tả hành động Lăng Chiến rời đi và trạng thái tâm trí của Lăng Tiếu.",
      "emotion": "tường thuật",
      "order_in_story": 42,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Anh nhìn lại thân thể mình, cảm nhận sự yếu ớt, nhưng trong lòng lại dâng lên một ngọn lửa quyết tâm rực cháy.",
      "context": "Mô tả trạng thái nội tâm của Lăng Tiếu, sự tương phản giữa thể chất và ý chí.",
      "emotion": "tường thuật",
      "order_in_story": 43,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, kể lại câu chuyện một cách khách quan nhưng có điểm nhấn vào cảm xúc nhân vật."
    },
    {
      "speaker_id": 2,
      "name": "Lăng Tiếu",
      "age_category": "young",
      "gender": "male",
      "role": "child",
      "dialogue": "Thế giới này, ta sẽ không để mình giống như những kẻ phế vật trước đây nữa. Ta sẽ tìm lại con đường võ đạo, báo thù cho Lăng Tiếu nguyên bản, và bảo vệ những người thân yêu của mình!",
      "context": "Suy nghĩ nội tâm, hạ quyết tâm về tương lai ở thế giới mới, báo thù và bảo vệ gia đình.",
      "emotion": "hào hứng",
      "order_in_story": 44,
      "voice": "zephyr",
      "characteristics": "Giọng nam trẻ, mạnh mẽ, đầy quyết tâm và ý chí kiên định."
    },
    {
      "speaker_id": 1,
      "name": "Người dẫn truyện",
      "age_category": "adult",
      "gender": "female",
      "role": "narrator",
      "dialogue": "Anh siết chặt tay, đôi mắt ánh lên một vẻ kiên định lạ thường, như một ngọn đuốc thắp sáng bóng đêm. Cuộc đời mới của Lăng Tiếu, giờ đây đã chính thức bắt đầu, hứa hẹn một hành trình đầy cam go nhưng cũng vô cùng vinh quang.",
      "context": "Lời kết, mô tả sự quyết tâm của Lăng Tiếu và mở ra một chặng đường mới cho nhân vật.",
      "emotion": "tường thuật",
      "order_in_story": 45,
      "voice": "algieba",
      "characteristics": "Giọng nữ, trưởng thành, truyền cảm, có phần hào hùng để kết thúc đoạn trích."
    }
  ]
    
    try:
        result = generate_and_merge_multi_segment_audio(test_speakers)
        print(f"✓ Test completed successfully: {result}")
        return result
    except Exception as e:
        print(f"✗ Test failed: {str(e)}")
        return None

# Remove the inline execution code and replace with organized functions
# The old inline code has been refactored into the functions above

# Removed duplicate process_speakers_content function
# Logic has been consolidated into create_segments_from_speakers

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file header for the given audio data and parameters.

    Args:
        audio_data: The raw audio data as a bytes object.
        mime_type: Mime type of the audio data.

    Returns:
        A bytes object representing the WAV file with proper header.
    """
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size  # 36 bytes for header fields before data chunk size

    # http://soundfile.sapp.org/doc/WaveFormat/
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",          # ChunkID
        chunk_size,       # ChunkSize (total file size - 8 bytes)
        b"WAVE",          # Format
        b"fmt ",          # Subchunk1ID
        16,               # Subchunk1Size (16 for PCM)
        1,                # AudioFormat (1 for PCM)
        num_channels,     # NumChannels
        sample_rate,      # SampleRate
        byte_rate,        # ByteRate
        block_align,      # BlockAlign
        bits_per_sample,  # BitsPerSample
        b"data",          # Subchunk2ID
        data_size         # Subchunk2Size (size of audio data)
    )
    return header + audio_data

def parse_audio_mime_type(mime_type: str) -> dict:
    """Parses bits per sample and rate from an audio MIME type string.

    Args:
        mime_type: The audio MIME type string (e.g., "audio/L16;rate=24000").

    Returns:
        A dictionary with "bits_per_sample" and "rate" keys.
    """
    bits_per_sample = 16
    rate = 24000

    # Extract rate from parameters
    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                # Handle cases like "rate=" with no value or non-integer value
                pass # Keep rate as default
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass # Keep bits_per_sample as default if conversion fails

    return {"bits_per_sample": bits_per_sample, "rate": rate}
