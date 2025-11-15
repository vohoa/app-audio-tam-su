"""
Grok AI Automation using Selenium
Tự động hóa việc tạo hội thoại và lấy JSON từ https://x.com/i/grok
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


class GrokAIAutomation:
    """
    Automation class để tương tác với Grok AI
    Nhập prompt để tạo hội thoại, sau đó copy JSON response
    """

    def __init__(self, headless: bool = None, use_profile: bool = True, 
                 profile_name: str = None, system_profile_path: str = None):
        """
        Khởi tạo Grok AI automation instance
        
        Args:
            headless: Chạy browser ở chế độ headless hay không (None = dùng config)
            use_profile: Có sử dụng browser profile để lưu session không
            profile_name: Tên profile để lưu (None = dùng config)
            system_profile_path: Đường dẫn đến profile directory (None = dùng config)
        """
        
        # Get configuration from config.py
        self.headless = headless if headless is not None else config.GROK_HEADLESS
        profile_name = profile_name or config.GROK_AI_PROFILE
        
        print("⚙️ Initializing Grok AI Automation")
        print(f"📁 Profile: {profile_name}")
        print(f"👁️ Headless: {'Yes' if self.headless else 'No (UI visible)'}")
        
        self.driver = None
        self.wait = None
        self._session_invalid = False
        
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
        
        # Grok URL from config
        self.base_url = config.GROK_AI_URL
        
        # Chrome binary và ChromeDriver paths từ config
        self.chrome_binary_path = config.get_chrome_binary_path()
        self.chromedriver_path = config.get_chrome_driver_path()
        
        logger.info(f"Chrome binary: {self.chrome_binary_path}")
        logger.info(f"ChromeDriver: {self.chromedriver_path}")
        logger.info(f"Profile path: {self.profile_path}")
        logger.info(f"Grok URL: {self.base_url}")
        
        # 🔥 Kill all existing browser instances before starting
        logger.info("🧹 Killing all existing browser instances...")
        config.kill_browser_instances(self.chrome_binary_path, verbose=True)
        
        # 🛡️ Browser Fingerprint Manager
        project_root = self._get_project_root()
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

    def _get_profile_path(self) -> str:
        """Tạo đường dẫn profile directory"""
        if not self.use_profile:
            return None
            
        profile_dir = os.path.join(self.system_profile_path, self.profile_name)
        os.makedirs(profile_dir, exist_ok=True)
        logger.info(f"Profile directory: {profile_dir}")
        return profile_dir

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
                browser_executable_path=self.chrome_binary_path,  # Use config binary path
                use_subprocess=True,
                version_main=141  # Chỉ định version Chrome để tải đúng ChromeDriver
            )
            
            self.wait = WebDriverWait(self.driver, 20)
            
            # 🛡️ Apply browser fingerprint
            logger.info("🛡️ Applying browser fingerprint...")
            try:
                fingerprint = self.fingerprint_manager.get_or_create_fingerprint(
                    profile_name=self.profile_name,
                    timezone="America/New_York",  # Grok is X/Twitter, use US timezone
                    cpu_preference="mixed",
                    gpu_preference="mixed",
                    os_preference="windows"
                )
                
                self.fingerprint_manager.apply_fingerprint_to_driver(
                    self.driver, 
                    fingerprint
                )
                logger.info("✅ Browser fingerprint applied successfully")
            except Exception as fp_error:
                logger.warning(f"⚠️ Failed to apply fingerprint: {fp_error}")
                logger.info("ℹ️ Continuing without fingerprint (basic stealth still active)")
            
            logger.info(f"✓ {browser_name} started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}", exc_info=True)
            return False

    def open_grok(self) -> bool:
        """
        Mở trang Grok AI
        
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            logger.info(f"Opening Grok: {self.base_url}")
            self.driver.get(self.base_url)
            time.sleep(3)  # Wait for page load
            
            # Check if we're on the right page
            if "grok" in self.driver.current_url.lower():
                logger.info("✓ Grok page loaded successfully")
                return True
            else:
                logger.warning(f"Unexpected URL: {self.driver.current_url}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to open Grok: {e}", exc_info=True)
            return False

    def is_logged_in(self) -> bool:
        """
        Kiểm tra xem đã đăng nhập Grok.com chưa
        
        Returns:
            True nếu đã đăng nhập, False nếu chưa
        """
        try:
            logger.info("Checking login status...")
            time.sleep(3)  # Wait for page to fully load
            
            current_url = self.driver.current_url.lower()
            logger.info(f"Current URL: {current_url}")
            
            # Check 1: URL-based detection
            # If redirected to login or sign-in page
            if any(keyword in current_url for keyword in ['login', 'signin', 'sign-in', 'auth']):
                logger.info("❌ Not logged in - on login/auth page")
                return False
            
            # Check 2: Look for "Sign in" or "Log in" buttons (indicates not logged in)
            try:
                signin_indicators = [
                    "//button[contains(text(), 'Sign in')]",
                    "//button[contains(text(), 'Log in')]",
                    "//a[contains(text(), 'Sign in')]",
                    "//a[contains(text(), 'Log in')]",
                    "button[data-testid*='login']",
                    "button[data-testid*='signin']"
                ]
                
                for selector in signin_indicators:
                    try:
                        if selector.startswith('//'):
                            element = self.driver.find_element(By.XPATH, selector)
                        else:
                            element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        
                        if element.is_displayed():
                            logger.info(f"❌ Not logged in - found sign-in button: {selector}")
                            return False
                    except (NoSuchElementException, Exception):
                        continue
                        
            except Exception as e:
                logger.debug(f"Error checking sign-in buttons: {e}")
            
            # Check 3: Look for chat input (indicates logged in)
            try:
                chat_input_selectors = [
                    "textarea[aria-label='Ask Grok anything']",  # Exact Grok.com selector
                    "textarea[aria-label*='Ask Grok']",          # Partial match
                    "textarea[aria-label*='Grok']",              # Contains Grok
                    "textarea.bg-transparent",                   # Grok's textarea class
                    "textarea[dir='auto']",                      # Grok's textarea
                    "textarea[placeholder*='Ask']",
                    "textarea[placeholder*='Message']",
                    "textarea[data-testid*='input']",
                    "div[contenteditable='true']",
                    "[role='textbox']",
                    "textarea"
                ]
                
                for selector in chat_input_selectors:
                    try:
                        input_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if input_element.is_displayed():
                            logger.info(f"✓ Logged in - found chat input: {selector}")
                            return True
                    except NoSuchElementException:
                        continue
                        
            except Exception as e:
                logger.debug(f"Error checking input elements: {e}")
            
            # Check 4: Look for user profile/avatar (indicates logged in)
            try:
                profile_selectors = [
                    "[data-testid*='profile']",
                    "[data-testid*='avatar']",
                    "[aria-label*='Profile']",
                    "[aria-label*='Account']",
                    "img[alt*='Profile']",
                    "button[aria-label*='Profile menu']"
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
            
            # Default: if we're on grok.com and haven't found sign-in button, assume logged in
            if "grok.com" in current_url and "login" not in current_url:
                logger.info("✓ Logged in - on grok.com without login indicators")
                return True
            
            logger.info("❌ Not logged in - no positive indicators found")
            return False
                
        except Exception as e:
            logger.error(f"Error checking login status: {e}", exc_info=True)
            return False

    def select_expert_model(self) -> bool:
        """
        Chọn model "Expert" trước khi submit
        
        Steps:
        1. Click vào button chọn model
        2. Đợi dropdown xuất hiện
        3. Click vào option "Expert"
        
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            logger.info("Selecting Expert model...")
            
            # Step 1: Find and click model select button
            model_button_selectors = [
                "button[id='model-select-trigger']",  # Exact ID
                "button[aria-label='Chọn mô hình']",  # Vietnamese
                "button[aria-label*='model' i]",      # Contains "model"
                "button[aria-label*='mô hình' i]",    # Contains "mô hình"
                "button.rounded-full[aria-haspopup='menu']",  # Generic menu button
            ]
            
            model_button = None
            for selector in model_button_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            model_button = element
                            logger.info(f"✓ Found model button with selector: {selector}")
                            break
                    if model_button:
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not model_button:
                logger.warning("⚠️ Could not find model select button, continuing anyway...")
                return True  # Not critical, continue with default model
            
            # Click model button
            logger.info("Clicking model select button...")
            try:
                model_button.click()
                time.sleep(1)  # Wait for dropdown
                logger.info("✓ Model select button clicked")
            except Exception as e:
                logger.warning(f"Normal click failed: {e}, trying JavaScript click...")
                try:
                    self.driver.execute_script("arguments[0].click();", model_button)
                    time.sleep(1)
                    logger.info("✓ Model button clicked via JavaScript")
                except Exception as js_error:
                    logger.warning(f"JavaScript click failed: {js_error}, continuing anyway...")
                    return True  # Not critical
            
            # Step 2: Wait for dropdown and find Expert option
            logger.info("Looking for Expert model option...")
            
            expert_option_selectors = [
                # Look for menuitem with "Expert" text
                "div[role='menuitem']:has(span:contains('Expert'))",
                # XPath alternatives
                "//div[@role='menuitem']//span[contains(text(), 'Expert')]/..",
                "//div[@role='menuitem']//span[text()='Expert']/../..",
                # Generic - find by text in menuitem
                "div[role='menuitem']",  # Will need to check text
            ]
            
            expert_option = None
            
            # Try XPath first (more reliable for text matching)
            try:
                xpath_selectors = [
                    "//div[@role='menuitem'][.//span[text()='Expert']]",
                    "//div[@role='menuitem'][.//span[contains(text(), 'Expert')]]",
                    "//div[@role='menuitem' and contains(., 'Expert')]",
                ]
                
                for xpath in xpath_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, xpath)
                        for element in elements:
                            if element.is_displayed() and 'Expert' in element.text:
                                expert_option = element
                                logger.info(f"✓ Found Expert option with xpath: {xpath}")
                                break
                        if expert_option:
                            break
                    except Exception as e:
                        logger.debug(f"XPath {xpath} failed: {e}")
                        continue
            except Exception as e:
                logger.debug(f"XPath search failed: {e}")
            
            # Fallback: find all menuitems and check text
            if not expert_option:
                try:
                    menuitems = self.driver.find_elements(By.CSS_SELECTOR, "div[role='menuitem']")
                    for item in menuitems:
                        if item.is_displayed() and 'Expert' in item.text:
                            expert_option = item
                            logger.info("✓ Found Expert option by text search")
                            break
                except Exception as e:
                    logger.debug(f"Menuitem text search failed: {e}")
            
            if not expert_option:
                logger.warning("⚠️ Could not find Expert model option, using default model...")
                # Close dropdown if open
                try:
                    self.driver.find_element(By.TAG_NAME, 'body').click()
                except:
                    pass
                return True  # Not critical, continue with current model
            
            # Step 3: Click Expert option
            logger.info("Clicking Expert model option...")
            try:
                expert_option.click()
                time.sleep(0.5)
                logger.info("✓ Expert model selected successfully")
                return True
            except Exception as e:
                logger.warning(f"Normal click failed: {e}, trying JavaScript click...")
                try:
                    self.driver.execute_script("arguments[0].click();", expert_option)
                    time.sleep(0.5)
                    logger.info("✓ Expert model selected via JavaScript")
                    return True
                except Exception as js_error:
                    logger.warning(f"JavaScript click failed: {js_error}, using default model...")
                    return True  # Not critical
            
        except Exception as e:
            logger.warning(f"Error selecting Expert model: {e}, continuing with default...")
            return True  # Not critical, don't fail the whole process

    def click_submit_button(self, max_wait_time: int = 30, content_to_preserve: str = None, input_element = None) -> bool:
        """
        Tìm và click nút Submit sau khi nhập nội dung
        🔥 UPGRADED: Verify và restore content trước khi click để đảm bảo không bị mất
        
        Args:
            max_wait_time: Thời gian chờ tối đa để button enable (giây)
            content_to_preserve: Nội dung cần preserve (để restore nếu bị mất)
            input_element: Reference đến textarea element (để verify content)
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            # Find submit button
            logger.info("Looking for submit button...")
            submit_button_selectors = [
                "button[type='submit'][aria-label='Gửi']",  # Vietnamese "Send"
                "button[type='submit'][aria-label='Send']",  # English "Send"
                "button[type='submit'][aria-label*='gửi' i]",  # Case-insensitive Vietnamese
                "button[type='submit'][aria-label*='send' i]",  # Case-insensitive English
                "button[type='submit'] svg path[d*='M5 11L12 4']",  # SVG up arrow icon
                "button.rounded-full[type='submit']",  # Round submit button
            ]
            
            submit_button = None
            for selector in submit_button_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            submit_button = element
                            logger.info(f"✓ Found submit button with selector: {selector}")
                            break
                    if submit_button:
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not submit_button:
                logger.error("❌ Could not find submit button")
                return False
            
            # 🔥 NEW: Verify content before waiting for button
            if content_to_preserve and input_element:
                logger.info("🔒 Pre-submit content verification...")
                try:
                    current_value = self.driver.execute_script("return arguments[0].value;", input_element)
                    if not current_value or len(current_value) < len(content_to_preserve) * 0.5:  # Less than 50% = lost
                        logger.warning("⚠️ Content lost before submit! Restoring...")
                        self._force_restore_content(input_element, content_to_preserve)
                    else:
                        logger.info(f"✓ Content intact ({len(current_value)} chars)")
                except Exception as e:
                    logger.warning(f"Could not verify content: {e}")
            
            # Wait for button to be enabled (not disabled)
            logger.info("Waiting for submit button to be enabled...")
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                try:
                    # Check if button is enabled (not disabled)
                    is_disabled = submit_button.get_attribute('disabled')
                    
                    if is_disabled is None or is_disabled == 'false' or is_disabled == '':
                        logger.info("✓ Submit button is enabled!")
                        break
                    
                    # 🔥 NEW: Verify content during wait (content might disappear while waiting)
                    if content_to_preserve and input_element:
                        try:
                            current_value = self.driver.execute_script("return arguments[0].value;", input_element)
                            if not current_value or len(current_value) < len(content_to_preserve) * 0.5:
                                logger.warning("⚠️ Content lost during wait! Restoring...")
                                self._force_restore_content(input_element, content_to_preserve)
                        except:
                            pass
                    
                    logger.debug(f"Button still disabled, waiting... (disabled={is_disabled})")
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.debug(f"Error checking button state: {e}")
                    time.sleep(0.5)
            else:
                logger.warning("⚠️ Submit button did not enable within timeout, trying to click anyway...")
            
            # 🔥 NEW: FINAL content verification right before click
            if content_to_preserve and input_element:
                logger.info("🔒 Final content verification before submit...")
                max_restore_attempts = 3
                for attempt in range(max_restore_attempts):
                    try:
                        current_value = self.driver.execute_script("return arguments[0].value;", input_element)
                        if current_value and len(current_value) >= len(content_to_preserve) * 0.9:  # At least 90%
                            logger.info(f"✓ Content verified before submit ({len(current_value)} chars)")
                            break
                        else:
                            logger.warning(f"⚠️ Content incomplete (attempt {attempt+1}/{max_restore_attempts}), restoring...")
                            self._force_restore_content(input_element, content_to_preserve)
                            time.sleep(0.3)
                    except Exception as e:
                        logger.warning(f"Verification attempt {attempt+1} failed: {e}")
                        if attempt < max_restore_attempts - 1:
                            time.sleep(0.2)
            
            # Click the submit button
            logger.info("Clicking submit button...")
            try:
                submit_button.click()
                time.sleep(1)
                logger.info("✓ Submit button clicked successfully")
                return True
            except Exception as e:
                logger.warning(f"Normal click failed: {e}, trying JavaScript click...")
                try:
                    self.driver.execute_script("arguments[0].click();", submit_button)
                    time.sleep(1)
                    logger.info("✓ Submit button clicked via JavaScript")
                    return True
                except Exception as js_error:
                    logger.error(f"❌ JavaScript click also failed: {js_error}")
                    return False
            
        except Exception as e:
            logger.error(f"❌ Failed to click submit button: {e}", exc_info=True)
            return False

    def _force_restore_content(self, input_element, content: str, max_attempts: int = 3) -> bool:
        """
        🔥 FORCE restore content vào textarea bằng mọi cách
        
        Args:
            input_element: Textarea element
            content: Nội dung cần restore
            max_attempts: Số lần thử tối đa
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        logger.info(f"🔄 Force restoring content ({len(content)} chars)...")
        
        for attempt in range(max_attempts):
            try:
                # Method 1: Direct JavaScript value set + events
                self.driver.execute_script("""
                    var elem = arguments[0];
                    var content = arguments[1];
                    
                    // Clear first
                    elem.value = '';
                    elem.textContent = '';
                    
                    // Set content
                    elem.value = content;
                    
                    // Fire ALL possible events
                    elem.dispatchEvent(new Event('input', { bubbles: true }));
                    elem.dispatchEvent(new Event('change', { bubbles: true }));
                    elem.dispatchEvent(new Event('keydown', { bubbles: true }));
                    elem.dispatchEvent(new Event('keyup', { bubbles: true }));
                    elem.dispatchEvent(new Event('keypress', { bubbles: true }));
                    
                    // Focus and blur to trigger validation
                    elem.focus();
                    elem.blur();
                    elem.focus();
                """, input_element, content)
                
                time.sleep(0.2)
                
                # Verify
                restored = self.driver.execute_script("return arguments[0].value;", input_element)
                if restored and len(restored) >= len(content) * 0.9:
                    logger.info(f"✓ Content restored successfully (attempt {attempt+1})")
                    return True
                else:
                    logger.warning(f"Restore attempt {attempt+1} incomplete: {len(restored) if restored else 0}/{len(content)} chars")
                    
                # Method 2: Focus + send keys to trigger detection (if Method 1 failed)
                if attempt < max_attempts - 1:
                    input_element.click()
                    time.sleep(0.1)
                    input_element.send_keys(Keys.SPACE)
                    time.sleep(0.05)
                    input_element.send_keys(Keys.BACKSPACE)
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.warning(f"Restore attempt {attempt+1} failed: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(0.2)
        
        logger.error("❌ Failed to restore content after all attempts")
        return False

    def send_prompt(self, chapter_content: str) -> bool:
        """
        Gửi prompt vào Grok chat và click submit
        
        Args:
            chapter_content: Nội dung để gửi (chapter content hoặc prompt text)
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            logger.info("Sending prompt to Grok...")
            
            # Find input field based on actual Grok.com HTML structure
            # Priority order: most specific to most generic
            input_selectors = [
                "textarea[aria-label='Ask Grok anything']",  # Exact match from Grok.com
                "textarea[aria-label*='Ask Grok']",          # Partial match
                "textarea[aria-label*='Grok']",              # Contains Grok
                "textarea.bg-transparent",                   # Grok's transparent textarea
                "textarea[dir='auto']",                      # Grok's auto-direction textarea
                "textarea",                                  # Generic textarea
                "[contenteditable='true']",                  # Contenteditable fallback
                "[role='textbox']"                           # Role textbox fallback
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    input_element = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"✓ Found input element with selector: {selector}")
                    break
                except TimeoutException:
                    logger.debug(f"Selector not found: {selector}")
                    continue
            
            if not input_element:
                logger.error("❌ Could not find input element with any selector")
                return False
            
            # Use JavaScript to set value directly (bypass clipboard completely)
            logger.info(f"Setting prompt content via JavaScript... ({len(chapter_content)} characters)")
            
            try:
                # Method 1: Set value directly using JavaScript (most reliable)
                try:
                    # Clear existing content first
                    self.driver.execute_script("arguments[0].value = '';", input_element)
                    time.sleep(0.1)
                    
                    # Set new content via JavaScript
                    self.driver.execute_script(
                        "arguments[0].value = arguments[1];",
                        input_element,
                        chapter_content
                    )
                    time.sleep(0.2)
                    logger.debug("✓ Content set via JavaScript")
                    
                    # CRITICAL: Focus and simulate real user typing to trigger Grok's event detection
                    input_element.click()
                    time.sleep(0.2)
                    
                    # Send a space + backspace to simulate real typing (this triggers Grok's detection)
                    input_element.send_keys(Keys.SPACE)
                    time.sleep(0.1)
                    input_element.send_keys(Keys.BACKSPACE)
                    time.sleep(0.2)
                    
                    logger.debug("✓ Simulated user input to trigger Grok detection")
                    
                    # Trigger input event to update UI
                    self.driver.execute_script("""
                        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                    """, input_element)
                    time.sleep(0.3)
                    logger.debug("✓ Content locked with events")
                    
                    # Verify content was set and persists
                    current_value = self.driver.execute_script("return arguments[0].value;", input_element)
                    if current_value and len(current_value) > 0:
                        logger.info(f"✓ Content set successfully ({len(current_value)} characters)")
                    else:
                        raise Exception("Content verification failed")
                        
                except Exception as js_error:
                    logger.warning(f"JavaScript method failed: {js_error}, trying clipboard method...")
                    
                    # Method 2: Clipboard paste as fallback
                    try:
                        # Clear and create new clipboard
                        pyperclip.copy('')  # Clear
                        time.sleep(0.1)
                        pyperclip.copy(chapter_content)  # Set new content
                        time.sleep(0.2)
                        logger.debug(f"✓ Clipboard created with chapter content ({len(chapter_content)} chars)")
                        
                        # Focus on input
                        input_element.click()
                        time.sleep(0.2)
                        
                        # Paste using ActionChains
                        actions = ActionChains(self.driver)
                        actions.move_to_element(input_element)
                        actions.click()
                        actions.key_down(Keys.CONTROL)
                        actions.send_keys('v')
                        actions.key_up(Keys.CONTROL)
                        actions.perform()
                        time.sleep(0.5)
                        logger.debug("✓ Paste action performed")
                        
                        # Verify
                        pasted_content = self.driver.execute_script(
                            "return arguments[0].value || arguments[0].textContent;", 
                            input_element
                        )
                        
                        if pasted_content and len(pasted_content) > 0:
                            logger.info(f"✓ Content pasted successfully ({len(pasted_content)} characters)")
                        else:
                            raise Exception("Paste verification failed")
                            
                    except Exception as paste_error:
                        logger.warning(f"Clipboard paste failed: {paste_error}, trying send_keys...")
                        
                        # Method 3: send_keys as last resort
                        input_element.clear()
                        input_element.send_keys(chapter_content)
                        logger.info("✓ Content typed via send_keys fallback")
                
            except Exception as e:
                logger.error(f"All input methods failed: {e}")
                return False
            
            logger.info("✓ Prompt input completed successfully")
            
            # Select Expert model before submitting
            # logger.info("Selecting Expert model...")
            # self.select_expert_model()
            
            # CRITICAL: Re-verify and restore content after model selection
            # (Model selection may cause textarea to lose content)
            try:
                time.sleep(0.3)
                
                # Re-find textarea (it may have been re-rendered)
                for selector in input_selectors:
                    try:
                        temp_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if temp_element.is_displayed():
                            input_element = temp_element
                            break
                    except:
                        continue
                
                if input_element:
                    # Check if content still exists
                    current_value = self.driver.execute_script("return arguments[0].value;", input_element)
                    
                    if not current_value or len(current_value) == 0:
                        logger.warning("⚠️ Content lost after model selection, restoring...")
                        self._force_restore_content(input_element, chapter_content)
                    else:
                        logger.info(f"✓ Content verified after model selection ({len(current_value)} characters)")
                        
            except Exception as e:
                logger.warning(f"Could not verify content after model selection: {e}")
            
            # 🔥 Click submit button WITH content protection
            # Pass content and input_element for continuous verification
            if not self.click_submit_button(
                max_wait_time=30,
                content_to_preserve=chapter_content,
                input_element=input_element
            ):
                logger.error("❌ Failed to click submit button")
                return False
            
            logger.info("✓ Prompt sent and submitted successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send prompt: {e}", exc_info=True)
            return False

    def wait_for_response(self, timeout: int = None) -> bool:
        """
        Đợi Grok AI phản hồi xong bằng cách chờ action-buttons với class last-response xuất hiện
        
        Args:
            timeout: Thời gian chờ tối đa (giây), None = không giới hạn (chờ mãi)
            
        Returns:
            True nếu có response, False nếu thất bại
        """
        try:
            if timeout is None:
                logger.info("Waiting for Grok response (no timeout - waiting indefinitely)...")
            else:
                logger.info(f"Waiting for Grok response (timeout: {timeout}s)...")
            
            # Priority 1: Selectors cho action-buttons container với last-response class
            action_buttons_selectors = [
                "div.action-buttons.last-response",  # Div có cả 2 class
                ".last-response div.action-buttons",  # Parent có last-response
                "div.last-response .action-buttons",  # Alternative structure
                "div.action-buttons.print\\:hidden.last-response",  # With print:hidden class
            ]
            
            # Priority 2: Selectors cho specific buttons trong last-response (fallback)
            specific_button_selectors = [
                ".last-response button[aria-label='Copy']",          # English Copy button
                ".last-response button[aria-label='Sao chép']",      # Vietnamese Copy button  
                ".last-response button[aria-label='Read Aloud']",    # Read Aloud button
                ".last-response button[aria-label='Regenerate']",    # Regenerate button
                ".last-response button[aria-label='Like']",          # Like button
            ]
            
            start_time = time.time()
            check_interval = 2  # Check every 2 seconds
            last_log_time = 0
            
            while True:
                # Check timeout nếu có
                if timeout is not None and (time.time() - start_time) > timeout:
                    logger.warning(f"Timeout after {timeout}s waiting for response")
                    return False
                
                # Log progress every 10 seconds
                elapsed = time.time() - start_time
                if elapsed - last_log_time >= 10 and elapsed > 0:
                    logger.info(f"Still waiting... ({int(elapsed)}s elapsed)")
                    last_log_time = elapsed
                
                # Priority 1: Try to find action-buttons container
                for selector in action_buttons_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        for element in elements:
                            if element.is_displayed():
                                elapsed_time = time.time() - start_time
                                logger.info(f"✓ Action buttons container found after {elapsed_time:.1f}s")
                                logger.debug(f"   Using selector: {selector}")
                                # Extra wait to ensure buttons are fully rendered
                                time.sleep(0.5)
                                return True
                                
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                # Priority 2: Fallback to specific buttons
                for selector in specific_button_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        for element in elements:
                            if element.is_displayed():
                                elapsed_time = time.time() - start_time
                                logger.info(f"✓ Action button found after {elapsed_time:.1f}s")
                                logger.debug(f"   Using selector: {selector}")
                                time.sleep(0.5)
                                return True
                                
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                # Wait before next check
                time.sleep(check_interval)
            
        except Exception as e:
            logger.error(f"Error waiting for response: {e}", exc_info=True)
            return False

    def click_copy_button(self) -> bool:
        """
        (OPTIONAL) Thử click nút Copy trong last-response
        NOTE: Function này không bắt buộc phải thành công vì ta có thể đọc trực tiếp từ DOM
        
        Returns:
            True nếu click thành công (không quan tâm clipboard), False nếu không tìm thấy button
        """
        try:
            logger.info("(Optional) Trying to click copy button...")
            
            # Selectors cho nút Copy
            copy_button_selectors = [
                ".last-response button[aria-label='Sao chép']",
                ".last-response button[aria-label='Copy']",
                "button[aria-label='Sao chép']",
                "button[aria-label='Copy']",
            ]
            
            # Try to find and click copy button (best effort)
            for selector in copy_button_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            # Try simple click
                            try:
                                element.click()
                                logger.info(f"✓ Copy button clicked (selector: {selector})")
                                time.sleep(1)
                                return True
                            except:
                                # Try JavaScript click
                                try:
                                    self.driver.execute_script("arguments[0].click();", element)
                                    logger.info(f"✓ Copy button clicked via JS (selector: {selector})")
                                    time.sleep(1)
                                    return True
                                except:
                                    continue
                except:
                    continue
            
            logger.info("⚠️ Could not click copy button (not critical - will read from DOM)")
            return False
            
        except Exception as e:
            logger.debug(f"Copy button click failed: {e}")
            return False
                    
        except Exception as e:
            logger.error(f"Error clicking copy button: {e}", exc_info=True)
            return False

    def clean_html_syntax_highlighted_text(self, html_text: str) -> str:
        """
        Clean HTML syntax-highlighted text (remove <span> tags với class="line" và style)
        Xử lý cấu trúc: <pre class="shiki..."><code><span class="line"><span style="color:...">text</span></span></code></pre>
        
        Args:
            html_text: HTML text với syntax highlighting
            
        Returns:
            Clean text without HTML tags
        """
        try:
            import re
            
            # Log structure for debugging
            if '<pre class="shiki' in html_text:
                logger.debug("Detected Grok shiki syntax highlighting")
            
            # Method 1: Remove all HTML tags, keep only text content
            # This regex removes all tags but keeps the text inside
            clean_text = re.sub(r'<[^>]+>', '', html_text)
            
            # Decode HTML entities (&quot; -> ", &lt; -> <, &gt; -> >, &amp; -> &)
            clean_text = clean_text.replace('&quot;', '"')
            clean_text = clean_text.replace('&lt;', '<')
            clean_text = clean_text.replace('&gt;', '>')
            clean_text = clean_text.replace('&amp;', '&')
            clean_text = clean_text.replace('&#39;', "'")
            
            # Remove extra whitespace but preserve newlines
            lines = clean_text.split('\n')
            cleaned_lines = [line.strip() for line in lines if line.strip()]
            clean_text = '\n'.join(cleaned_lines)
            
            logger.debug(f"Cleaned text length: {len(clean_text)} chars")
            return clean_text.strip()
            
        except Exception as e:
            logger.debug(f"Error cleaning HTML text: {e}")
            return html_text

    def get_response_text_from_dom(self) -> Optional[str]:
        """
        Đọc trực tiếp nội dung response từ DOM (BYPASS CLIPBOARD)
        Xử lý cả text thường và HTML syntax-highlighted
        
        Returns:
            String chứa response text hoặc None nếu thất bại
        """
        try:
            logger.info("Reading response text directly from DOM...")
            
            # CRITICAL: Wait for content to be fully loaded
            # Sometimes HTML structure is present but content is still loading
            logger.info("Waiting for response content to fully load...")
            time.sleep(2)  # Give browser time to render content
            
            # Wait for text content to be present (not just HTML structure)
            max_wait = 10
            start_time = time.time()
            content_loaded = False
            
            while time.time() - start_time < max_wait:
                try:
                    # Check if .response-content-markdown has actual content (not just empty divs)
                    response_content = self.driver.find_element(By.CSS_SELECTOR, ".response-content-markdown")
                    text_content = self.driver.execute_script(
                        "return arguments[0].textContent || arguments[0].innerText;",
                        response_content
                    )
                    
                    if text_content and len(text_content.strip()) > 100:
                        logger.info(f"✓ Content loaded ({len(text_content)} characters)")
                        content_loaded = True
                        break
                    else:
                        logger.debug(f"Content still loading... ({len(text_content) if text_content else 0} chars)")
                        time.sleep(1)
                except:
                    logger.debug("Waiting for .response-content-markdown to appear...")
                    time.sleep(1)
            
            if not content_loaded:
                logger.warning("⚠️ Content may not be fully loaded, continuing anyway...")
            
            # DEBUG: First check if .response-content-markdown exists
            try:
                response_elements = self.driver.find_elements(By.CSS_SELECTOR, ".response-content-markdown")
                logger.info(f"DEBUG: Found {len(response_elements)} .response-content-markdown elements")
                
                if response_elements:
                    for idx, elem in enumerate(response_elements[:3]):  # Check first 3
                        try:
                            tag = elem.tag_name
                            classes = elem.get_attribute('class')
                            is_visible = elem.is_displayed()
                            logger.debug(f"  [{idx}] Tag: {tag}, Classes: {classes}, Visible: {is_visible}")
                            
                            # Get structure of first element
                            if idx == 0:
                                inner_html_sample = self.driver.execute_script(
                                    "return arguments[0].innerHTML.substring(0, 500);",
                                    elem
                                )
                                logger.debug(f"  HTML structure sample:\n{inner_html_sample}")
                        except Exception as e:
                            logger.debug(f"  [{idx}] Error inspecting element: {e}")
            except Exception as e:
                logger.warning(f"DEBUG: Could not find .response-content-markdown elements: {e}")
            
            # Selectors for response text elements - FIXED to use .response-content-markdown
            response_selectors = [
                # Grok's syntax-highlighted code blocks - PRIORITY
                ".response-content-markdown pre.shiki code",
                ".response-content-markdown pre[class*='shiki'] code",
                # Standard code blocks
                ".response-content-markdown pre code",
                ".response-content-markdown code pre",
                ".response-content-markdown code",
                ".response-content-markdown pre",
                # Markdown content
                ".response-content-markdown [data-message-text]",
                ".response-content-markdown div[class*='message-content']",
                ".response-content-markdown",  # The container itself
                # Generic text containers
                ".response-content-markdown article",
                ".response-content-markdown div.text-fg-primary",
                ".response-content-markdown p",
            ]
            
            response_text = None
            
            for selector in response_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.debug(f"Selector '{selector}': found {len(elements)} elements")
                    
                    for element in elements:
                        if element.is_displayed():
                            # Method 1: Try .text first (best for plain text)
                            text = element.text
                            
                            # Method 2: If .text is empty or very short, try innerHTML/outerHTML
                            if not text or len(text.strip()) < 50:
                                # CRITICAL FIX: Get outerHTML of parent if checking for <pre class="shiki">
                                # Because selector ".last-response pre.shiki code" returns <code> element
                                # and innerHTML doesn't include parent <pre> tag
                                
                                # Try to get parent element if this is a <code> inside <pre>
                                parent_element = self.driver.execute_script(
                                    "return arguments[0].parentElement;",
                                    element
                                )
                                
                                # Check if parent is <pre> with shiki class
                                if parent_element:
                                    parent_tag = parent_element.tag_name.lower()
                                    parent_classes = parent_element.get_attribute('class') or ''
                                    
                                    logger.debug(f"Element: {element.tag_name}, Parent: {parent_tag}, Classes: {parent_classes}")
                                    
                                    # If parent is <pre> with shiki, use parent's outerHTML
                                    if parent_tag == 'pre' and 'shiki' in parent_classes:
                                        logger.info("Found Grok shiki code block, using parent outerHTML...")
                                        html_content = self.driver.execute_script(
                                            "return arguments[0].outerHTML;",
                                            parent_element
                                        )
                                        logger.debug(f"Parent HTML sample: {html_content[:200]}...")
                                        text = self.clean_html_syntax_highlighted_text(html_content)
                                    else:
                                        # Normal case: use element's innerHTML
                                        html_content = self.driver.execute_script(
                                            "return arguments[0].innerHTML;",
                                            element
                                        )
                                        
                                        if html_content:
                                            # Check if it contains syntax highlighting tags
                                            if ('<span class="line">' in html_content or 
                                                'style="color:' in html_content):
                                                logger.info("Detected syntax-highlighted HTML, cleaning...")
                                                logger.debug(f"HTML sample: {html_content[:200]}...")
                                                text = self.clean_html_syntax_highlighted_text(html_content)
                                            else:
                                                # Just remove all HTML tags
                                                import re
                                                text = re.sub(r'<[^>]+>', '', html_content)
                                else:
                                    # No parent, use element innerHTML
                                    html_content = self.driver.execute_script(
                                        "return arguments[0].innerHTML;",
                                        element
                                    )
                                    
                                    if html_content:
                                        # Check for syntax highlighting
                                        if ('<span class="line">' in html_content or 
                                            'style="color:' in html_content):
                                            logger.info("Detected syntax-highlighted HTML, cleaning...")
                                            text = self.clean_html_syntax_highlighted_text(html_content)
                                        else:
                                            import re
                                            text = re.sub(r'<[^>]+>', '', html_content)
                            
                            # Method 3: If still empty, try textContent via JS
                            if not text or len(text.strip()) < 50:
                                text = self.driver.execute_script(
                                    "return arguments[0].textContent || arguments[0].innerText;",
                                    element
                                )
                            
                            if text and len(text.strip()) > 50:  # Reasonable length
                                response_text = text.strip()
                                logger.info(f"✓ Found response text: {len(response_text)} characters")
                                logger.debug(f"   Using selector: {selector}")
                                logger.debug(f"   Text sample: {response_text[:100]}...")
                                return response_text
                                
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            # Fallback: Try to get ALL text from .response-content-markdown container
            if not response_text:
                try:
                    logger.info("Trying to get all text from .response-content-markdown container...")
                    
                    # Try multiple ways to get the response content
                    response_container = None
                    
                    # Method 1: .response-content-markdown class (CORRECT SELECTOR)
                    try:
                        response_container = self.driver.find_element(By.CSS_SELECTOR, ".response-content-markdown")
                        logger.info("✓ Found .response-content-markdown container")
                    except Exception as e:
                        logger.debug(f"Method 1 (.response-content-markdown) failed: {e}")
                    
                    # Method 2: Try action-buttons.last-response sibling
                    if not response_container:
                        try:
                            action_buttons = self.driver.find_element(By.CSS_SELECTOR, "div.action-buttons.last-response")
                            # Find previous sibling that contains .response-content-markdown
                            response_container = self.driver.execute_script("""
                                let buttons = arguments[0];
                                let sibling = buttons.previousElementSibling;
                                while (sibling) {
                                    if (sibling.querySelector('.response-content-markdown')) {
                                        return sibling.querySelector('.response-content-markdown');
                                    }
                                    sibling = sibling.previousElementSibling;
                                }
                                return null;
                            """, action_buttons)
                            if response_container:
                                logger.info("✓ Found response-content-markdown via action-buttons sibling")
                        except Exception as e:
                            logger.debug(f"Method 2 (action-buttons sibling) failed: {e}")
                    
                    # Method 3: Find all response-content-markdown and get the last one
                    if not response_container:
                        try:
                            all_responses = self.driver.find_elements(By.CSS_SELECTOR, ".response-content-markdown")
                            if all_responses:
                                response_container = all_responses[-1]
                                logger.info(f"✓ Found response-content-markdown as last element ({len(all_responses)} total)")
                        except Exception as e:
                            logger.debug(f"Method 3 (last response-content-markdown) failed: {e}")
                    
                    if not response_container:
                        logger.error("❌ Could not find .response-content-markdown container with any method")
                        return None
                    
                    # Try innerHTML first (may have syntax highlighting)
                    html_content = self.driver.execute_script(
                        "return arguments[0].innerHTML;",
                        response_container
                    )
                    
                    if html_content:
                        logger.debug(f"Container has {len(html_content)} characters of HTML")
                        
                        if ('<pre class="shiki' in html_content or 
                            '<span class="line">' in html_content or 
                            'style="color:' in html_content):
                            logger.info("Detected Grok syntax-highlighted HTML in container, cleaning...")
                            logger.debug(f"Container HTML sample: {html_content[:200]}...")
                            response_text = self.clean_html_syntax_highlighted_text(html_content)
                        else:
                            # Get textContent
                            response_text = self.driver.execute_script(
                                "return arguments[0].textContent || arguments[0].innerText;",
                                response_container
                            )
                    
                    if response_text and len(response_text.strip()) > 50:
                        logger.info(f"✓ Got text from container: {len(response_text)} characters")
                        logger.debug(f"   Text sample: {response_text[:100]}...")
                        return response_text.strip()
                    else:
                        logger.warning(f"Container text too short or empty: {len(response_text) if response_text else 0} chars")
                        
                except Exception as e:
                    logger.debug(f"Container fallback failed: {e}")
            
            logger.error("❌ Could not find response text in DOM")
            return None
            
        except Exception as e:
            logger.error(f"Error reading response from DOM: {e}", exc_info=True)
            return None

    def get_clipboard_and_parse_json(self) -> Optional[Dict[str, Any]]:
        """
        Lấy nội dung từ clipboard và parse thành JSON
        FALLBACK: Nếu clipboard empty, đọc trực tiếp từ DOM
        
        Returns:
            Dict chứa JSON data hoặc None nếu thất bại
        """
        try:
            # Method 1: Try clipboard first
            time.sleep(0.5)
            json_text = pyperclip.paste()
            
            if not json_text or len(json_text.strip()) == 0:
                logger.warning("⚠️ Clipboard is empty, reading from DOM instead...")
                
                # Method 2: Read directly from DOM (BYPASS CLIPBOARD)
                json_text = self.get_response_text_from_dom()
                
                if not json_text:
                    logger.error("❌ Could not get response text from DOM either")
                    return None
                    
                logger.info(f"✓ Got {len(json_text)} characters from DOM")
            else:
                logger.info(f"✓ Got {len(json_text)} characters from clipboard")
            
            # Parse JSON
            try:
                # Clean up text if needed
                json_text = json_text.strip()
                
                # DEBUG: Log raw text structure to understand what we got
                logger.debug(f"Raw text first 1000 chars:\n{json_text[:1000]}")
                logger.debug(f"Raw text last 500 chars:\n{json_text[-500:]}")
                
                # Try to find JSON in code blocks
                if "```json" in json_text:
                    logger.info("Extracting JSON from ```json code block...")
                    json_text = json_text.split("```json")[1].split("```")[0].strip()
                elif "```" in json_text:
                    logger.info("Extracting JSON from ``` code block...")
                    json_text = json_text.split("```")[1].split("```")[0].strip()
                
                # Additional cleaning: Remove any leading/trailing text before/after JSON
                # JSON must start with { or [ 
                if not json_text.startswith('{') and not json_text.startswith('['):
                    logger.info("Text doesn't start with JSON, trying to find JSON object...")
                    # Find first { or [
                    start_idx = min(
                        json_text.find('{') if json_text.find('{') >= 0 else len(json_text),
                        json_text.find('[') if json_text.find('[') >= 0 else len(json_text)
                    )
                    if start_idx < len(json_text):
                        json_text = json_text[start_idx:]
                        logger.info(f"Trimmed to start from character {start_idx}")
                
                # Find last } or ]
                if json_text.startswith('{'):
                    last_brace = json_text.rfind('}')
                    if last_brace > 0:
                        json_text = json_text[:last_brace + 1]
                elif json_text.startswith('['):
                    last_bracket = json_text.rfind(']')
                    if last_bracket > 0:
                        json_text = json_text[:last_bracket + 1]
                
                logger.debug(f"After cleaning, JSON text first 300 chars: {json_text[:300]}")
                
                # Try to parse as JSON
                json_data = json.loads(json_text)
                logger.info("✓ JSON parsed successfully")
                return json_data
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                logger.error(f"Error at line {e.lineno}, column {e.colno}, position {e.pos}")
                
                # Show context around error
                if e.pos and e.pos < len(json_text):
                    start = max(0, e.pos - 100)
                    end = min(len(json_text), e.pos + 100)
                    context = json_text[start:end]
                    logger.error(f"Context around error:\n{context}")
                
                logger.debug(f"Full raw text (first 2000 chars):\n{json_text[:2000]}")
                
                # Return raw text as fallback (để có thể lưu file)
                logger.warning("Returning raw text instead of JSON object")
                return {"raw_content": json_text}
                
        except Exception as e:
            logger.error(f"Error getting clipboard and parsing JSON: {e}", exc_info=True)
            return None

    def extract_json_response(self) -> Optional[Dict[str, Any]]:
        """
        Trích xuất JSON response từ Grok
        Method 1: Thử click Copy button (optional, có thể fail)
        Method 2: Đọc trực tiếp từ DOM (main method)
        
        Returns:
            Dict chứa JSON data hoặc None nếu thất bại
        """
        try:
            logger.info("Extracting JSON response...")
            
            # Optional: Try to click copy button (không bắt buộc thành công)
            self.click_copy_button()
            
            # Main method: Get content from clipboard OR DOM
            return self.get_clipboard_and_parse_json()
            
        except Exception as e:
            logger.error(f"Failed to extract JSON: {e}", exc_info=True)
            return None

    def save_conversation_to_file(self, content: str, story_id: int, chapter_number: int,
                                   story_name: str) -> Optional[str]:
        """
        Lưu nội dung conversation vào file trong thư mục audio_downloads/<story_name>/conversations/

        Args:
            content: Nội dung cần lưu (JSON string hoặc raw text)
            story_id: ID của story
            chapter_number: Số thứ tự chapter
            story_name: Tên story (BẮT BUỘC)

        Returns:
            Đường dẫn file đã lưu, hoặc None nếu thất bại
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

            # Tạo tên file
            filename = f"{story_id}_{chapter_number}.json"
            filepath = os.path.join(conversations_dir, filename)

            logger.info(f"Saving conversation to: {filepath}")

            # Lưu file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            file_size = os.path.getsize(filepath)
            logger.info(f"✓ File saved successfully ({file_size} bytes)")
            logger.info(f"  Location: {filepath}")

            return filepath

        except Exception as e:
            logger.error(f"Failed to save conversation file: {e}", exc_info=True)
            return None


    def goto_conversation_json_page(self) -> bool:
        """
        Mở trang chứa conversation JSON theo cấu hình CONVERSATION_JSON_URL
        
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            url = getattr(config, "CONVERSATION_JSON_URL", None)
            if not url:
                logger.error("CONVERSATION_JSON_URL is not set in config.")
                return False
            logger.info(f"Opening conversation JSON page: {url}")
            self.driver.get(url)
            time.sleep(3)  # Wait for page load
            logger.info("✓ Conversation JSON page loaded")
            return True
        except Exception as e:
            logger.error(f"Failed to open conversation JSON page: {e}", exc_info=True)
            return False
        
    def generate_conversation_json(self, chapter_content: str, story_name: str,
                                  story_id: int = None, chapter_number: int = None,
                                  timeout: int = None, save_to_file: bool = True) -> Optional[Dict[str, Any]]:
        """
        Quy trình hoàn chỉnh: gửi nội dung truyện, Grok tự tạo prompt và JSON, lưu file

        Args:
            chapter_content: Nội dung chapter truyện (Grok sẽ tự tạo prompt từ đây)
            story_name: Tên story (BẮT BUỘC)
            story_id: ID của story (optional, dùng cho tên file)
            chapter_number: Số thứ tự chapter (optional, dùng cho tên file)
            timeout: Thời gian chờ response (None = không giới hạn)
            save_to_file: Có lưu kết quả ra file không

        Returns:
            Dict chứa JSON data hoặc None nếu thất bại
        """
        try:
            # Ensure browser is started
            if not self.driver:
                if not self.start_browser():
                    return None
            
            # Open Grok if not already there
            if "grok" not in self.driver.current_url.lower():
                if not self.open_grok():
                    return None
            
            # Check login
            if not self.is_logged_in():
                logger.warning("⚠️ Not logged in to Grok.com")
                logger.info("Please login manually in the browser window...")
                logger.info("After logging in, press Enter to continue...")
                
                # Keep browser open for manual login
                input("Press Enter after logging in...")
                
                # Re-check login status
                if not self.is_logged_in():
                    logger.error("❌ Still not logged in to Grok.com")
                    return None
                
                logger.info("✓ Login verified successfully")
            
            # Go to conversation convert json page if configured
            if hasattr(config, 'CONVERSATION_JSON_URL') and config.CONVERSATION_JSON_URL:
                if not self.goto_conversation_json_page():
                    logger.warning("Failed to open conversation JSON page, continuing anyway...")
            
            # Send chapter content (Grok sẽ tự xử lý và tạo JSON)
            logger.info(f"📖 Sending chapter content ({len(chapter_content)} characters)...")
            if not self.send_prompt(chapter_content):
                return None
            
            # Wait for response (no timeout by default - wait indefinitely)
            logger.info("⏳ Waiting for Grok to process content and generate JSON...")
            logger.info("   (Grok is creating prompt and generating conversation JSON)")
            if not self.wait_for_response(timeout):
                logger.error("Failed to get response")
                return None
            
            # Extract JSON
            logger.info("📋 Extracting generated JSON...")
            json_data = self.extract_json_response()
            
            if not json_data:
                logger.error("Failed to extract JSON data")
                return None
            
            # Save to file if requested and info provided
            if save_to_file and story_id is not None and chapter_number is not None:
                # Convert JSON to string for saving
                if "raw_content" in json_data:
                    # Already raw text
                    content_to_save = json_data["raw_content"]
                else:
                    # Convert dict to JSON string
                    content_to_save = json.dumps(json_data, indent=2, ensure_ascii=False)
                
                saved_path = self.save_conversation_to_file(
                    content_to_save,
                    story_id,
                    chapter_number,
                    story_name
                )
                
                if saved_path:
                    logger.info(f"✓ Conversation saved to: {saved_path}")
                    # Add filepath to result
                    json_data["saved_filepath"] = saved_path
                else:
                    logger.warning("Failed to save conversation file")
            
            return json_data
            
        except Exception as e:
            logger.error(f"Failed to generate conversation JSON: {e}", exc_info=True)
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

