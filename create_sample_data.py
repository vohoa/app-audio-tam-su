"""
Create sample stories and chapters for testing
"""
from database_service import DatabaseService


def create_sample_data():
    """Create sample stories and chapters"""
    db = DatabaseService()

    print("📚 Creating sample data...")

    # Sample Story 1: Cổ tích Việt Nam
    story1 = db.create_story(
        name="Sự Tích Cây Tre Trăm Đốt",
        author="Truyện cổ tích Việt Nam",
        category="Cổ tích",
        description="Câu chuyện về cây tre trăm đốt và tình yêu son sắt của hai vợ chồng."
    )
    print(f"✅ Created story: {story1['name']}")

    # Chapters for Story 1
    chapters1 = [
        {
            "title": "Chương 1: Ngày xửa ngày xưa",
            "content": """Ngày xửa ngày xưa, có một ông vua rất thương dân. Một hôm, khi đi vi hành, ông gặp một cặp vợ chồng trẻ sống hạnh phúc bên nhau.

Ông vua rất ấn tượng với tình cảm son sắt của họ và muốn thử lòng hai người."""
        },
        {
            "title": "Chương 2: Lời thách thức",
            "content": """Vua nói với người vợ: 'Ta muốn thử lòng hai người. Nếu người chồng của ngươi phải đi xa một trăm năm, ngươi có chờ được không?'

Người vợ kiên quyết: 'Tôi xin hứa sẽ chờ chồng tôi, dù có lâu đến mấy!'"""
        },
        {
            "title": "Chương 3: Thử thách",
            "content": """Vua bắt người chồng đi xa một trăm năm. Người vợ hàng ngày đứng chờ chồng, ngày qua ngày, năm qua năm.

Bà già đi, tóc bạc phơ nhưng vẫn kiên trì đứng chờ."""
        },
        {
            "title": "Chương 4: Phép màu",
            "content": """Cảm động trước tình yêu son sắt ấy, trời đất ban phép màu biến người vợ thành cây tre với một trăm đốt, mỗi đốt tượng trưng cho một năm chờ đợi.

Khi người chồng trở về, anh đã tìm thấy cây tre và nhận ra đó chính là vợ mình."""
        }
    ]

    for i, chapter_data in enumerate(chapters1, 1):
        db.create_chapter(
            story_id=story1['id'],
            title=chapter_data['title'],
            content=chapter_data['content'],
            chapter_number=i
        )
    print(f"  Added {len(chapters1)} chapters")

    # Sample Story 2: Truyện cười
    story2 = db.create_story(
        name="Truyện Cười Dân Gian",
        author="Truyện dân gian",
        category="Truyện cười",
        description="Những câu chuyện cười vui nhộn về trí khôn của người Việt Nam."
    )
    print(f"✅ Created story: {story2['name']}")

    # Chapters for Story 2
    chapters2 = [
        {
            "title": "Chuyện 1: Cái bánh đa",
            "content": """Có một ông vua tham ăn, nghe nói bánh đa rất ngon nên sai người đi mua.

Nhưng ông lại bảo: 'Hãy mua loại có nhiều lỗ nhất, vì như vậy sẽ được nhiều bánh hơn!'

Người hầu cười và nói: 'Thưa bệ hạ, lỗ nhiều thì bánh ít chứ ạ!'"""
        },
        {
            "title": "Chuyện 2: Trộm vịt",
            "content": """Một người đi trộm vịt, bị chủ nhà bắt quả tang.

Người trộm vội nói: 'Tôi không trộm đâu, tôi chỉ đang dạy con vịt của ông bơi thôi!'

Chủ nhà hỏi: 'Vậy tại sao ngươi lại nhét nó vào bao?'

'Dạ, vịt nó học xong rồi, tôi đang đưa về nhà để làm bài tập ạ!'"""
        }
    ]

    for i, chapter_data in enumerate(chapters2, 1):
        db.create_chapter(
            story_id=story2['id'],
            title=chapter_data['title'],
            content=chapter_data['content'],
            chapter_number=i
        )
    print(f"  Added {len(chapters2)} chapters")

    # Sample Story 3: Khoa học
    story3 = db.create_story(
        name="Khám Phá Vũ Trụ",
        author="Nguyễn Văn A",
        category="Khoa học",
        description="Những kiến thức thú vị về vũ trụ dành cho thiếu nhi."
    )
    print(f"✅ Created story: {story3['name']}")

    # Chapters for Story 3
    chapters3 = [
        {
            "title": "Bài 1: Mặt trời là gì?",
            "content": """Mặt trời là một ngôi sao rất lớn ở trung tâm hệ mặt trời của chúng ta.

Nó lớn hơn Trái Đất rất nhiều lần và cung cấp ánh sáng cũng như nhiệt lượng cho sự sống trên Trái Đất.

Mặt trời được tạo thành từ các chất khí nóng chảy và có nhiệt độ rất cao."""
        },
        {
            "title": "Bài 2: Các hành tinh",
            "content": """Hệ mặt trời có tám hành tinh quay xung quanh mặt trời.

Gần mặt trời nhất là Sao Thủy, sau đó là Sao Kim, Trái Đất, Sao Hỏa, Sao Mộc, Sao Thổ, Sao Thiên Vương và Sao Hải Vương.

Mỗi hành tinh có đặc điểm riêng và khoảng cách khác nhau so với mặt trời."""
        }
    ]

    for i, chapter_data in enumerate(chapters3, 1):
        db.create_chapter(
            story_id=story3['id'],
            title=chapter_data['title'],
            content=chapter_data['content'],
            chapter_number=i
        )
    print(f"  Added {len(chapters3)} chapters")

    print("\n" + "="*60)
    print("✅ Sample data created successfully!")
    print("="*60)
    print(f"📚 Stories: 3")
    print(f"📖 Chapters: {len(chapters1) + len(chapters2) + len(chapters3)}")
    print(f"📁 Database: stories.db")
    print("\nYou can now run the app and see the sample data:")
    print("  python main.py")


if __name__ == '__main__':
    create_sample_data()
