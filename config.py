"""
Configuration file for Audio Generator Desktop App
"""
import os
from typing import Dict
from decouple import config

# API Configuration (CHỈ để lấy dữ liệu truyện/chương)
API_BASE_URL = config('API_BASE_URL', default='http://localhost:8000/api')
API_TIMEOUT = config('API_TIMEOUT', default=30, cast=int)

# Pagination
CHAPTERS_PER_PAGE = config('CHAPTERS_PER_PAGE', default=50, cast=int)

# UI Configuration
WINDOW_WIDTH = config('WINDOW_WIDTH', default=1400, cast=int)
WINDOW_HEIGHT = config('WINDOW_HEIGHT', default=900, cast=int)

# ============================================
# SELENIUM AUDIO GENERATION (LOCAL)
# ============================================

# Chrome/ChromeDriver paths (mặc định sử dụng Brave Browser)
CHROME_BINARY_PATH = config('CHROME_BINARY_PATH', default='/usr/bin/brave-browser')
CHROMEDRIVER_PATH = config('CHROMEDRIVER_PATH', default=None)

# Audio download path
# NOTE: Force use .env file value, ignore system environment variable
# to ensure we use the correct project directory
from decouple import RepositoryEnv
_project_dir = os.path.dirname(__file__)
_env_file = os.path.join(_project_dir, '.env')

# Read directly from .env file to override system environment variable
if os.path.exists(_env_file):
    try:
        _repo = RepositoryEnv(_env_file)
        _audio_path = _repo['AUDIO_DOWNLOAD_PATH'] if 'AUDIO_DOWNLOAD_PATH' in _repo.data else ''
        if _audio_path:
            AUDIO_DOWNLOAD_PATH = _audio_path
        else:
            # Use default project directory
            AUDIO_DOWNLOAD_PATH = os.path.join(_project_dir, 'audio_downloads')
    except Exception as e:
        # Fallback to default
        AUDIO_DOWNLOAD_PATH = os.path.join(_project_dir, 'audio_downloads')
else:
    # Fallback to original logic
    AUDIO_DOWNLOAD_PATH = config(
        'AUDIO_DOWNLOAD_PATH',
        default=os.path.join(_project_dir, 'audio_downloads')
    )

# Selenium settings
SELENIUM_HEADLESS = config('SELENIUM_HEADLESS', default=False, cast=bool)
SELENIUM_DEBUGGING_PORT = config('SELENIUM_DEBUGGING_PORT', default=9222, cast=int)

# Gemini API Key
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')

# Conversation JSON URL (for AI-generated conversations)
CONVERSATION_JSON_URL = config('CONVERSATION_JSON_URL', default='')

# ============================================
# GROK AI CONFIGURATION
# ============================================

# Grok AI URL
GROK_AI_URL = config('GROK_AI_URL', default='https://grok.com/')

# Grok AI Profile
GROK_AI_PROFILE = config('GROK_AI_PROFILE', default='grok_ai')

# Conversations directory
CONVERSATIONS_DIR = config(
    'CONVERSATIONS_DIR',
    default=os.path.join(os.path.dirname(__file__), 'conversations')
)

# Grok AI timeouts
GROK_RESPONSE_TIMEOUT = config('GROK_RESPONSE_TIMEOUT', default=60, cast=int)
GROK_PROMPT_DELAY = config('GROK_PROMPT_DELAY', default=0.05, cast=float)

# Grok AI headless mode
GROK_HEADLESS = config('GROK_HEADLESS', default=False, cast=bool)


# ============================================
# PERPLEXITY AI CONFIGURATION
# ============================================

# Perplexity AI URL
PERPLEXITY_AI_URL = config('PERPLEXITY_AI_URL', default='https://www.perplexity.ai/')

# Perplexity AI Profile
PERPLEXITY_AI_PROFILE = config('PERPLEXITY_AI_PROFILE', default='perplexity_ai')

# Perplexity Conversation JSON URL (optional)
PERPLEXITY_CONVERSATION_JSON_URL = config('PERPLEXITY_CONVERSATION_JSON_URL', default='')
PERPLEXITY_PROMPT_JSON_URL= config('PERPLEXITY_PROMPT_JSON_URL', default ='')
# Perplexity AI timeouts
PERPLEXITY_RESPONSE_TIMEOUT = config('PERPLEXITY_RESPONSE_TIMEOUT', default=60, cast=int)
PERPLEXITY_PROMPT_DELAY = config('PERPLEXITY_PROMPT_DELAY', default=0.05, cast=float)

