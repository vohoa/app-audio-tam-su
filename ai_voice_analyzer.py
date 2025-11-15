"""
AI-Powered Voice Analyzer using Gemini AI
Automatically analyzes Vietnamese text and generates speech configuration
"""

import json
import logging
from google import genai
from google.genai import types
from decouple import config

logger = logging.getLogger(__name__)

class AIVoiceAnalyzer:
    """
    Uses Gemini AI to analyze Vietnamese text content and generate 
    intelligent voice configurations for multi-speaker TTS
    """
    
    def __init__(self):
        self.api_key = config('GEMINI_API_KEY', default='')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        self.client = genai.Client(api_key=self.api_key)
    
    
    def create_analysis_prompt(self, text_content):
        """Create analysis prompt for Gemini AI"""

        prompt = f"""
        Phân tích đoạn văn bản tiếng Việt sau đây và xác định thông tin về các nhân vật có lời thoại và người dẫn truyện theo thứ tự xuất hiện trong câu chuyện:

        VĂN BẢN:
        {text_content}

        Hãy phân tích và trả về thông tin dưới dạng JSON với cấu trúc:
        {{
        "speakers": [
        {{
            "speaker_id": 1,
            "name": "tên nhân vật (nếu có)",
            "age_category": "child|young|adult|elderly", 
            "gender": "male|female|unknown",
            "role": "child|parent|grandparent|teacher|authority|neutral|narrator",
            "dialogue": "lời thoại đầy đủ của nhân vật hoặc phần dẫn truyện",
            "context": "tình huống/hoàn cảnh khi nhân vật nói hoặc phần mô tả",
            "emotion": "cảm xúc chủ đạo (vui|buồn|tức giận|lo lắng|bình thường|hào hứng|tường thuật)",
            "order_in_story": 1,
            "voice": "Tên voice phù hợp với đặc điểm nhân vật và giới tính, chỉ chọn một trong các tên sau: achernar, achird, algenib, algieba, alnilam, aoede, autonoe, callirrhoe, charon, despina, enceladus, erinome, fenrir, gacrux, iapetus, kore, laomedeia, leda, orus, puck, pulcherrima, rasalgethi, sadachbia, sadaltager, schedar, sulafat, umbriel, vindemiatrix, zephyr, zubenelgenubi",
            "characteristics": "mô tả đặc điểm giọng nói phù hợp"
        }}
        ]
        }}

    HƯỚNG DẪN PHÂN TÍCH QUAN TRỌNG:
    1. SẮP XẾP THEO THỨ TỰ: Các speakers phải được sắp xếp theo thứ tự xuất hiện trong câu chuyện từ đầu đến cuối
    2. ĐÁNH SỐ THỨ TỰ: Gán order_in_story bắt đầu từ 1 cho đoạn hội thoại đầu tiên
    3. NGƯỜI DẪN TRUYỆN: 
       - Các phần mô tả, tường thuật không phải lời thoại của nhân vật sẽ được gán cho người dẫn truyện
       - Role: "narrator"
       - Emotion: "tường thuật" 
       - Voice: hệ thống chọn algieba
    4. TÌNH HUỐNG: Mô tả ngắn gọn tình huống khi nhân vật đang nói (ví dụ: "đang hỏi thăm", "phản đối quyết định", "giải thích vấn đề")
    5. CẢM XÚC: Xác định cảm xúc chủ đạo để lựa chọn giọng đọc phù hợp
    6. PHÂN TÍCH ĐỘ TUỔI: Dựa vào cách xưng hô (con, cháu, mẹ, ông, bà...) và ngữ cảnh
    7. NHẬN DẠNG GIỚI TÍNH: Từ danh xưng, vai trò và ngữ cảnh câu chuyện
    8. LỜI THOẠI ĐẦY ĐỦ: Ghi lại toàn bộ lời nói của nhân vật hoặc phần dẫn truyện, không rút gọn
    9. VAI TRÒ TRONG CÂU CHUYỆN: Xác định vai trò và mối quan hệ giữa các nhân vật
    10. PHÂN BIỆT LỜI THOẠI VÀ DẪN TRUYỆN:
        - Lời thoại: thường trong dấu ngoặc kép hoặc có từ chỉ nói như "nói", "hỏi", "trả lời"
        - Dẫn truyện: phần mô tả hành động, cảnh vật, tình huống, suy nghĩ của nhân vật

    CHÚ Ý: 
    - Mỗi lần xuất hiện hội thoại của cùng một nhân vật sẽ tạo một speaker entry riêng biệt với order_in_story tăng dần
    - Phần dẫn truyện cũng tạo speaker entry riêng với is_narrator: true
    - Trường "voice" chỉ được chọn một tên duy nhất trong danh sách allowed voice names đã cho ở trên
    - Ưu tiên voice phù hợp nhân vật dùng giọng phù hợp với đặc điểm

    Chỉ trả về JSON, không thêm text khác.
    """
        try:
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-pro",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                    )
                )
            except Exception as e:
                logger.error(f"Gemini API call failed: {e}")
                raise RuntimeError("Gemini API service is currently unavailable. Please try again later.") from e
            
            ai_text = response.candidates[0].content.parts[0].text
            
            # Parse JSON response
            try:
                # Remove markdown code blocks if present
                clean_text = ai_text.strip()
                if clean_text.startswith('```json'):
                    clean_text = clean_text[7:]
                if clean_text.endswith('```'):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()
                
                ai_analysis = json.loads(clean_text)
                return ai_analysis
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', clean_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    raise e
                    
        except Exception as e:
            logger.error(f"Error getting AI analysis: {str(e)}")
            raise e


    def generate_content_analysis_story_chapter(self, text_content):
        """Generate enhanced story content with better dialogue and structure"""
        
        prompt = f"""
Bạn là một nhà văn chuyên nghiệp có kinh nghiệm viết truyện tình cảm, tiểu thuyết, tiên hiệp, kiếm hiệp và kể chuyện. Nhiệm vụ của bạn là cải thiện và viết lại đoạn văn bản tiếng Việt sau đây để tạo ra một câu chuyện hấp dẫn, sinh động và cuốn hút hơn.

VĂN BẢN GỐC:
{text_content}

YÊU CẦU VIẾT LẠI:

1. **NGÔN NGỮ VÀ CÚ PHÁP:**
   - Sửa lỗi chính tả, ngữ pháp và cú pháp
   - Sử dụng từ ngữ phong phú, tự nhiên và phù hợp với độ tuổi
   - Đảm bảo câu văn mạch lạc, dễ hiểu

2. **CẤU TRÚC CÂU CHUYỆN:**
   - Tạo mở đầu thu hút, phát triển nội dung hợp lý, kết thúc ấn tượng
   - Xây dựng nhịp độ câu chuyện hấp dẫn, có điểm nhấn
   - Kết nối các sự kiện một cách tự nhiên và logic

3. **HỘI THOẠI VÀ NHÂN VẬT:**
   - Tạo thêm hội thoại sinh động, tự nhiên giữa các nhân vật
   - Thể hiện rõ tính cách, cảm xúc của từng nhân vật qua lời nói
   - Sử dụng ngôn ngữ phù hợp với độ tuổi và vai trò của nhân vật
   - Thêm chi tiết mô tả cử chỉ, biểu cảm để làm sống động hội thoại
   - **QUY TẮC DẤU NGOẶC KÉP TỰ ĐỘNG:** 
     * Bạn hãy TỰ ĐỘNG NHẬN DIỆN đâu là hội thoại của nhân vật và đâu là phần dẫn truyện
     * TẤT CẢ các câu nói trực tiếp của nhân vật (kể cả cũ và mới) đều phải có dấu ngoặc kép "..."
     * Phần dẫn truyện, mô tả hành động, cảnh vật KHÔNG có dấu ngoặc kép
     * KHÔNG cần phân biệt câu thoại cũ hay mới - hãy xử lý thống nhất theo logic hội thoại

4. **MÔ TẢ VÀ KHÔNG GIAN:**
   - Bổ sung mô tả không gian, bối cảnh sinh động
   - Sử dụng các giác quan để tạo hình ảnh sống động
   - Mô tả cảm xúc, tâm trạng nhân vật một cách tinh tế

5. **YẾU TỐ HẤP DẪN:**
   - Tạo yếu tố bất ngờ, thú vị phù hợp với nội dung
   - Xây dựng xung đột nhẹ nhàng để tạo hồi hộp
   - Thêm các chi tiết đặc biệt, thú vị để câu chuyện thêm cuốn hút

6. **GIÁ TRỊ GIÁO DỤC:**
   - Giữ nguyên thông điệp tích cực, bài học ý nghĩa
   - Thể hiện các giá trị đạo đức, tình cảm gia đình
   - Khuyến khích tư duy tích cực, sáng tạo

CHÚ Ý QUAN TRỌNG:
- Giữ nguyên ý chính và thông điệp của câu chuyện gốc
- Độ dài câu chuyện nên tương đương hoặc dài hơn 20-30% so với bản gốc
- Đảm bảo câu chuyện phù hợp với trẻ em và gia đình
- Sử dụng tiếng Việt chuẩn, tránh từ ngữ khó hiểu
- Tạo ra nội dung gốc, tránh copy nguyên văn từ bản gốc
- **QUY TẮC DẤU NGOẶC KÉP THÔNG MINH:**
  * HỘI THOẠI (lời nói trực tiếp của nhân vật): Luôn có dấu ngoặc kép "..."
  * DẪN TRUYỆN (mô tả, tường thuật, hành động): Không có dấu ngoặc kép
  * TỰ ĐỘNG PHÂN LOẠI: Hãy tự nhận diện đâu là hội thoại, đâu là dẫn truyện
  * VÍ DỤ: Mẹ nói: "Con ơi, hôm nay thế nào?" (có ngoặc kép)
  * VÍ DỤ: Mẹ đi vào phòng với nụ cười ấm áp. (không có ngoặc kép)

Hãy viết lại câu chuyện hoàn chỉnh với tất cả các cải tiến trên. Chỉ trả về nội dung câu chuyện được viết lại, không thêm giải thích hay chú thích gì khác.
"""
        
        response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.8,
                    top_p=0.9
                )
            )

        return response.candidates[0].content.parts[0].text

    def _get_ai_analysis(self, prompt):
        """Get analysis from Gemini AI"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.9
                )
            )
            
            ai_text = response.candidates[0].content.parts[0].text
            
            # Parse JSON response
            try:
                # Remove markdown code blocks if present
                clean_text = ai_text.strip()
                if clean_text.startswith('```json'):
                    clean_text = clean_text[7:]
                if clean_text.endswith('```'):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()
                
                ai_analysis = json.loads(clean_text)
                return ai_analysis
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', clean_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    raise e
                    
        except Exception as e:
            logger.error(f"Error getting AI analysis: {str(e)}")
            raise e
    
