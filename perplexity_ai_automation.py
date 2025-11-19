"""
Perplexity AI Automation using Selenium
Tự động hóa việc tạo hội thoại và lấy JSON từ https://www.perplexity.ai
"""

import os
import time
import json
import logging
import pyperclip
from typing import Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import undetected_chromedriver as uc

# Import config
import config

# Import browser fingerprint
from browser_fingerprint import ProfileFingerprintManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerplexityAIAutomation:
    """
    Automation class để tương tác với Perplexity AI
    Nhập prompt để tạo hội thoại, sau đó copy JSON response
    """

    def __init__(self, headless: bool = None, use_profile: bool = True, 
                 profile_name: str = None, system_profile_path: str = None):
        """
        Khởi tạo Perplexity AI automation instance
        
        Args:
            headless: Chạy browser ở chế độ headless hay không (None = dùng config)
            use_profile: Có sử dụng browser profile để lưu session không
            profile_name: Tên profile để lưu (None = dùng config)
            system_profile_path: Đường dẫn đến profile directory (None = dùng config)
        """
        
        # Get configuration from config.py
        self.headless = headless if headless is not None else config.PERPLEXITY_HEADLESS
        profile_name = profile_name or config.PERPLEXITY_AI_PROFILE
        
        print("⚙️ Initializing Perplexity AI Automation")
        print(f"📁 Profile: {profile_name}")
        print(f"👁️ Headless: {'Yes' if self.headless else 'No (UI visible)'}")
        
        self.driver = None
        self.wait = None
        self._session_invalid = False
        self.fingerprint_config = None  # Will be loaded in start_browser()
        
        # Profile setup
        self.use_profile = use_profile
        self.profile_name = profile_name
        
        # Use config for chrome_profiles path
        if system_profile_path:
            self.system_profile_path = system_profile_path
        else:
            project_root = os.path.dirname(os.path.abspath(__file__))
            self.system_profile_path = os.path.join(project_root, 'chrome_profiles')
        
        self.profile_path = self._get_profile_path() if use_profile else None
        
        # Perplexity URL from config
        self.base_url = config.PERPLEXITY_AI_URL
        
        # Chrome binary và ChromeDriver paths từ config
        self.chrome_binary_path = config.get_chrome_binary_path()
        self.chromedriver_path = config.get_chrome_driver_path()
        
        logger.info(f"Chrome binary: {self.chrome_binary_path}")
        logger.info(f"ChromeDriver: {self.chromedriver_path}")
        logger.info(f"Profile path: {self.profile_path}")
        logger.info(f"Perplexity URL: {self.base_url}")
        
        # 🔥 Kill all existing browser instances before starting
        logger.info("🧹 Killing all existing browser instances...")
        config.kill_browser_instances(self.chrome_binary_path, verbose=True)
        
        # 🛡️ Browser Fingerprint Manager
        project_root = os.path.dirname(os.path.abspath(__file__))
        self.fingerprint_manager = ProfileFingerprintManager(
            profiles_dir=self.system_profile_path,
            configs_dir=os.path.join(project_root, 'profile_configs')
        )
        logger.info("🛡️ Fingerprint Manager initialized")

    def _get_profile_path(self) -> str:
        """Tạo đường dẫn profile directory"""
        if not self.use_profile:
            return None
            
        profile_dir = os.path.join(self.system_profile_path, self.profile_name)
        os.makedirs(profile_dir, exist_ok=True)
        logger.info(f"Profile directory: {profile_dir}")
        return profile_dir

    def _get_project_root(self) -> str:
        """Lấy đường dẫn gốc của project"""
        current_file = os.path.abspath(__file__)
        return os.path.dirname(current_file)

    def _create_chrome_options(self) -> Options:
        """Tạo Chrome options với các settings cần thiết"""
        options = uc.ChromeOptions()
        
        # Basic options
        if self.headless:
            options.add_argument('--headless=new')
        
        # Common options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # User agent
        options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Window size
        options.add_argument('--window-size=1920,1080')
        
        # Profile
        if self.profile_path:
            options.add_argument(f'--user-data-dir={self.profile_path}')
            logger.info(f"Using profile: {self.profile_path}")
        
        # Prefs (these work with undetected_chromedriver)
        prefs = {
            'profile.default_content_setting_values.notifications': 2,
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False
        }
        options.add_experimental_option('prefs', prefs)
        
        return options

    def start_browser(self) -> bool:
        """
        Khởi động Chrome browser (hoặc Brave nếu được cấu hình)
        
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            browser_name = "Brave Browser" if "brave" in self.chrome_binary_path.lower() else "Chrome"
            logger.info(f"Starting {browser_name}...")
            logger.info(f"Browser binary: {self.chrome_binary_path}")
            
            options = self._create_chrome_options()
            
            # Use undetected_chromedriver with configured browser binary
            self.driver = uc.Chrome(
                options=options,
                browser_executable_path=self.chrome_binary_path,
                use_subprocess=True,
                version_main=142  # Chỉ định version Chrome để tải đúng ChromeDriver
            )
            
            self.wait = WebDriverWait(self.driver, 20)
            return True
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}", exc_info=True)
            return False

    def open_perplexity(self) -> bool:
        """
        Mở trang Perplexity AI
        
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            logger.info(f"Opening Perplexity: {self.base_url}")
            self.driver.get(self.base_url)
            time.sleep(3)  # Wait for page load
            
            # Check if we're on the right page
            if "perplexity" in self.driver.current_url.lower():
                logger.info("✓ Perplexity page loaded successfully")
                return True
            else:
                logger.warning(f"Unexpected URL: {self.driver.current_url}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to open Perplexity: {e}", exc_info=True)
            return False

    def is_logged_in(self) -> bool:
        """
        Kiểm tra xem đã đăng nhập Perplexity.ai chưa
        
        Returns:
            True nếu đã đăng nhập, False nếu chưa
        """
        try:
            logger.info("Checking login status...")
            time.sleep(3)  # Wait for page to fully load
            
            current_url = self.driver.current_url.lower()
            logger.info(f"Current URL: {current_url}")
            
            # Check 1: URL-based detection
            if any(keyword in current_url for keyword in ['login', 'signin', 'sign-in', 'auth']):
                logger.info("❌ Not logged in - on login/auth page")
                return False
            
            # Check 2: Look for "Sign in" or "Log in" buttons
            try:
                signin_indicators = [
                    "//button[contains(text(), 'Sign in')]",
                    "//button[contains(text(), 'Log in')]",
                    "//a[contains(text(), 'Sign in')]",
                    "//a[contains(text(), 'Log in')]",
                ]
                
                for selector in signin_indicators:
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        if element.is_displayed():
                            logger.info(f"❌ Not logged in - found sign-in button: {selector}")
                            return False
                    except (NoSuchElementException, Exception):
                        continue
                        
            except Exception as e:
                logger.debug(f"Error checking sign-in buttons: {e}")
            
            # Check 3: Look for search/prompt input (indicates logged in)
            try:
                input_selectors = [
                    "textarea[placeholder*='Ask']",
                    "textarea[placeholder*='Search']",
                    "textarea",
                    "div[contenteditable='true']",
                    "[role='textbox']",
                ]
                
                for selector in input_selectors:
                    try:
                        input_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if input_element.is_displayed():
                            logger.info(f"✓ Logged in - found input: {selector}")
                            return True
                    except NoSuchElementException:
                        continue
                        
            except Exception as e:
                logger.debug(f"Error checking input elements: {e}")
            
            # Check 4: Look for user profile/avatar
            try:
                profile_selectors = [
                    "[data-testid*='profile']",
                    "[data-testid*='avatar']",
                    "[aria-label*='Profile']",
                    "[aria-label*='Account']",
                    "img[alt*='Profile']",
                ]
                
                for selector in profile_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if element.is_displayed():
                            logger.info(f"✓ Logged in - found profile element: {selector}")
                            return True
                    except NoSuchElementException:
                        continue
                        
            except Exception as e:
                logger.debug(f"Error checking profile elements: {e}")
            
            # Default: if we're on perplexity.ai and haven't found sign-in button, assume logged in
            if "perplexity.ai" in current_url and "login" not in current_url:
                logger.info("✓ Logged in - on perplexity.ai without login indicators")
                return True
            
            logger.info("❌ Not logged in - no positive indicators found")
            return False
                
        except Exception as e:
            logger.error(f"Error checking login status: {e}", exc_info=True)
            return False

    def send_prompt(self, chapter_content: str) -> bool:
        """
        Gửi prompt vào Perplexity chat và click submit
        Perplexity sử dụng Lexical Editor với cấu trúc đặc biệt
        
        Args:
            chapter_content: Nội dung để gửi (chapter content hoặc prompt text)
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            logger.info("Sending prompt to Perplexity (Lexical Editor)...")
            
            # Find Lexical editor div (contenteditable)
            input_selectors = [
                "div[contenteditable='true'][id='ask-input']",  # Exact Perplexity selector
                "div[contenteditable='true'][data-lexical-editor='true']",
                "div[contenteditable='true'][role='textbox']",
                "div[contenteditable='true']",
                "[contenteditable='true']",
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    input_element = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"✓ Found Lexical editor with selector: {selector}")
                    break
                except TimeoutException:
                    logger.debug(f"Selector not found: {selector}")
                    continue
            
            if not input_element:
                logger.error("❌ Could not find Lexical editor element")
                return False
            
            # Method 1: Insert content using Lexical structure
            logger.info(f"Inserting content into Lexical editor... ({len(chapter_content)} characters)")
            
            try:
                # IMPORTANT: Interact with editor to ensure it's ready
                logger.info("Preparing editor for input...")
                
                # Click to focus
                input_element.click()
                time.sleep(0.5)
                
                # Type a test character and delete it to activate editor
                logger.info("Activating editor with test input...")
                input_element.send_keys(".")
                time.sleep(0.3)
                
                # Select all and delete (clear any placeholder)
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                actions.key_down(Keys.CONTROL)
                actions.send_keys('a')
                actions.key_up(Keys.CONTROL)
                actions.send_keys(Keys.BACK_SPACE)
                actions.perform()
                time.sleep(0.5)
                
                logger.info("Editor activated and cleared")
                
                # **PRIORITY 1: innerHTML with Lexical structure (FASTEST - sends all content at once)**
                try:
                    logger.info("=" * 60)
                    logger.info("Method 1: Trying innerHTML method...")
                    logger.info(f"Original content length: {len(chapter_content)} chars")
                    logger.info("=" * 60)
                    
                    # Re-find element to ensure fresh reference after activation
                    for selector in input_selectors:
                        try:
                            input_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if input_element.is_displayed():
                                logger.info(f"Re-found editor: {selector}")
                                break
                        except:
                            continue
                    
                    # Split content into paragraphs for better formatting
                    paragraphs = chapter_content.split('\n')
                    logger.info(f"Split into {len(paragraphs)} paragraphs")
                    
                    # Build Lexical HTML structure
                    # Each line becomes: <p dir="auto"><span data-lexical-text="true">text</span></p>
                    lexical_html_parts = []
                    for para in paragraphs:
                        if para.strip():  # Non-empty paragraph
                            # Escape HTML special chars
                            escaped_text = (para
                                .replace('&', '&amp;')
                                .replace('<', '&lt;')
                                .replace('>', '&gt;')
                                .replace('"', '&quot;')
                                .replace("'", '&#39;')
                            )
                            lexical_html_parts.append(
                                f'<p dir="auto"><span data-lexical-text="true">{escaped_text}</span></p>'
                            )
                        else:  # Empty paragraph (blank line)
                            lexical_html_parts.append('<p dir="auto"><br></p>')
                    
                    lexical_html = ''.join(lexical_html_parts)
                    logger.info(f"Generated Lexical HTML: {len(lexical_html)} chars")
                    logger.info(f"HTML preview: {lexical_html[:200]}...")
                    
                    # Focus and click to ensure element is ready
                    input_element.click()
                    time.sleep(0.3)
                    
                    # Set innerHTML
                    logger.info("Setting innerHTML...")
                    self.driver.execute_script(
                        "arguments[0].innerHTML = arguments[1];",
                        input_element,
                        lexical_html
                    )
                    time.sleep(1.5)  # Longer wait for DOM update
                    
                    # Trigger input events
                    logger.info("Triggering input events...")
                    self.driver.execute_script("""
                        const element = arguments[0];
                        element.focus();
                        element.dispatchEvent(new Event('input', { bubbles: true }));
                        element.dispatchEvent(new Event('change', { bubbles: true }));
                        element.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true }));
                        element.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
                        element.dispatchEvent(new Event('blur', { bubbles: true }));
                        element.focus();
                    """, input_element)
                    time.sleep(1)
                    
                    # Verify content multiple times
                    logger.info("Verifying innerHTML content...")
                    for attempt in range(5):
                        time.sleep(0.8)
                        try:
                            # Re-find element to avoid stale reference
                            for selector in input_selectors:
                                try:
                                    input_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                                    if input_element.is_displayed():
                                        break
                                except:
                                    continue
                            
                            current_text = input_element.text
                            current_html = self.driver.execute_script("return arguments[0].innerHTML;", input_element)
                            logger.info(f"Verification attempt {attempt + 1}:")
                            logger.info(f"  - Text length: {len(current_text)} chars")
                            logger.info(f"  - HTML length: {len(current_html)} chars")
                            logger.info(f"  - Text preview: {current_text[:100]}...")
                            
                            if len(current_text) >= len(chapter_content) * 0.8:  # Lowered threshold
                                logger.info(f"✓ Content set via innerHTML ({len(current_text)} chars) - ALL AT ONCE")
                                break
                        except Exception as e:
                            logger.warning(f"Verification attempt {attempt + 1} error: {e}")
                    else:
                        current_text = input_element.text
                        logger.error(f"❌ innerHTML verification failed!")
                        logger.error(f"   Expected: {len(chapter_content)} chars")
                        logger.error(f"   Got:      {len(current_text)} chars ({len(current_text)/len(chapter_content)*100:.1f}%)")
                        logger.error(f"   Content in editor: {current_text[:200]}...")
                        raise Exception(f"Content verification failed (got {len(current_text)} chars)")
                        
                except Exception as html_error:
                    logger.warning(f"innerHTML method failed: {html_error}, trying DataTransfer paste simulation...")
                    
                    # **PRIORITY 2: Simulate paste using DataTransfer API (ALL AT ONCE)**
                    try:
                        logger.info("=" * 60)
                        logger.info("Method 2: Trying DataTransfer paste simulation (ALL AT ONCE)...")
                        logger.info(f"Original content length: {len(chapter_content)} chars")
                        logger.info("=" * 60)
                        
                        # Re-find and activate editor
                        for selector in input_selectors:
                            try:
                                input_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                                if input_element.is_displayed():
                                    logger.info(f"Re-found editor: {selector}")
                                    break
                            except:
                                continue
                        
                        # Focus on editor
                        input_element.click()
                        time.sleep(0.5)
                        
                        logger.info("Simulating paste event with DataTransfer...")
                        
                        # Escape content for JavaScript (use JSON.stringify to handle all special chars)
                        import json
                        json_content = json.dumps(chapter_content)
                        
                        # JavaScript to simulate paste event with DataTransfer
                        paste_js = f"""
                        const element = arguments[0];
                        const content = {json_content};
                        
                        // Focus element
                        element.focus();
                        
                        // Create DataTransfer object with content
                        const dataTransfer = new DataTransfer();
                        dataTransfer.setData('text/plain', content);
                        
                        // Create and dispatch paste event
                        const pasteEvent = new ClipboardEvent('paste', {{
                            bubbles: true,
                            cancelable: true,
                            clipboardData: dataTransfer
                        }});
                        
                        element.dispatchEvent(pasteEvent);
                        
                        // Also try input event
                        setTimeout(() => {{
                            element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}, 100);
                        
                        return true;
                        """
                        
                        logger.info("Executing paste simulation...")
                        self.driver.execute_script(paste_js, input_element)
                        time.sleep(3)  # Wait for paste to process
                        
                        # Verify
                        logger.info("Verifying pasted content...")
                        for attempt in range(5):
                            time.sleep(1)
                            try:
                                # Re-find element
                                for selector in input_selectors:
                                    try:
                                        input_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                                        if input_element.is_displayed():
                                            break
                                    except:
                                        continue
                                
                                current_text = input_element.text
                                logger.info(f"Verification attempt {attempt + 1}: {len(current_text)} chars ({len(current_text)/len(chapter_content)*100:.1f}%)")
                                logger.info(f"  Preview: {current_text[:100]}...")
                                
                                if len(current_text) >= len(chapter_content) * 0.7:
                                    logger.info(f"✓ Content pasted via DataTransfer ({len(current_text)} chars) - ALL AT ONCE")
                                    break
                            except Exception as e:
                                logger.warning(f"Verification attempt {attempt + 1} error: {e}")
                        else:
                            current_text = input_element.text
                            logger.error(f"❌ DataTransfer paste verification failed!")
                            logger.error(f"   Expected: {len(chapter_content)} chars")
                            logger.error(f"   Got:      {len(current_text)} chars ({len(current_text)/len(chapter_content)*100:.1f}%)")
                            raise Exception("DataTransfer paste verification failed")
                        
                    except Exception as paste_error:
                        logger.error(f"=" * 60)
                        logger.error(f"❌ ALL INPUT METHODS FAILED!")
                        logger.error(f"innerHTML error: {html_error}")
                        logger.error(f"DataTransfer paste error: {paste_error}")
                        logger.error(f"=" * 60)
                        return False
                time.sleep(0.5)
                final_text = input_element.text
                logger.info(f"Final content length: {len(final_text)} chars (original: {len(chapter_content)})")
                
                if len(final_text) < len(chapter_content) * 0.3:
                    logger.error(f"Content too short after all attempts")
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to set content: {e}", exc_info=True)
                return False
            
            # Find and click submit button
            logger.info("Looking for submit button...")
            submit_selectors = [
                "button[type='submit']",
                "button[aria-label*='Submit']",
                "button[aria-label*='Send']",
                "button[aria-label*='Search']",
                "button.bg-super",  # Perplexity's primary button
                "button svg[data-icon='arrow-right']",  # Arrow icon button
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            submit_button = element
                            logger.info(f"✓ Found submit button: {selector}")
                            break
                    if submit_button:
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not submit_button:
                logger.error("❌ Could not find submit button")
                return False
            
            # Wait for button to be enabled
            logger.info("Waiting for submit button to be enabled...")
            max_wait = 10
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                try:
                    is_disabled = submit_button.get_attribute('disabled')
                    is_aria_disabled = submit_button.get_attribute('aria-disabled')
                    
                    if (is_disabled is None or is_disabled == 'false') and \
                       (is_aria_disabled is None or is_aria_disabled == 'false'):
                        logger.info("✓ Submit button is enabled")
                        break
                    
                    time.sleep(0.5)
                except Exception as e:
                    logger.debug(f"Error checking button state: {e}")
                    time.sleep(0.5)
            
            # Click submit
            logger.info("Clicking submit button...")
            try:
                submit_button.click()
                time.sleep(1)
                logger.info("✓ Submit button clicked")
                return True
            except Exception as e:
                logger.warning(f"Normal click failed: {e}, trying JavaScript...")
                try:
                    self.driver.execute_script("arguments[0].click();", submit_button)
                    time.sleep(1)
                    logger.info("✓ Submit via JavaScript")
                    return True
                except Exception as js_error:
                    logger.error(f"❌ JavaScript click failed: {js_error}")
                    return False
            
        except Exception as e:
            logger.error(f"❌ Failed to send prompt: {e}", exc_info=True)
            return False

    def wait_for_response(self, timeout: int = None) -> bool:
        """
        Đợi Perplexity AI phản hồi xong (generic method)
        DEPRECATED: Use wait_for_conversation_response() or wait_for_image_prompt_response()
        
        Args:
            timeout: Thời gian chờ tối đa (giây), None = không giới hạn
            
        Returns:
            True nếu có response, False nếu thất bại
        """
        # Default to conversation response for backward compatibility
        return self.wait_for_conversation_response(timeout)
    
    def wait_for_conversation_response(self, timeout: int = None) -> bool:
        """
        Đợi Perplexity AI phản hồi conversation JSON
        Auto-scroll để đảm bảo response được render đầy đủ
        
        Args:
            timeout: Thời gian chờ tối đa (giây), None = không giới hạn
            
        Returns:
            True nếu có response, False nếu thất bại
        """
        try:
            if timeout is None:
                logger.info("Waiting for conversation JSON response (no timeout)...")
            else:
                logger.info(f"Waiting for conversation JSON response (timeout: {timeout}s)...")
            
            # Response indicators for conversation JSON
            response_selectors = [
                # Specific Perplexity selectors for code blocks
                "div[id^='markdown-content-'] pre code",
                "div[class*='codeWrapper'] code",
                "pre.not-prose code",
                
                # Fallback selectors
                "pre code",
                "div[id^='markdown-content-']",
                "div[class*='codeWrapper']",
                "pre.not-prose",
            ]
            
            start_time = time.time()
            check_interval = 2
            last_log_time = 0
            last_scroll_time = 0
            scroll_count = 0
            
            while True:
                if timeout is not None and (time.time() - start_time) > timeout:
                    logger.warning(f"Timeout after {timeout}s")
                    return False
                
                elapsed = time.time() - start_time
                
                # Auto-scroll every 3 seconds to load content
                if elapsed - last_scroll_time >= 3:
                    try:
                        # Scroll down to load content
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        scroll_count += 1
                        logger.debug(f"Auto-scrolled to bottom (scroll #{scroll_count})")
                        last_scroll_time = elapsed
                        time.sleep(0.5)  # Wait for content to load after scroll
                    except Exception as scroll_error:
                        logger.debug(f"Scroll error: {scroll_error}")
                
                # Log progress
                if elapsed - last_log_time >= 10 and elapsed > 0:
                    logger.info(f"Still waiting... ({int(elapsed)}s elapsed, {scroll_count} scrolls)")
                    last_log_time = elapsed
                
                # Check for response
                for selector in response_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed():
                                text = element.text.strip()
                                
                                # Check if this looks like a conversation JSON
                                if len(text) > 100:
                                    # Check for conversation JSON markers
                                    if ('{' in text or '[' in text) and '"speakers"' in text:
                                        elapsed_time = time.time() - start_time
                                        logger.info(f"✓ Conversation JSON response found after {elapsed_time:.1f}s ({scroll_count} scrolls)")
                                        
                                        # Scroll to element to ensure it's fully visible
                                        try:
                                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                                            time.sleep(1)
                                        except:
                                            pass
                                        
                                        return True
                                        
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                time.sleep(check_interval)
            
        except Exception as e:
            logger.error(f"Error waiting for conversation response: {e}", exc_info=True)
            return False
    
    def wait_for_image_prompt_response(self, timeout: int = None) -> bool:
        """
        Đợi Perplexity AI phản hồi image prompt JSON
        Auto-scroll để đảm bảo response được render đầy đủ
        
        Args:
            timeout: Thời gian chờ tối đa (giây), None = không giới hạn
            
        Returns:
            True nếu có response, False nếu thất bại
        """
        try:
            if timeout is None:
                logger.info("Waiting for image prompt JSON response (no timeout)...")
            else:
                logger.info(f"Waiting for image prompt JSON response (timeout: {timeout}s)...")
            
            # Response indicators for image prompt JSON
            response_selectors = [
                # Specific Perplexity selectors for code blocks
                "div[id^='markdown-content-'] pre code",
                "div[class*='codeWrapper'] code",
                "pre.not-prose code",
                
                # Fallback selectors
                "pre code",
                "div[id^='markdown-content-']",
                "div[class*='codeWrapper']",
                "pre.not-prose",
            ]
            
            start_time = time.time()
            check_interval = 2
            last_log_time = 0
            last_scroll_time = 0
            scroll_count = 0
            
            while True:
                if timeout is not None and (time.time() - start_time) > timeout:
                    logger.warning(f"Timeout after {timeout}s")
                    return False
                
                elapsed = time.time() - start_time
                
                # Auto-scroll every 3 seconds to load content
                if elapsed - last_scroll_time >= 3:
                    try:
                        # Scroll down to load content
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        scroll_count += 1
                        logger.debug(f"Auto-scrolled to bottom (scroll #{scroll_count})")
                        last_scroll_time = elapsed
                        time.sleep(0.5)  # Wait for content to load after scroll
                    except Exception as scroll_error:
                        logger.debug(f"Scroll error: {scroll_error}")
                
                # Log progress
                if elapsed - last_log_time >= 10 and elapsed > 0:
                    logger.info(f"Still waiting... ({int(elapsed)}s elapsed, {scroll_count} scrolls)")
                    last_log_time = elapsed
                
                # Check for response
                for selector in response_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed():
                                text = element.text.strip()
                                
                                # Check if this looks like an image prompt JSON
                                if len(text) > 100:
                                    # Check for image prompt JSON markers
                                    # Image prompts typically have different structure than conversations
                                    # Check for various prompt-related keywords
                                    has_json_structure = '{' in text or '[' in text
                                    has_prompt_keywords = (
                                        '"prompt"' in text or 
                                        '"prompts"' in text or  # Số nhiều
                                        '"image_prompt' in text or 
                                        '"scenes"' in text or
                                        '"content"' in text and '"id"' in text  # Structure với id và content
                                    )
                                    
                                    # Exclude conversation JSON (has "speakers")
                                    is_conversation = '"speakers"' in text or '"speaker_id"' in text
                                    
                                    if has_json_structure and has_prompt_keywords and not is_conversation:
                                        elapsed_time = time.time() - start_time
                                        logger.info(f"✓ Image prompt JSON response found after {elapsed_time:.1f}s ({scroll_count} scrolls)")
                                        logger.info(f"  Preview: {text[:200]}...")
                                        
                                        # Scroll to element to ensure it's fully visible
                                        try:
                                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                                            time.sleep(1)
                                        except:
                                            pass
                                        
                                        return True
                                        
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                time.sleep(check_interval)
            
        except Exception as e:
            logger.error(f"Error waiting for image prompt response: {e}", exc_info=True)
            return False

    def clean_html_syntax_highlighted_text(self, html_text: str) -> str:
        """Clean HTML text by removing tags"""
        try:
            import re
            clean_text = re.sub(r'<[^>]+>', '', html_text)
            clean_text = clean_text.replace('&quot;', '"')
            clean_text = clean_text.replace('&lt;', '<')
            clean_text = clean_text.replace('&gt;', '>')
            clean_text = clean_text.replace('&amp;', '&')
            clean_text = clean_text.replace('&#39;', "'")
            
            lines = clean_text.split('\n')
            cleaned_lines = [line.strip() for line in lines if line.strip()]
            clean_text = '\n'.join(cleaned_lines)
            
            return clean_text.strip()
        except Exception as e:
            logger.debug(f"Error cleaning HTML: {e}")
            return html_text

    def get_response_text_from_dom(self) -> Optional[str]:
        """
        Đọc response text từ DOM
        Perplexity sử dụng cấu trúc: div[id^='markdown-content-'] > ... > pre > div.codeWrapper > ... > code
        
        Returns:
            Response text hoặc None
        """
        try:
            logger.info("Reading response from DOM...")
            time.sleep(3)  # Wait for content to load
            
            # Perplexity's actual structure for code blocks
            response_selectors = [
                # Specific Perplexity code block structure
                "div[id^='markdown-content-'] pre code",
                "div[class*='codeWrapper'] code",
                "pre.not-prose code",
                
                # Fallback selectors
                "[data-testid*='answer'] pre code",
                "[data-testid*='response'] pre code",
                "div[class*='answer'] pre code",
                "div[class*='response'] pre code",
                "article pre code",
                
                # General selectors (last resort)
                "pre code",
                "[data-testid*='answer']",
                "[data-testid*='response']",
                "div[class*='answer']",
                "div[class*='response']",
                "article",
            ]
            
            for selector in response_selectors:
                try:
                    logger.debug(f"Trying selector: {selector}")
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.debug(f"Found {len(elements)} elements with selector: {selector}")
                    
                    for idx, element in enumerate(elements):
                        try:
                            if not element.is_displayed():
                                logger.debug(f"Element {idx} not displayed, skipping")
                                continue
                            
                            # Try to get text using multiple methods
                            text = None
                            
                            # Method 1: .text property
                            text = element.text
                            logger.debug(f"Element {idx} .text length: {len(text) if text else 0}")
                            
                            # Method 2: textContent via JavaScript
                            if not text or len(text.strip()) < 50:
                                text = self.driver.execute_script(
                                    "return arguments[0].textContent;",
                                    element
                                )
                                logger.debug(f"Element {idx} textContent length: {len(text) if text else 0}")
                            
                            # Method 3: Clean innerHTML from syntax highlighting
                            if not text or len(text.strip()) < 50:
                                html_content = self.driver.execute_script(
                                    "return arguments[0].innerHTML;",
                                    element
                                )
                                if html_content:
                                    logger.debug(f"Element {idx} innerHTML length: {len(html_content)}")
                                    text = self.clean_html_syntax_highlighted_text(html_content)
                                    logger.debug(f"Element {idx} cleaned text length: {len(text) if text else 0}")
                            
                            # Check if we got valid JSON-like content
                            if text and len(text.strip()) > 50:
                                # Check if it looks like JSON
                                text_stripped = text.strip()
                                if text_stripped.startswith('{') or text_stripped.startswith('['):
                                    logger.info(f"✓ Found JSON response with selector '{selector}': {len(text)} chars")
                                    logger.info(f"Preview: {text[:200]}...")
                                    return text.strip()
                                elif '"speakers"' in text or '"speaker_id"' in text:
                                    # Contains JSON structure even without leading brace
                                    logger.info(f"✓ Found JSON-like response with selector '{selector}': {len(text)} chars")
                                    logger.info(f"Preview: {text[:200]}...")
                                    return text.strip()
                                else:
                                    logger.debug(f"Element {idx} has text but doesn't look like JSON")
                                    
                        except Exception as elem_error:
                            logger.debug(f"Error processing element {idx}: {elem_error}")
                            continue
                                
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            logger.error("❌ Could not find response in DOM")
            return None
            
        except Exception as e:
            logger.error(f"Error reading from DOM: {e}", exc_info=True)
            return None

    def extract_json_response(self) -> Optional[Dict[str, Any]]:
        """
        Trích xuất JSON response
        
        Returns:
            Dict chứa JSON data hoặc None
        """
        try:
            logger.info("Extracting JSON response...")
            
            # 🔥 CRITICAL: Scroll to bottom and wait for completion toolbar
            logger.info("🔄 Starting aggressive scrolling to load full content...")
            
            # Completion indicators: Share, Export, Rewrite buttons
            completion_selectors = [
                "button:has(div:contains('Share'))",
                "button:has(div:contains('Export'))",
                "button:has(div:contains('Rewrite'))",
                "button[aria-label*='Copy']",  # Copy button also indicates completion
            ]
            
            max_scrolls = 50  # ⬆️ Increased: Maximum 50 scrolls for long content
            max_scroll_time = 60  # ⏱️ Maximum 60 seconds for scrolling
            scroll_count = 0
            start_scroll_time = time.time()
            last_scroll_height = 0
            stable_scroll_count = 0  # Count how many times scroll height stayed the same
            
            logger.info(f"📊 Scroll limits: {max_scrolls} scrolls or {max_scroll_time}s timeout")
            
            while scroll_count < max_scrolls:
                # ⏱️ Check timeout
                elapsed = time.time() - start_scroll_time
                if elapsed > max_scroll_time:
                    logger.warning(f"⏱️ Scroll timeout after {elapsed:.1f}s, stopping...")
                    break
                
                # Scroll to bottom
                try:
                    # Get current scroll height BEFORE scrolling
                    current_height = self.driver.execute_script("return document.body.scrollHeight")
                    
                    # Scroll to bottom
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    scroll_count += 1
                    time.sleep(1.0)  # ⬆️ Increased: Wait longer for content to load
                    
                    # Get new scroll height AFTER scrolling
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    
                    # Check if scroll position changed
                    if new_height == last_scroll_height:
                        stable_scroll_count += 1
                        logger.debug(f"📍 Scroll {scroll_count}/{max_scrolls} - Height stable ({new_height}px) - Stability: {stable_scroll_count}")
                    else:
                        stable_scroll_count = 0  # Reset stability counter
                        logger.debug(f"📍 Scroll {scroll_count}/{max_scrolls} - Height: {last_scroll_height}px → {new_height}px")
                    
                    last_scroll_height = new_height
                    
                    # If scroll height has been stable for 3 consecutive scrolls, likely at bottom
                    if stable_scroll_count >= 3:
                        logger.info(f"✓ Reached bottom (scroll height stable at {new_height}px for {stable_scroll_count} scrolls)")
                        # Continue to check for completion indicators
                    
                except Exception as scroll_error:
                    logger.debug(f"Scroll error: {scroll_error}")
                
                # Check for completion toolbar
                completion_found = False
                for selector in completion_selectors:
                    try:
                        # Use XPath for better text matching
                        if 'contains' in selector:
                            # Convert to XPath
                            if 'Share' in selector:
                                xpath = "//button//div[contains(text(), 'Share')]"
                            elif 'Export' in selector:
                                xpath = "//button//div[contains(text(), 'Export')]"
                            elif 'Rewrite' in selector:
                                xpath = "//button//div[contains(text(), 'Rewrite')]"
                            else:
                                continue
                            
                            elements = self.driver.find_elements(By.XPATH, xpath)
                        else:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        if elements and any(e.is_displayed() for e in elements):
                            logger.info(f"✓ Completion indicator found: {selector}")
                            completion_found = True
                            break
                    except Exception as e:
                        logger.debug(f"Completion check error for {selector}: {e}")
                
                # If completion found AND scroll is stable, do extra scrolls then break
                if completion_found and stable_scroll_count >= 2:
                    logger.info(f"✅ Response complete after {scroll_count} scrolls (elapsed: {elapsed:.1f}s)")
                    logger.info("🔄 Doing 5 extra aggressive scrolls to ensure all content loaded...")
                    
                    # ⬆️ INCREASED: Do 5 more aggressive scrolls to be absolutely sure
                    for i in range(5):
                        try:
                            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(0.8)
                            scroll_count += 1
                            logger.debug(f"Extra scroll {i+1}/5")
                        except:
                            pass
                    break
            else:
                # Loop completed without break (hit max_scrolls)
                elapsed = time.time() - start_scroll_time
                logger.warning(f"⚠️ Reached max scrolls ({max_scrolls}) after {elapsed:.1f}s, proceeding anyway...")
            
            final_elapsed = time.time() - start_scroll_time
            logger.info(f"✅ Scrolling completed: {scroll_count} scrolls in {final_elapsed:.1f}s")
            
            # 🔥 CRITICAL: Additional scroll inside code blocks to ensure full JSON content
            logger.info("🔄 Scrolling inside code blocks to load full JSON content...")
            try:
                # Find all code blocks
                code_blocks = self.driver.find_elements(By.CSS_SELECTOR, "div[class*='codeWrapper'], pre.not-prose, div[id^='markdown-content-'] pre")
                logger.info(f"Found {len(code_blocks)} code blocks to scroll")
                
                for idx, block in enumerate(code_blocks):
                    try:
                        if not block.is_displayed():
                            continue
                        
                        # Scroll window to bring code block into view
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", block)
                        time.sleep(0.3)
                        
                        # Get scroll height of code block
                        block_scroll_height = self.driver.execute_script("return arguments[0].scrollHeight;", block)
                        block_client_height = self.driver.execute_script("return arguments[0].clientHeight;", block)
                        
                        logger.debug(f"Code block {idx+1}: scrollHeight={block_scroll_height}px, clientHeight={block_client_height}px")
                        
                        # If code block has scrollable content, scroll it
                        if block_scroll_height > block_client_height:
                            logger.info(f"📜 Code block {idx+1} is scrollable, scrolling to bottom...")
                            
                            # Scroll inside the code block multiple times to ensure full load
                            for scroll_attempt in range(10):  # Max 10 scrolls per block
                                current_scroll = self.driver.execute_script("return arguments[0].scrollTop;", block)
                                
                                # Scroll down inside the block
                                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", block)
                                time.sleep(0.3)
                                
                                new_scroll = self.driver.execute_script("return arguments[0].scrollTop;", block)
                                
                                # If scroll position didn't change, we're at bottom
                                if new_scroll == current_scroll:
                                    logger.debug(f"   Scroll attempt {scroll_attempt+1}: Reached bottom at {new_scroll}px")
                                    break
                                else:
                                    logger.debug(f"   Scroll attempt {scroll_attempt+1}: {current_scroll}px → {new_scroll}px")
                            
                            logger.info(f"✓ Code block {idx+1} scrolled to bottom")
                        else:
                            logger.debug(f"Code block {idx+1} is not scrollable")
                            
                    except Exception as block_error:
                        logger.debug(f"Error scrolling code block {idx+1}: {block_error}")
                
                logger.info("✅ Code block scrolling completed")
                
            except Exception as scroll_error:
                logger.warning(f"Error during code block scrolling: {scroll_error}")
            
            # Wait a bit for content to fully render after scrolling
            time.sleep(2)
            
            # Get text from DOM
            json_text = self.get_response_text_from_dom()
            
            if not json_text:
                logger.error("❌ Could not get response text")
                return None
            
            # Parse JSON
            try:
                json_text = json_text.strip()
                
                # Extract from code blocks
                if "```json" in json_text:
                    logger.info("Extracting from ```json block...")
                    json_text = json_text.split("```json")[1].split("```")[0].strip()
                elif "```" in json_text:
                    logger.info("Extracting from ``` block...")
                    json_text = json_text.split("```")[1].split("```")[0].strip()
                
                # Find JSON boundaries
                if not json_text.startswith('{') and not json_text.startswith('['):
                    start_idx = min(
                        json_text.find('{') if json_text.find('{') >= 0 else len(json_text),
                        json_text.find('[') if json_text.find('[') >= 0 else len(json_text)
                    )
                    if start_idx < len(json_text):
                        json_text = json_text[start_idx:]
                
                if json_text.startswith('{'):
                    last_brace = json_text.rfind('}')
                    if last_brace > 0:
                        json_text = json_text[:last_brace + 1]
                elif json_text.startswith('['):
                    last_bracket = json_text.rfind(']')
                    if last_bracket > 0:
                        json_text = json_text[:last_bracket + 1]
                
                # Clean JSON text (remove common issues)
                json_text = self._clean_json_text(json_text)
                
                json_data = json.loads(json_text)
                logger.info("✓ JSON parsed successfully")
                return json_data
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                logger.debug(f"JSON text (first 500 chars): {json_text[:500]}")
                
                # Try to fix and retry
                fixed_json = self._try_fix_json(json_text, e)
                if fixed_json:
                    try:
                        json_data = json.loads(fixed_json)
                        logger.info("✓ JSON parsed successfully after fixing")
                        return json_data
                    except json.JSONDecodeError as e2:
                        logger.error(f"Still failed after fix attempt: {e2}")
                
                logger.warning("Returning raw text instead")
                return {"raw_content": json_text, "error": str(e)}
                
        except Exception as e:
            logger.error(f"Failed to extract JSON: {e}", exc_info=True)
            return None

    def save_conversation_to_file(self, content: str, story_id: int, chapter_number: int,
                                   story_name: str) -> Optional[str]:
        """
        Lưu conversation vào file trong thư mục audio_downloads/<story_name>/conversations/

        Args:
            content: Nội dung cần lưu
            story_id: ID story
            chapter_number: Số chương
            story_name: Tên story (BẮT BUỘC)

        Returns:
            File path hoặc None
        """
        try:
            # Convert story name to slug
            from selenium_audio_generator import convert_to_slug
            story_folder = convert_to_slug(story_name)

            # Tạo đường dẫn: audio_downloads/<story_name>/conversations/
            base_dir = os.path.dirname(os.path.abspath(__file__))
            conversations_dir = os.path.join(
                base_dir,
                'audio_downloads',
                story_folder,
                'conversations'
            )
            os.makedirs(conversations_dir, exist_ok=True)

            filename = f"{story_id}_{chapter_number}.json"
            filepath = os.path.join(conversations_dir, filename)

            logger.info(f"Saving to: {filepath}")

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"✓ File saved ({os.path.getsize(filepath)} bytes)")
            return filepath

        except Exception as e:
            logger.error(f"Failed to save file: {e}", exc_info=True)
            return None
    
    def save_image_prompt_to_file(self, content: str, story_name: str, story_id: int, chapter_number: int) -> Optional[str]:
        """
        Lưu image prompt vào file trong story folder: audio_downloads/<story_name>/image_prompts/

        Args:
            content: Nội dung cần lưu
            story_name: Tên story (BẮT BUỘC)
            story_id: ID story
            chapter_number: Số chương

        Returns:
            File path hoặc None
        """
        try:
            # Convert story name to slug
            from selenium_audio_generator import convert_to_slug
            story_folder = convert_to_slug(story_name)

            # Tạo đường dẫn: audio_downloads/<story_name>/image_prompts/
            base_dir = os.path.dirname(os.path.abspath(__file__))
            prompts_dir = os.path.join(
                base_dir,
                'audio_downloads',
                story_folder,
                'image_prompts'
            )
            os.makedirs(prompts_dir, exist_ok=True)

            filename = f"{story_id}_chapter_{chapter_number}.json"
            filepath = os.path.join(prompts_dir, filename)

            logger.info(f"Saving image prompt to: {filepath}")

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"✓ Image prompt saved ({os.path.getsize(filepath)} bytes)")
            return filepath

        except Exception as e:
            logger.error(f"Failed to save image prompt: {e}", exc_info=True)
            return None

    def goto_conversation_json_page(self) -> bool:
        """
        Mở trang conversation JSON theo config
        
        Returns:
            True nếu thành công
        """
        try:
            url = getattr(config, "PERPLEXITY_CONVERSATION_JSON_URL", None)
            if not url:
                logger.warning("PERPLEXITY_CONVERSATION_JSON_URL not set")
                return True  # Not critical
            
            logger.info(f"Opening conversation page: {url}")
            self.driver.get(url)
            time.sleep(3)
            logger.info("✓ Page loaded")
            return True
        except Exception as e:
            logger.warning(f"Failed to open page: {e}")
            return True  # Not critical
    
    def goto_prompt_json_page(self) -> bool:
        """
        Mở trang prompt JSON theo config (để tạo image prompts)
        
        Returns:
            True nếu thành công
        """
        try:
            url = getattr(config, "PERPLEXITY_CREATE_PROMPT_IMAGES", None)
            if not url:
                logger.warning("PERPLEXITY_CREATE_PROMPT_IMAGES not set")
                return True  # Not critical
            
            logger.info(f"Opening image prompt page: {url}")
            self.driver.get(url)
            time.sleep(3)
            logger.info("✓ Page loaded")
            return True
        except Exception as e:
            logger.warning(f"Failed to open page: {e}")
            return True  # Not critical

    def generate_conversation_json(self, chapter_content: str, story_name: str,
                                  story_id: int = None, chapter_number: int = None,
                                  timeout: int = None, save_to_file: bool = True) -> Optional[Dict[str, Any]]:
        """
        Quy trình hoàn chỉnh: tạo conversation JSON từ Perplexity

        Args:
            chapter_content: Nội dung chapter
            story_name: Tên story (BẮT BUỘC)
            story_id: ID story (optional, dùng cho tên file)
            chapter_number: Số chương (optional, dùng cho tên file)
            timeout: Timeout cho response
            save_to_file: Có lưu file không

        Returns:
            JSON data hoặc None
        """
        try:
            # Start browser if needed
            if not self.driver:
                if not self.start_browser():
                    return None
            
            # Open Perplexity
            if "perplexity" not in self.driver.current_url.lower():
                if not self.open_perplexity():
                    return None
            
            # Check login
            if not self.is_logged_in():
                logger.warning("⚠️ Not logged in")
                logger.info("Please login manually...")
                input("Press Enter after logging in...")
                
                if not self.is_logged_in():
                    logger.error("❌ Still not logged in")
                    return None
                
                logger.info("✓ Login verified")
            
            # Go to conversation page if configured
            if hasattr(config, 'PERPLEXITY_CONVERSATION_JSON_URL') and config.PERPLEXITY_CONVERSATION_JSON_URL:
                self.goto_conversation_json_page()
            
            # Send prompt
            logger.info(f"📖 Sending content ({len(chapter_content)} chars)...")
            if not self.send_prompt(chapter_content):
                return None
            
            # Wait for response
            logger.info("⏳ Waiting for conversation response...")
            if not self.wait_for_conversation_response(timeout):
                logger.error("Failed to get conversation response")
                return None
            
            # Extract JSON
            logger.info("📋 Extracting JSON...")
            json_data = self.extract_json_response()
            
            if not json_data:
                logger.error("Failed to extract JSON")
                return None
            
            # Save to file
            if save_to_file and story_id is not None and chapter_number is not None:
                if "raw_content" in json_data:
                    content_to_save = json_data["raw_content"]
                else:
                    content_to_save = json.dumps(json_data, indent=2, ensure_ascii=False)
                
                saved_path = self.save_conversation_to_file(
                    content_to_save,
                    story_id,
                    chapter_number,
                    story_name
                )
                
                if saved_path:
                    logger.info(f"✓ Saved to: {saved_path}")
                    json_data["saved_filepath"] = saved_path
            
            return json_data
            
        except Exception as e:
            logger.error(f"Failed to generate JSON: {e}", exc_info=True)
            return None
    
    def generate_image_prompts(self, chapter_content: str, story_name: str,
                               story_id: int = None, chapter_number: int = None,
                               timeout: int = None, save_to_file: bool = True) -> Optional[Dict[str, Any]]:
        """
        Quy trình hoàn chỉnh: tạo image prompts JSON từ Perplexity

        Args:
            chapter_content: Nội dung chapter
            story_name: Tên story (BẮT BUỘC)
            story_id: ID story (optional, dùng cho tên file)
            chapter_number: Số chương (optional, dùng cho tên file)
            timeout: Timeout cho response
            save_to_file: Có lưu file không

        Returns:
            JSON data hoặc None
        """
        try:
            # Start browser if needed
            if not self.driver:
                if not self.start_browser():
                    return None
            
            # Open Perplexity
            if "perplexity" not in self.driver.current_url.lower():
                if not self.open_perplexity():
                    return None
            
            # Check login
            if not self.is_logged_in():
                logger.warning("⚠️ Not logged in")
                logger.info("Please login manually...")
                input("Press Enter after logging in...")
                
                if not self.is_logged_in():
                    logger.error("❌ Still not logged in")
                    return None
                
                logger.info("✓ Login verified")
            
            # Go to image prompt page if configured
            if hasattr(config, 'PERPLEXITY_CREATE_PROMPT_IMAGES') and config.PERPLEXITY_CREATE_PROMPT_IMAGES:
                self.goto_prompt_json_page()
            
            # Send prompt
            logger.info(f"🎨 Sending content for image prompts ({len(chapter_content)} chars)...")
            if not self.send_prompt(chapter_content):
                return None
            
            # Wait for response
            logger.info("⏳ Waiting for image prompt response...")
            if not self.wait_for_image_prompt_response(timeout):
                logger.error("Failed to get image prompt response")
                return None
            
            # Extract JSON
            logger.info("📋 Extracting image prompts JSON...")
            json_data = self.extract_json_response()
            
            if not json_data:
                logger.error("Failed to extract image prompts")
                return None
            
            # Save to file in story's image_prompts folder
            if save_to_file and story_id is not None and chapter_number is not None:
                if "raw_content" in json_data:
                    content_to_save = json_data["raw_content"]
                else:
                    content_to_save = json.dumps(json_data, indent=2, ensure_ascii=False)
                
                saved_path = self.save_image_prompt_to_file(
                    content_to_save,
                    story_name,
                    story_id,
                    chapter_number
                )
                
                if saved_path:
                    logger.info(f"✓ Image prompts saved to: {saved_path}")
                    json_data["saved_filepath"] = saved_path
            
            return json_data
            
        except Exception as e:
            logger.error(f"Failed to generate image prompts: {e}", exc_info=True)
            return None
    
    def _clean_json_text(self, json_text: str) -> str:
        """
        Clean JSON text to remove common formatting issues
        
        Args:
            json_text: Raw JSON text
            
        Returns:
            Cleaned JSON text
        """
        import re
        
        # Remove trailing commas before closing brackets/braces
        json_text = re.sub(r',\s*}', '}', json_text)
        json_text = re.sub(r',\s*]', ']', json_text)
        
        # Remove comments (if any)
        json_text = re.sub(r'//.*?\n', '\n', json_text)
        json_text = re.sub(r'/\*.*?\*/', '', json_text, flags=re.DOTALL)
        
        return json_text
    
    def _try_fix_json(self, json_text: str, error: json.JSONDecodeError) -> Optional[str]:
        """
        Attempt to fix JSON based on the error
        
        Args:
            json_text: JSON text with error
            error: JSONDecodeError exception
            
        Returns:
            Fixed JSON text or None
        """
        try:
            error_msg = str(error).lower()
            
            # Try to fix specific errors
            if "expecting ',' delimiter" in error_msg or "expecting property name" in error_msg:
                logger.info("Attempting to fix delimiter/property issues...")
                
                # Try to find the problematic line
                lines = json_text.split('\n')
                if hasattr(error, 'lineno') and error.lineno <= len(lines):
                    line_idx = error.lineno - 1
                    problematic_line = lines[line_idx]
                    
                    # Try to fix trailing comma in object/array
                    if problematic_line.strip().endswith(','):
                        # Check if next non-empty line is closing bracket
                        for next_idx in range(line_idx + 1, len(lines)):
                            next_line = lines[next_idx].strip()
                            if next_line:
                                if next_line.startswith('}') or next_line.startswith(']'):
                                    # Remove trailing comma
                                    lines[line_idx] = lines[line_idx].rstrip(',')
                                    fixed = '\n'.join(lines)
                                    logger.info("✓ Removed trailing comma")
                                    return fixed
                                break
            
            # If can't fix, try to truncate to last valid JSON structure
            if json_text.startswith('{'):
                # Try to find last complete object
                brace_count = 0
                last_valid = 0
                for i, char in enumerate(json_text):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            last_valid = i + 1
                
                if last_valid > 0 and last_valid < len(json_text):
                    truncated = json_text[:last_valid]
                    logger.info(f"Attempting to use truncated JSON (first {last_valid} chars)")
                    return truncated
            
            return None
            
        except Exception as fix_error:
            logger.debug(f"Error in JSON fix attempt: {fix_error}")
            return None

    def close(self):
        """Đóng browser"""
        try:
            if self.driver:
                logger.info("Closing browser...")
                self.driver.quit()
                self.driver = None
                logger.info("✓ Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    def __enter__(self):
        """Context manager entry"""
        self.start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
