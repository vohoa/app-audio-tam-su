"""
API Service Layer for Audio Generator Desktop App
CHỈ xử lý lấy dữ liệu truyện/chương và upload audio
KHÔNG xử lý Selenium (xử lý local)
"""
import requests
import os
from typing import Dict, List, Optional, Any
from config import API_BASE_URL, API_TIMEOUT
from logger_config import LoggerConfig

# Initialize API logger
logger = LoggerConfig.setup_module_logger('api', LoggerConfig.API_LOG_FILE)


class APIService:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.timeout = API_TIMEOUT
        self.token = None  # Authentication token
        self.user_data = None  # User information
        
    def _get_headers(self) -> Dict:
        """Get request headers with authentication"""
        headers = {}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """Make GET request to API"""
        url = f"{self.base_url}{endpoint}"
        try:
            headers = self._get_headers()
            response = requests.get(url, params=params, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"GET {url} | FAILED | {str(e)}", exc_info=True)
            raise Exception(f"API Error: {str(e)}")
    
    def _post(self, endpoint: str, data: Optional[Dict] = None, files: Optional[Dict] = None) -> Any:
        """Make POST request to API"""
        url = f"{self.base_url}{endpoint}"
        try:
            headers = self._get_headers()
            if files:
                response = requests.post(url, data=data, files=files, headers=headers, timeout=self.timeout)
            else:
                response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"POST {url} | FAILED | {str(e)}", exc_info=True)
            raise Exception(f"API Error: {str(e)}")
    
    def _delete(self, endpoint: str) -> Any:
        """Make DELETE request to API"""
        url = f"{self.base_url}{endpoint}"
        try:
            headers = self._get_headers()
            response = requests.delete(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"DELETE {url} | FAILED | {str(e)}", exc_info=True)
            raise Exception(f"API Error: {str(e)}")
    
    # ============================================
    # Authentication APIs
    # ============================================
    
    def login(self, username: str, password: str) -> Dict:
        """Login and get authentication token"""
        data = {
            'username': username,
            'password': password
        }
        try:
            # Try Django REST JWT token endpoint
            result = self._post('/token/', data=data)
            
            # Store token (could be 'token', 'access', or 'access_token')
            if 'token' in result:
                self.token = result['token']
            elif 'access' in result:
                self.token = result['access']
            elif 'access_token' in result:
                self.token = result['access_token']
            
            self.user_data = result
            return result
        except Exception as e:
            logger.error(f"Login failed for user {username}: {str(e)}")
            raise
    
    def set_token(self, token: str, user_data: Optional[Dict] = None):
        """Set authentication token manually"""
        self.token = token
        if user_data:
            self.user_data = user_data
    
    def clear_token(self):
        """Clear authentication token (logout)"""
        self.token = None
        self.user_data = None
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.token is not None
    
    # Story APIs
    def get_stories(self) -> List[Dict]:
        """Get all stories"""
        response = self._get('/stories/')
        return response.get('results', [])
    
    def get_story(self, story_id: int) -> Dict:
        """Get story by ID"""
        return self._get(f'/stories/{story_id}/')
    
    # Chapter APIs
    def get_chapters_by_story(self, story_id: int, page: int = 1, page_size: int = 50) -> Dict:
        """Get chapters for a story with pagination"""
        params = {
            'story': story_id,
            'page': page,
            'page_size': page_size
        }
        result = self._get('/chapters/', params=params)
        return result
    
    def get_chapter(self, chapter_id: int) -> Dict:
        """Get full chapter detail by ID"""
        return self._get(f'/chapters/{chapter_id}/')
    
    def create_chapter(self, story_id: int, title: str, content: str) -> Dict:
        """Create a new chapter"""
        data = {
            'story': story_id,
            'title': title,
            'content': content
        }
        return self._post('/chapters/', data=data)
    
    # Audio Management APIs (CHỈ upload/delete, KHÔNG generate)
    def upload_chapter_audio(self, chapter_id: int, audio_file_path: str) -> Dict:
        """Upload audio file for a chapter"""
        with open(audio_file_path, 'rb') as f:
            files = {'audio_file': f}
            result = self._post(f'/chapters/{chapter_id}/upload-audio/', files=files)
        return result
    
    def delete_chapter_audio(self, chapter_id: int) -> Dict:
        """Delete audio for a chapter"""
        return self._delete(f'/chapters/{chapter_id}/audio/')
    
    # ============================================
    # DEPRECATED METHODS (Old API-based architecture)
    # These methods are no longer supported.
    # Use selenium_audio_generator.py for local audio generation instead.
    # ============================================
    
    def convert_chapter_to_audio(self, chapter_id: int) -> Dict:
        """DEPRECATED: Use SeleniumAudioGenerator instead"""
        raise NotImplementedError(
            "API-based audio generation is no longer supported. "
            "Please use SeleniumAudioGenerator for local audio generation."
        )
    
    def generate_audio_with_selenium(self, chapter_id: int) -> Dict:
        """DEPRECATED: Use SeleniumAudioGenerator instead"""
        raise NotImplementedError(
            "API-based Selenium generation is no longer supported. "
            "Please use SeleniumAudioGenerator for local audio generation."
        )
    
    def get_task_status(self, task_id: str) -> Dict:
        """DEPRECATED: No longer needed with local generation"""
        raise NotImplementedError(
            "Task polling is no longer supported. "
            "Local Selenium generation completes synchronously."
        )