# Perplexity AI headless mode
PERPLEXITY_HEADLESS = config('PERPLEXITY_HEADLESS', default=False, cast=bool)


# ============================================
# RUNWARE API CONFIGURATION
# ============================================

# Runware API Key
RUNWARE_API_KEY = config('RUNWARE_API_KEY', default='')

# Runware Image Settings
RUNWARE_DEFAULT_MODEL = config('RUNWARE_DEFAULT_MODEL', default='runware:101@1')
RUNWARE_DEFAULT_WIDTH = config('RUNWARE_DEFAULT_WIDTH', default=1024, cast=int)
RUNWARE_DEFAULT_HEIGHT = config('RUNWARE_DEFAULT_HEIGHT', default=1024, cast=int)

# Generated images directory
GENERATED_IMAGES_DIR = config(
    'GENERATED_IMAGES_DIR',
    default=os.path.join(os.path.dirname(__file__), 'generated_images')
)

# Generated videos directory
GENERATED_VIDEOS_DIR = config(
    'GENERATED_VIDEOS_DIR',
    default=os.path.join(os.path.dirname(__file__), 'generated_videos')
)

# Video settings
VIDEO_FPS = config('VIDEO_FPS', default=1, cast=int)  # 1 frame per second (mỗi ảnh hiển thị 1 giây)
VIDEO_TRANSITION_DURATION = config('VIDEO_TRANSITION_DURATION', default=0.5, cast=float)  # Thời gian chuyển cảnh


# ============================================
# Helper functions for dynamic config updates
# ============================================

def get_gemini_api_key() -> str:
    """Get current Gemini API Key from environment or .env file"""
    return config('GEMINI_API_KEY', default='')


def get_audio_download_path() -> str:
    """Get current audio download path from environment or .env file"""
    return config(
        'AUDIO_DOWNLOAD_PATH', 
        default=os.path.join(os.path.dirname(__file__), 'audio_downloads')
    )


def get_conversation_json_url() -> str:
    """Get current conversation JSON URL from environment or .env file"""
    return config('CONVERSATION_JSON_URL', default='')


def get_conversations_dir() -> str:
    """Get conversations directory path"""
    return config(
        'CONVERSATIONS_DIR',
        default=os.path.join(os.path.dirname(__file__), 'conversations')
    )


def get_grok_ai_url() -> str:
    """Get Grok AI URL"""
    return config('GROK_AI_URL', default='https://grok.com/')


def get_grok_ai_profile() -> str:
    """Get Grok AI profile name"""
    return config('GROK_AI_PROFILE', default='grok_ai')


def get_grok_response_timeout() -> int:
    """Get Grok AI response timeout in seconds"""
    return config('GROK_RESPONSE_TIMEOUT', default=60, cast=int)


def get_perplexity_ai_url() -> str:
    """Get Perplexity AI URL"""
    return config('PERPLEXITY_AI_URL', default='https://www.perplexity.ai/')


def get_perplexity_ai_profile() -> str:
    """Get Perplexity AI profile name"""
    return config('PERPLEXITY_AI_PROFILE', default='perplexity_ai')


def get_perplexity_conversation_json_url() -> str:
    """Get Perplexity conversation JSON URL"""
    return config('PERPLEXITY_CONVERSATION_JSON_URL', default='')


def get_perplexity_response_timeout() -> int:
    """Get Perplexity AI response timeout in seconds"""
    return config('PERPLEXITY_RESPONSE_TIMEOUT', default=60, cast=int)


