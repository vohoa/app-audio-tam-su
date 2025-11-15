"""
Script to import data from API to local database
Run this if you want to migrate data from the old API-based system
"""
from api_service import APIService
from database_service import DatabaseService
import sys


def import_data(api_url: str, username: str, password: str):
    """Import stories and chapters from API to local database"""

    print("🔄 Starting data import from API to local database...")
    print(f"API URL: {api_url}")
    print(f"Username: {username}")

    # Initialize services
    api = APIService(base_url=api_url)
    db = DatabaseService()

    try:
        # Login to API
        print("\n🔐 Logging in to API...")
        api.login(username, password)
        print("✅ Login successful!")

        # Get all stories from API
        print("\n📚 Fetching stories from API...")
        stories = api.get_stories()
        print(f"Found {len(stories)} stories")

        # Import each story
        story_mapping = {}  # Map old story ID to new story ID
        total_chapters = 0

        for i, story in enumerate(stories, 1):
            print(f"\n[{i}/{len(stories)}] Importing story: {story['name']}")

            # Create story in database
            try:
                db_story = db.create_story(
                    name=story['name'],
                    description=story.get('description', ''),
                    author=story.get('author', ''),
                    category=story.get('category', ''),
                    cover_image=story.get('cover_image', '')
                )
                story_mapping[story['id']] = db_story['id']
                print(f"  ✅ Story created (ID: {db_story['id']})")

                # Get chapters for this story
                print(f"  📖 Fetching chapters...")
                chapters_result = api.get_chapters_by_story(story['id'], page=1, page_size=1000)
                chapters = chapters_result.get('results', [])
                print(f"  Found {len(chapters)} chapters")

                # Import each chapter
                chapter_count = 0
                for chapter in chapters:
                    try:
                        # Get full chapter data if needed
                        if 'content' not in chapter or not chapter['content']:
                            full_chapter = api.get_chapter(chapter['id'])
                            chapter = full_chapter

                        db_chapter = db.create_chapter(
                            story_id=db_story['id'],
                            title=chapter['title'],
                            content=chapter.get('content', ''),
                            chapter_number=chapter.get('chapter_number')
                        )

                        # If chapter has audio_file, update it
                        if chapter.get('audio_file'):
                            db.upload_chapter_audio(
                                chapter_id=db_chapter['id'],
                                audio_file_path=chapter['audio_file']
                            )

                        chapter_count += 1
                        total_chapters += 1

                    except Exception as e:
                        print(f"    ⚠️ Failed to import chapter '{chapter.get('title', 'Unknown')}': {e}")
                        continue

                print(f"  ✅ Imported {chapter_count}/{len(chapters)} chapters")

            except Exception as e:
                print(f"  ❌ Failed to import story '{story['name']}': {e}")
                continue

        # Summary
        print("\n" + "="*60)
        print("📊 IMPORT SUMMARY")
        print("="*60)
        print(f"✅ Stories imported: {len(story_mapping)}/{len(stories)}")
        print(f"✅ Chapters imported: {total_chapters}")
        print(f"📁 Database file: stories.db")
        print("\n🎉 Import completed successfully!")

    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    # Configuration
    API_URL = input("Enter API URL (e.g., http://localhost:8000/api): ").strip()
    USERNAME = input("Enter username: ").strip()
    PASSWORD = input("Enter password: ").strip()

    if not API_URL or not USERNAME or not PASSWORD:
        print("❌ All fields are required!")
        sys.exit(1)

    # Confirm before import
    print("\n⚠️  WARNING: This will import all data from API to local database.")
    print("If data already exists in database, duplicates may be created.")
    confirm = input("Continue? (yes/no): ").strip().lower()

    if confirm != 'yes':
        print("❌ Import cancelled")
        sys.exit(0)

    # Run import
    import_data(API_URL, USERNAME, PASSWORD)
