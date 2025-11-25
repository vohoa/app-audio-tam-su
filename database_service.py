"""
Database Service Layer for Audio Generator Desktop App
Sử dụng SQLite để lưu trữ dữ liệu local thay vì gọi API
"""
import sqlite3
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from logger_config import LoggerConfig
from config import get_default_language

# Initialize database logger
logger = LoggerConfig.get_logger('database')


class DatabaseService:
    def __init__(self, db_path: str = 'stories.db'):
        """Initialize database connection"""
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn

    def init_database(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Create stories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                author TEXT,
                category TEXT,
                cover_image TEXT,
                language TEXT DEFAULT 'vi',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Migration: Add language column if not exists (for existing databases)
        try:
            cursor.execute('ALTER TABLE stories ADD COLUMN language TEXT DEFAULT "vi"')
            logger.info("Added language column to stories table")
        except sqlite3.OperationalError:
            # Column already exists
            pass

        # Create chapters table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                story_id INTEGER NOT NULL,
                chapter_number INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                audio_file TEXT,
                audio_duration INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
            )
        ''')

        # Create indexes
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_chapters_story_id
            ON chapters(story_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_chapters_chapter_number
            ON chapters(story_id, chapter_number)
        ''')

        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")

    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """Convert Row object to dictionary"""
        if row is None:
            return None
        return dict(row)

    # ============================================
    # Story APIs
    # ============================================

    def get_stories(self) -> List[Dict]:
        """Get all stories"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT s.*, COUNT(c.id) as chapter_count
            FROM stories s
            LEFT JOIN chapters c ON s.id = c.story_id
            GROUP BY s.id
            ORDER BY s.created_at DESC
        ''')

        stories = [self._row_to_dict(row) for row in cursor.fetchall()]
        conn.close()

        # Format for compatibility with API response
        return stories

    def get_story(self, story_id: int) -> Dict:
        """Get story by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT s.*, COUNT(c.id) as chapter_count
            FROM stories s
            LEFT JOIN chapters c ON s.id = c.story_id
            WHERE s.id = ?
            GROUP BY s.id
        ''', (story_id,))

        row = cursor.fetchone()
        conn.close()

        if row is None:
            raise Exception(f"Story with ID {story_id} not found")

        return self._row_to_dict(row)

    def create_story(self, name: str, description: str = '', author: str = '',
                     category: str = '', cover_image: str = '', language: str = None) -> Dict:
        """Create a new story"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Use default language if not provided
        if language is None:
            language = get_default_language()

        cursor.execute('''
            INSERT INTO stories (name, description, author, category, cover_image, language)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, description, author, category, cover_image, language))

        story_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Created story: {name} (ID: {story_id}, Language: {language})")
        return self.get_story(story_id)

    def update_story(self, story_id: int, name: str = None, description: str = None,
                     author: str = None, category: str = None, cover_image: str = None,
                     language: str = None) -> Dict:
        """Update an existing story"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Build dynamic update query
        updates = []
        params = []

        if name is not None:
            updates.append('name = ?')
            params.append(name)
        if description is not None:
            updates.append('description = ?')
            params.append(description)
        if author is not None:
            updates.append('author = ?')
            params.append(author)
        if category is not None:
            updates.append('category = ?')
            params.append(category)
        if cover_image is not None:
            updates.append('cover_image = ?')
            params.append(cover_image)
        if language is not None:
            updates.append('language = ?')
            params.append(language)

        if not updates:
            conn.close()
            return self.get_story(story_id)

        updates.append('updated_at = CURRENT_TIMESTAMP')
        params.append(story_id)

        query = f"UPDATE stories SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
        conn.close()

        logger.info(f"Updated story ID: {story_id}")
        return self.get_story(story_id)

    def delete_story(self, story_id: int) -> Dict:
        """Delete a story and all its chapters"""
        # Get story info before deleting
        story = self.get_story(story_id)

        conn = self.get_connection()
        cursor = conn.cursor()

        # Delete all chapters first (cascade should handle this, but explicit is better)
        cursor.execute('DELETE FROM chapters WHERE story_id = ?', (story_id,))

        # Delete story
        cursor.execute('DELETE FROM stories WHERE id = ?', (story_id,))

        conn.commit()
        conn.close()

        logger.info(f"Deleted story ID: {story_id}")
        return {'success': True, 'message': f'Deleted story: {story["name"]}'}

    # ============================================
    # Chapter APIs
    # ============================================

    def get_chapters_by_story(self, story_id: int, page: int = 1, page_size: int = 50) -> Dict:
        """Get chapters for a story with pagination"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get total count
        cursor.execute('SELECT COUNT(*) as count FROM chapters WHERE story_id = ?', (story_id,))
        total_count = cursor.fetchone()['count']

        # Get paginated chapters
        offset = (page - 1) * page_size
        cursor.execute('''
            SELECT * FROM chapters
            WHERE story_id = ?
            ORDER BY chapter_number ASC
            LIMIT ? OFFSET ?
        ''', (story_id, page_size, offset))

        chapters = [self._row_to_dict(row) for row in cursor.fetchall()]
        conn.close()

        # Format for compatibility with API response
        return {
            'count': total_count,
            'results': chapters,
            'next': None,
            'previous': None
        }

    def get_chapter(self, chapter_id: int) -> Dict:
        """Get full chapter detail by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM chapters WHERE id = ?', (chapter_id,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            raise Exception(f"Chapter with ID {chapter_id} not found")

        return self._row_to_dict(row)

    def create_chapter(self, story_id: int, title: str, content: str,
                      chapter_number: int = None) -> Dict:
        """Create a new chapter"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Auto-generate chapter number if not provided
        if chapter_number is None:
            cursor.execute('''
                SELECT COALESCE(MAX(chapter_number), 0) + 1 as next_number
                FROM chapters WHERE story_id = ?
            ''', (story_id,))
            chapter_number = cursor.fetchone()['next_number']

        cursor.execute('''
            INSERT INTO chapters (story_id, chapter_number, title, content)
            VALUES (?, ?, ?, ?)
        ''', (story_id, chapter_number, title, content))

        chapter_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Created chapter: {title} (ID: {chapter_id})")
        return self.get_chapter(chapter_id)

    def update_chapter(self, chapter_id: int, title: str = None, content: str = None,
                      chapter_number: int = None) -> Dict:
        """Update an existing chapter"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Build dynamic update query
        updates = []
        params = []

        if title is not None:
            updates.append('title = ?')
            params.append(title)
        if content is not None:
            updates.append('content = ?')
            params.append(content)
        if chapter_number is not None:
            updates.append('chapter_number = ?')
            params.append(chapter_number)

        if not updates:
            conn.close()
            return self.get_chapter(chapter_id)

        updates.append('updated_at = CURRENT_TIMESTAMP')
        params.append(chapter_id)

        query = f"UPDATE chapters SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
        conn.close()

        logger.info(f"Updated chapter ID: {chapter_id}")
        return self.get_chapter(chapter_id)

    def delete_chapter(self, chapter_id: int) -> Dict:
        """Delete a chapter and its audio file if exists"""
        # Get chapter info before deleting
        chapter = self.get_chapter(chapter_id)

        # Delete physical audio file if exists
        if chapter.get('audio_file') and os.path.exists(chapter['audio_file']):
            try:
                os.remove(chapter['audio_file'])
                logger.info(f"Deleted audio file: {chapter['audio_file']}")
            except Exception as e:
                logger.warning(f"Failed to delete audio file: {e}")

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM chapters WHERE id = ?', (chapter_id,))
        conn.commit()
        conn.close()

        logger.info(f"Deleted chapter ID: {chapter_id}")
        return {'success': True, 'message': f'Deleted chapter: {chapter["title"]}'}

    # ============================================
    # Audio Management APIs
    # ============================================

    def upload_chapter_audio(self, chapter_id: int, audio_file_path: str) -> Dict:
        """Update chapter with audio file path"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE chapters
            SET audio_file = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (audio_file_path, chapter_id))

        conn.commit()
        conn.close()

        logger.info(f"Updated audio for chapter ID: {chapter_id}")
        return self.get_chapter(chapter_id)

    def delete_chapter_audio(self, chapter_id: int) -> Dict:
        """Remove audio file path from chapter"""
        chapter = self.get_chapter(chapter_id)

        # Delete physical file if exists
        if chapter.get('audio_file') and os.path.exists(chapter['audio_file']):
            try:
                os.remove(chapter['audio_file'])
                logger.info(f"Deleted audio file: {chapter['audio_file']}")
            except Exception as e:
                logger.warning(f"Failed to delete audio file: {e}")

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE chapters
            SET audio_file = NULL, audio_duration = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (chapter_id,))

        conn.commit()
        conn.close()

        logger.info(f"Removed audio from chapter ID: {chapter_id}")
        return {'success': True, 'message': 'Audio deleted successfully'}

    # ============================================
    # Authentication stub (for compatibility)
    # ============================================

    def is_authenticated(self) -> bool:
        """Always return True for local database"""
        return True

    def set_token(self, token: str, user_data: Optional[Dict] = None):
        """No-op for local database"""
        pass

    def clear_token(self):
        """No-op for local database"""
        pass