def get_chrome_binary_path() -> str:
    """
    Get Chrome binary path from config, or auto-detect if not configured
    
    Priority:
    1. User config from .env (CHROME_BINARY_PATH) - Mặc định: /usr/bin/brave-browser
    2. Brave Browser (/usr/bin/brave-browser) - KHÔNG dùng Chrome mặc định của hệ thống
    3. Chrome-for-Testing in project (chrome-linux64/chrome) - nếu có
    4. Return empty string if not found
    
    Returns:
        str: Path to Chrome binary, or empty string if not found
    """
    # Check user config first (default is Brave Browser)
    configured_path = config('CHROME_BINARY_PATH', default='/usr/bin/brave-browser')
    if configured_path and os.path.exists(configured_path):
        return configured_path
    
    # Ưu tiên Brave Browser - KHÔNG dùng Chrome mặc định
    if os.path.exists('/usr/bin/brave-browser'):
        return '/usr/bin/brave-browser'
    
    # Fallback: Chrome-for-Testing (project local) nếu Brave không có
    project_dir = os.path.dirname(os.path.abspath(__file__))
    chrome_for_testing = os.path.join(project_dir, 'chrome-linux64', 'chrome')
    if os.path.exists(chrome_for_testing):
        return chrome_for_testing
    
    # Không tự động detect system Chrome nữa, chỉ trả về empty string
    return ''


def get_chrome_driver_path() -> str:
    """
    Get ChromeDriver path from config, or auto-detect if not configured
    
    Priority:
    1. User config from .env (CHROME_DRIVER_PATH)
    2. ChromeDriver in project (chrome_driver/chromedriver)
    3. Return None to let undetected_chromedriver manage automatically
    
    Returns:
        str: Path to ChromeDriver, or empty string for auto-management
    """
    # Check user config first
    configured_path = config('CHROME_DRIVER_PATH', default='')
    if configured_path and os.path.exists(configured_path):
        return configured_path
    
    # Auto-detect project ChromeDriver
    project_dir = os.path.dirname(os.path.abspath(__file__))
    project_chromedriver = os.path.join(project_dir, 'chrome_driver', 'chromedriver')
    if os.path.exists(project_chromedriver):
        return project_chromedriver
    
    # Return empty string to let undetected_chromedriver auto-manage
    return ''


