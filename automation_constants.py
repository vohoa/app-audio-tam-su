"""
Constants for Google AI Studio Automation
Centralized configuration values for selectors, timeouts, and delays
"""

# ============================================
# URLS
# ============================================
BASE_URL = "https://aistudio.google.com/generate-speech"
MAKERSUITE_URL = "https://makersuite.google.com/app/prompts/new_freeform"

# ============================================
# TIMEOUTS (seconds)
# ============================================
class Timeouts:
    """Timeout values for various operations"""
    AUTH = 300  # 5 minutes for authentication
    PAGE_LOAD = 30  # Page loading
    AUDIO_GENERATION_BASE = 1800  # 30 minutes base timeout
    ELEMENT_WAIT = 10  # Standard element wait
    DOWNLOAD_WAIT = 30  # Audio download wait
    SESSION_RECOVERY = 60  # Session recovery
    VOICE_SELECTION = 15  # Voice dropdown selection


# ============================================
# DELAYS (seconds) - Human-like behavior
# ============================================
class Delays:
    """Delay ranges for human-like interactions"""
    # Standard delays
    HUMAN_MIN = 0.5
    HUMAN_MAX = 2.0

    # Typing delays (per character)
    TYPING_MIN = 0.08  # 80ms per character
    TYPING_MAX = 0.12  # 120ms per character

    # Punctuation delays (longer pauses)
    PUNCTUATION_MIN = 0.15  # 150ms
    PUNCTUATION_MAX = 0.30  # 300ms

    # Click delays
    CLICK_MIN = 0.2
    CLICK_MAX = 0.5

    # Scroll delays
    SCROLL_MIN = 0.3
    SCROLL_MAX = 0.6

    # Post-paste delays
    PASTE_MIN = 0.2
    PASTE_MAX = 0.4

    # Element interaction delays
    ELEMENT_MIN = 0.1
    ELEMENT_MAX = 0.3


# ============================================
# CSS SELECTORS
# ============================================
class Selectors:
    """CSS selectors for web elements"""

    # Authentication
    LOGIN_INDICATORS = [
        "[data-testid*='avatar']",
        "[aria-label*='Account']",
        ".profile-button",
        "[data-testid*='profile']",
    ]

    TEXT_INPUT_INDICATORS = [
        "textarea",
        "[contenteditable='true']",
        "[role='textbox']"
    ]

    SIGNIN_INDICATORS = [
        "input[type='email']",
        "input[type='password']",
        "[data-testid*='signin']",
        "[data-testid*='login']",
    ]

    # Voice selection
    VOICE_BUTTON = "button[aria-label*='voice']"
    VOICE_DROPDOWN = ".voice-selector"
    VOICE_OPTION = ".voice-option"

    # Text input
    TEXT_INPUT = "textarea[placeholder*='text']"
    TEXT_AREA = "textarea"
    CONTENTEDITABLE = "[contenteditable='true']"

    # Generation
    GENERATE_BUTTON = "button[aria-label*='Generate']"
    AUDIO_PLAYER = "audio"
    AUDIO_SOURCE = "audio source"

    # Loading indicators
    LOADING_SPINNER = ".loading-spinner"
    PROGRESS_BAR = ".progress-bar"

    # Error messages
    ERROR_MESSAGE = ".error-message"
    AUTH_ERROR = "[data-testid*='auth-error']"


# ============================================
# AUDIO SETTINGS
# ============================================
class Audio:
    """Audio generation and download settings"""
    DEFAULT_VOICE = "vi-VN-Neural2-A"
    SUPPORTED_FORMATS = ['.mp3', '.wav', '.m4a', '.ogg']
    MIN_FILE_SIZE = 1024  # 1KB minimum

    # Generation time estimation
    CHARS_PER_SECOND = 15  # ~15 characters per second of audio
    BASE_GENERATION_TIME = 10  # 10 seconds base generation time
    SAFETY_MULTIPLIER = 2.5  # Safety factor for timeout


# ============================================
# CHROME SETTINGS
# ============================================
class Chrome:
    """Chrome browser configuration"""
    DEFAULT_WINDOW_SIZE = "--start-maximized"
    HEADLESS_NEW = "--headless=new"

    # Anti-detection arguments
    STEALTH_ARGS = [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-blink-features=AutomationControlled',
    ]

    # Experimental options
    EXCLUDE_SWITCHES = ["enable-automation"]
    DISABLE_AUTOMATION_EXTENSION = False


# ============================================
# ERROR MESSAGES
# ============================================
class ErrorMessages:
    """Standard error messages"""
    SESSION_INVALID = "Session invalid or expired"
    AUTH_REQUIRED = "Authentication required"
    ELEMENT_NOT_FOUND = "Required element not found"
    TIMEOUT = "Operation timed out"
    DOWNLOAD_FAILED = "Audio download failed"
    GENERATION_FAILED = "Audio generation failed"


# ============================================
# CHARACTERS FOR SPECIAL HANDLING
# ============================================
PUNCTUATION_CHARS = ' .,!?;:\n\t'
ESCAPE_CHARS = ['\\', '"', '\n', '\r']


# ============================================
# RETRY SETTINGS
# ============================================
class Retry:
    """Retry configuration for various operations"""
    MAX_ATTEMPTS = 3
    BACKOFF_FACTOR = 2  # Exponential backoff
    INITIAL_DELAY = 1  # seconds