def get_chrome_version(chrome_binary_path: str = None) -> str:
    """
    Get Chrome version from binary
    
    Args:
        chrome_binary_path: Path to Chrome binary (optional, will auto-detect if None)
    
    Returns:
        str: Version string (e.g., "140.0.7339.207") or "Unknown"
    """
    import subprocess
    
    if not chrome_binary_path:
        chrome_binary_path = get_chrome_binary_path()
    
    if not chrome_binary_path or not os.path.exists(chrome_binary_path):
        return "Unknown"
    
    try:
        result = subprocess.run(
            [chrome_binary_path, '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Output: "Google Chrome 140.0.7339.207" or "Chromium 140.0.7339.207"
        version_output = result.stdout.strip()
        # Extract version number
        parts = version_output.split()
        if len(parts) >= 3:
            return parts[-1]  # Last part is version
        return version_output
    except Exception as e:
        return f"Error: {str(e)}"


def kill_browser_instances(chrome_binary_path: str = None, verbose: bool = True) -> Dict[str, bool]:
    """
    Kill all browser instances and related processes based on configured browser
    Ensures clean startup by removing zombie processes and locks
    
    TỰ ĐỘNG XÁC ĐỊNH: Dựa vào CHROME_BINARY_PATH để kill đúng browser
    - Nếu path chứa "brave" → kill Brave Browser
    - Nếu path chứa "chrome/chromium" → kill Chrome/Chromium
    - Mặc định: dùng config từ .env (hiện tại: /usr/bin/brave-browser)
    
    Args:
        chrome_binary_path: Path to browser binary (optional, sẽ lấy từ config nếu None)
        verbose: Print status messages
    
    Returns:
        Dict with status of each cleanup operation:
        {
            'zombie_chromedrivers': bool,
            'chromedrivers': bool,
            'browsers': bool,
            'profile_locks': bool
        }
    """
    import subprocess
    import signal
    
    results = {
        'zombie_chromedrivers': False,
        'chromedrivers': False,
        'browsers': False,
        'profile_locks': False
    }
    
    # Lấy browser path từ config nếu không được cung cấp
    if not chrome_binary_path:
        chrome_binary_path = get_chrome_binary_path()
    
    # TỰ ĐỘNG xác định browser type dựa vào đường dẫn thực tế
    browser_name = "browser"
    browser_process_names = []
    
    if chrome_binary_path:
        path_lower = chrome_binary_path.lower()
        
        if "brave" in path_lower:
            # Brave Browser
            browser_name = "Brave Browser"
            browser_process_names = ["brave", "brave-browser", "BraveBrowser"]
        elif "chromium" in path_lower:
            # Chromium
            browser_name = "Chromium"
            browser_process_names = ["chromium", "chromium-browser"]
        elif "chrome-linux64" in path_lower or "chrome-for-testing" in path_lower:
            # Chrome-for-Testing (downloaded version trong project)
            # Process name là "chrome" nhưng KHÔNG kill system Chrome
            browser_name = "Chrome-for-Testing"
            browser_process_names = ["chrome"]  # Chỉ kill "chrome", không kill "google-chrome"
            if verbose:
                print(f"   ℹ️  Using Chrome-for-Testing from: {chrome_binary_path}")
                print(f"   ℹ️  Will only kill 'chrome' processes (not system Chrome)")
        elif "chrome" in path_lower:
            # Google Chrome (system)
            browser_name = "Chrome"
            browser_process_names = ["chrome", "google-chrome", "google-chrome-stable"]
        else:
            # Fallback: cố gắng extract tên từ path
            browser_name = os.path.basename(chrome_binary_path)
            browser_process_names = [browser_name]
            if verbose:
                print(f"   ℹ️  Unknown browser type, will try to kill: {browser_name}")
    else:
        # Không có browser path, cảnh báo
        if verbose:
            print("⚠️  No browser binary path found, skipping browser cleanup")
        return results
    
    if verbose:
        print(f"🧹 Killing all {browser_name} instances and related processes...")
    
    # 1. Kill zombie chromedrivers
    try:
        result = subprocess.run(
            ['pkill', '-9', '-f', 'chromedriver.*defunct'],
            capture_output=True,
            timeout=5
        )
        results['zombie_chromedrivers'] = result.returncode == 0
        if verbose and results['zombie_chromedrivers']:
            print("   ✅ Killed zombie chromedrivers")
    except Exception as e:
        if verbose:
            print(f"   ⚠️  Could not kill zombie chromedrivers: {e}")
    
    # 2. Kill all chromedrivers
    try:
        result = subprocess.run(
            ['pkill', '-9', 'chromedriver'],
            capture_output=True,
            timeout=5
        )
        results['chromedrivers'] = result.returncode == 0
        if verbose and results['chromedrivers']:
            print("   ✅ Killed all chromedrivers")
    except Exception as e:
        if verbose:
            print(f"   ℹ️  No chromedrivers running")
    
    # 3. Kill all browser processes (Chrome or Brave)
    killed_any = False
    for process_name in browser_process_names:
        try:
            result = subprocess.run(
                ['pkill', '-9', process_name],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                killed_any = True
                if verbose:
                    print(f"   ✅ Killed {process_name} processes")
        except Exception as e:
            pass  # Continue to next process name
    
    results['browsers'] = killed_any
    if verbose and not killed_any:
        print(f"   ℹ️  No {browser_name} processes running")
    
    # 4. Remove profile locks
    try:
        project_dir = os.path.dirname(os.path.abspath(__file__))
        profile_dir = os.path.join(project_dir, 'chrome_profiles')
        
        if os.path.exists(profile_dir):
            lock_files_removed = 0
            
            # Find and remove lock files
            for root, dirs, files in os.walk(profile_dir):
                for filename in files:
                    if filename in ['SingletonLock', 'SingletonSocket', 'SingletonCookie']:
                        lock_file = os.path.join(root, filename)
                        try:
                            os.remove(lock_file)
                            lock_files_removed += 1
                        except Exception:
                            pass
            
            results['profile_locks'] = lock_files_removed > 0
            if verbose and lock_files_removed > 0:
                print(f"   ✅ Removed {lock_files_removed} profile lock files")
            elif verbose:
                print("   ℹ️  No profile locks found")
        else:
            if verbose:
                print("   ℹ️  Profile directory not found")
    except Exception as e:
        if verbose:
            print(f"   ⚠️  Could not remove profile locks: {e}")
    
    # Wait for cleanup to complete
    import time
    time.sleep(1)
    
    if verbose:
        print("✨ Browser cleanup complete!")
    
    return results
