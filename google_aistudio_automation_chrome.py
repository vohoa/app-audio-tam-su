"""
Google AI Studio Generate Speech Automation using Selenium
Tự động hóa việc tạo audio từ https://aistudio.google.com/generate-speech
"""

import os
import time
import logging
import subprocess
import base64
from typing import Optional, Dict, Any

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# Undetected chromedriver for anti-bot
import undetected_chromedriver as uc

# Local imports
import config
from browser_fingerprint import ProfileFingerprintManager
from utils.delays import HumanDelay
from utils.input_handler import InputHandler
from proxy_manager import ProxyManager, ProxyData

# NOTE: pyperclip, random, Keys are now used inside utils modules
# NOTE: Timeouts, Selectors, Audio, Chrome constants will be used in future refactoring phases

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleAIStudioAutomation:
    """
    Automation class để tương tác với Google AI Studio Generate Speech
    """

    def __init__(self, headless: bool = False, download_path: str = None, use_profile: bool = True, profile_name: str = "aistudio", system_profile_path: str = None, auto_clear_data_on_startup: bool = True, extensions: list = None, auto_install_extensions: bool = False, use_proxy: bool = True, proxy_data: dict = None):
        """
        Khởi tạo automation instance - NORMAL MODE (không dùng debugging port)
        
        Args:
            headless: Chạy browser ở chế độ headless hay không
            download_path: Đường dẫn lưu file audio tải về
            use_profile: Có sử dụng browser profile để lưu session không
            profile_name: Tên profile để lưu (default: "aistudio")
            system_profile_path: Đường dẫn đến profile directory (default: ./chrome_profiles)
            auto_clear_data_on_startup: Tự động xóa dữ liệu duyệt khi khởi động (default: True)
            extensions: Danh sách đường dẫn extensions (.crx files) hoặc Chrome Web Store IDs để cài đặt
            auto_install_extensions: Tự động cài đặt extensions từ danh sách (default: False)
            use_proxy: Có sử dụng proxy hay không (default: False)
            proxy_data: Thông tin proxy dưới dạng dict {host, port, username, password, protocol}
        """
        
        print("⚙️ Initializing Google AI Studio Automation - NORMAL CHROME MODE")
        print(f"📁 use_profile: {profile_name}")
        print(f"👁️ headless_mode: {'Yes' if headless else 'No (UI visible)'}")
        print(f"🧹 auto_clear_data: {'Yes' if auto_clear_data_on_startup else 'No'}")
        print(f"🌐 use_proxy: {'Yes' if use_proxy else 'No'}")
        
        self.driver = None
        self.wait = None
        self.headless = headless
        self._session_invalid = False
        self.auto_clear_data_on_startup = auto_clear_data_on_startup
        
        # Proxy configuration
        self.use_proxy = True
        self.proxy_data = proxy_data
        self.proxy_manager = ProxyManager()
        
        # Extensions configuration
        self.extensions = extensions or []
        self.auto_install_extensions = auto_install_extensions
        self.installed_extensions = []
        
        # Sử dụng project root để tạo paths
        project_root = self._get_project_root()
        self.download_path = download_path or os.path.join(project_root, 'audio_downloads')
        
        # Tạo extensions directory
        self.extensions_path = os.path.join(project_root, 'chrome_extensions')
        if not os.path.exists(self.extensions_path):
            os.makedirs(self.extensions_path, exist_ok=True)
            logger.info(f"Đã tạo extensions directory: {self.extensions_path}")
        
        # Tạo download directory
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path, exist_ok=True)
            logger.info(f"Đã tạo download directory: {self.download_path}")
        
        self.use_profile = use_profile
        self.profile_name = profile_name
        
        # ⚠️ THAY ĐỔI QUAN TRỌNG: Tắt debugging mode
        self.use_debugging_port = False
        self.debugging_port = None  # Không dùng debugging port
        
        # Profile path setup
        self.system_profile_path = system_profile_path or os.path.join(project_root, 'chrome_profiles')
        self.profile_path = self._get_profile_path() if use_profile else None
        self.base_url = "https://aistudio.google.com/generate-speech"

        # Input handler will be initialized after driver setup
        self.input_handler = None
        
        # Chrome binary và ChromeDriver paths - Use config
        self.chrome_binary_path = config.get_chrome_binary_path()
        self.chromedriver_path = config.get_chrome_driver_path()
        
        # Log Chrome configuration
        logger.info(f"📋 Chrome Configuration:")
        logger.info(f"   Binary: {self.chrome_binary_path}")
        logger.info(f"   Driver: {self.chromedriver_path or 'Auto-managed'}")
        
        # 🔥 Kill all existing browser instances before starting
        logger.info("🧹 Killing all existing browser instances...")
        config.kill_browser_instances(self.chrome_binary_path, verbose=True)
        
        # # 🛡️ Browser Fingerprint Manager
        # self.fingerprint_manager = ProfileFingerprintManager(
        #     profiles_dir=self.system_profile_path,
        #     configs_dir=os.path.join(project_root, 'profile_configs')
        # )
        # logger.info("🛡️ Fingerprint Manager initialized")

        
    def _get_project_root(self) -> str:
        """
        Lấy đường dẫn project root cho local development
        
        Returns:
            str: Đường dẫn đến project root
        """
        # Method 2: Fallback to current working directory logic
        current_dir = os.getcwd()
        return current_dir
        
    def _get_proxy_url(self) -> str:
        """
        Get the proxy URL in the format required by Chrome
        
        Returns:
            str: Proxy URL in format protocol://username:password@host:port
        """
        if not self.proxy_data:
            return ""
            
        host = self.proxy_data.get("host", "")
        port = self.proxy_data.get("port", "")
        username = self.proxy_data.get("username", "")
        password = self.proxy_data.get("password", "")
        protocol = self.proxy_data.get("protocol", "http")
        
        if not host or not port:
            return ""
            
        if username and password:
            return f"{protocol}://{username}:{password}@{host}:{port}"
        else:
            return f"{protocol}://{host}:{port}"
        
    def _get_chrome_binary_path(self) -> str:
        """
        Lấy đường dẫn đến Chrome binary - Sử dụng config với auto-detect
        
        Returns:
            str: Đường dẫn đến Chrome binary
        """
        import config
        
        # Use config to get Chrome path (will auto-detect if not configured)
        chrome_binary = config.get_chrome_binary_path()
        
        # Fallback to project local if config returns empty
        if not chrome_binary:
            project_root = self._get_project_root()
            chrome_binary = os.path.join(project_root, 'chrome-linux64', 'chrome')
        
        logger.info(f"Chrome binary path: {chrome_binary}")
        
        # Log Chrome version
        chrome_version = config.get_chrome_version(chrome_binary)
        logger.info(f"Chrome version: {chrome_version}")
        
        return chrome_binary
    
    def _get_chromedriver_path(self) -> str:
        """
        Lấy đường dẫn đến ChromeDriver - Sử dụng config với auto-manage
        
        Returns:
            str: Đường dẫn đến ChromeDriver (hoặc empty string để auto-manage)
        """
        import config
        
        # Use config to get ChromeDriver path (will auto-detect or return empty for auto-manage)
        chromedriver = config.get_chrome_driver_path()
        
        # Fallback to project local if config returns empty
        if not chromedriver:
            project_root = self._get_project_root()
            chromedriver = os.path.join(project_root, 'chrome_driver', 'chromedriver')
        
        logger.info(f"ChromeDriver path: {chromedriver or 'Auto-managed'}")
        return chromedriver
    
    
    def _human_delay(self, min_seconds: float = None, max_seconds: float = None) -> None:
        """
        Thêm delay ngẫu nhiên để mô phỏng hành vi người thật
        [REFACTORED] Now uses HumanDelay utility class

        Args:
            min_seconds: Thời gian delay tối thiểu (default from constants)
            max_seconds: Thời gian delay tối đa (default from constants)
        """
        HumanDelay.standard(min_seconds, max_seconds)
    
    def _paste_text(self, element, text: str) -> None:
        """
        Paste text nhanh bằng clipboard thay vì typing từng ký tự
        [DEPRECATED] Use InputHandler instead
        [REFACTORED] Now delegates to InputHandler with 'fast' mode

        Args:
            element: Web element để paste text
            text: Text cần paste
        """
        if self.input_handler is None:
            self.input_handler = InputHandler(self.driver)

        success = self.input_handler.input_text(element, text, mode='fast')
        if not success:
            logger.error("❌ InputHandler failed - this should not happen")
            raise Exception("Failed to paste text using InputHandler")
    
    def _human_type(self, element, text: str, use_fast_paste: bool = True) -> None:
        """
        Nhập text với tùy chọn fast paste hoặc human typing
        [REFACTORED] Now uses InputHandler with mode selection

        Args:
            element: Web element để nhập text
            text: Text cần nhập
            use_fast_paste: True = dùng paste nhanh, False = typing như người thật
        """
        if self.input_handler is None:
            self.input_handler = InputHandler(self.driver)

        mode = 'fast' if use_fast_paste else 'human'
        success = self.input_handler.input_text(element, text, mode=mode)

        if not success:
            logger.error(f"❌ InputHandler failed with mode '{mode}'")
            raise Exception(f"Failed to input text using mode '{mode}'")
    
    def _human_type_old(self, element, text: str) -> None:
        """
        Nhập text với tốc độ như người thật (tốc độ chậm hơn, tự nhiên hơn)
        [DEPRECATED] Use _human_type() with use_fast_paste=False instead
        [REFACTORED] Now delegates to InputHandler

        Args:
            element: Web element để nhập text
            text: Text cần nhập
        """
        if self.input_handler is None:
            self.input_handler = InputHandler(self.driver)

        success = self.input_handler.input_text(element, text, mode='human')
        if not success:
            logger.error("❌ InputHandler (human mode) failed")
            raise Exception("Failed to input text using human typing mode")
    
    def _human_click(self, element) -> None:
        """
        Click với movement như người thật - PURE SELENIUM, NO JAVASCRIPT
        [REFACTORED] Now uses HumanDelay utility

        Args:
            element: Element cần click
        """
        try:
            # Ensure window focus trước khi thực hiện human-like interactions
            self._ensure_window_focus()

            # Scroll to element bằng ActionChains (không dùng JavaScript)
            actions = ActionChains(self.driver)
            actions.move_to_element(element).perform()
            HumanDelay.scroll()

            # Click bằng ActionChains
            actions = ActionChains(self.driver)
            actions.click(element).perform()
            HumanDelay.click()

        except Exception as e:
            logger.warning(f"⚠️ Lỗi trong _human_click với ActionChains: {str(e)}")
            # Fallback: Direct click (vẫn không dùng JavaScript)
            try:
                element.click()
                logger.info("✅ Fallback direct click thành công")
                HumanDelay.click()
            except Exception as direct_error:
                logger.error(f"❌ Direct click thất bại: {str(direct_error)}")
                raise

    def _scroll_to_element(self, element) -> None:
        """
        Scroll đến element bằng ActionChains - PURE SELENIUM, NO JAVASCRIPT
        [REFACTORED] Now uses HumanDelay utility

        Args:
            element: Element cần scroll đến
        """
        try:
            actions = ActionChains(self.driver)
            actions.move_to_element(element).perform()
            HumanDelay.scroll()
        except Exception as e:
            logger.warning(f"⚠️ Không thể scroll đến element: {str(e)}")

    def _ensure_window_focus(self) -> bool:
        """
        Đảm bảo automation window có focus để tránh mất thao tác khi user dùng màn hình khác
        
        Returns:
            bool: True nếu thành công hoặc không cần thiết
        """
        try:
            # Switch to current window handle để ensure focus
            current_handle = self.driver.current_window_handle
            self.driver.switch_to.window(current_handle)
            
            # Execute JavaScript để force focus window
            self.driver.execute_script("window.focus();")
            
            # Optional: Bring window to front (if supported)
            try:
                self.driver.execute_script("window.top.focus();")
            except:
                pass  # Some environments might not support this
                
            return True
            
        except Exception as e:
            logger.debug(f"Could not ensure window focus: {str(e)}")
            return False
        
    def _get_profile_path(self) -> str:
        """
        Lấy đường dẫn đến browser profile directory - chung cho cả Normal và Debugging mode
        
        Returns:
            str: Đường dẫn đến profile directory
        """
        # Sử dụng chrome_profiles folder chung trong project
        project_root = self._get_project_root()
        profile_path = os.path.join(project_root, 'chrome_profiles')
        
        # Tạo thư mục nếu chưa tồn tại
        if not os.path.exists(profile_path):
            os.makedirs(profile_path, exist_ok=True)
            logger.info(f"Đã tạo thư mục chrome_profiles: {profile_path}")
        
        # Tạo shared profile directory cho cả Normal và Debugging mode
        shared_profile_path = os.path.join(profile_path, self.profile_name)
        if not os.path.exists(shared_profile_path):
            os.makedirs(shared_profile_path, exist_ok=True)
            logger.info(f"Đã tạo shared profile: {shared_profile_path}")
        else:
            logger.info(f"♻️ Sử dụng shared profile có sẵn: {shared_profile_path}")
            
        logger.info(f"🔗 Profile được chia sẻ giữa Normal và Debugging mode: {shared_profile_path}")
        return profile_path
    
    def _is_logged_in(self) -> bool:
        """
        Kiểm tra xem đã đăng nhập Google chưa
        
        Returns:
            bool: True nếu đã đăng nhập, False nếu chưa
        """
        try:
            # Kiểm tra các indicator cho trạng thái đăng nhập
            login_indicators = [
                # Có avatar/profile button
                "[data-testid*='avatar']",
                "[aria-label*='Account']",
                ".profile-button",
                "[data-testid*='profile']",
                # Có text input field (dấu hiệu đã vào được app)
                "textarea",
                "[contenteditable='true']",
                "[role='textbox']"
            ]
            
            for selector in login_indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            # Nếu tìm thấy textarea/textbox, kiểm tra kỹ hơn
                            if selector in ["textarea", "[contenteditable='true']", "[role='textbox']"]:
                                # Đảm bảo không phải là sign-in form
                                if not self._is_signin_page():
                                    logger.info("Phát hiện đã đăng nhập - có text input field")
                                    return True
                            else:
                                logger.info(f"Phát hiện đã đăng nhập - tìm thấy {selector}")
                                return True
                except NoSuchElementException:
                    continue
            
            return False
            
        except WebDriverException as e:
            error_msg = str(e)
            if "invalid session id" in error_msg.lower() or "session" in error_msg.lower():
                logger.error(f"❌ Session bị mất kết nối: {error_msg}")
                logger.info("🔄 Attempting to reconnect driver...")
                # Đánh dấu cần restart driver
                self._session_invalid = True
                return False
            else:
                logger.error(f"Lỗi WebDriver khi kiểm tra trạng thái đăng nhập: {error_msg}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra trạng thái đăng nhập: {str(e)}")
            return False
    
    def _restart_driver_if_needed(self) -> bool:
        """
        Restart driver nếu session bị invalid
        
        Returns:
            bool: True nếu restart thành công, False nếu thất bại
        """
        if not self._session_invalid:
            return True
            
        logger.info("🔄 Restarting driver due to invalid session...")
        
        try:
            # Đóng driver cũ nếu còn tồn tại
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
                self.wait = None
            
            # Khởi động lại driver
            self.setup_driver()
            self._session_invalid = False
            logger.info("✅ Driver restarted successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to restart driver: {str(e)}")
            return False
    
    def _is_signin_page(self) -> bool:
        """
        Kiểm tra xem có đang ở trang sign-in không
        
        Returns:
            bool: True nếu đang ở trang sign-in
        """
        try:
            signin_indicators = [
                "input[type='email']",
                "input[type='password']", 
                "[data-testid*='signin']",
                "[data-testid*='login']",
                "button:contains('Sign in')",
                "button:contains('Next')"
            ]
            
            for selector in signin_indicators:
                try:
                    if ":contains" in selector:
                        # Sử dụng XPath cho text search
                        xpath = "//button[contains(text(), 'Sign in') or contains(text(), 'Next')]"
                        elements = self.driver.find_elements(By.XPATH, xpath)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        if element.is_displayed():
                            return True
                except NoSuchElementException:
                    continue
            
            return False
            
        except Exception:
            return False
        
    def _setup_chrome_driver(self) -> webdriver.Chrome:
        """
        Setup Chrome driver với undetected_chromedriver để bypass bot detection
        
        ⭐ PRIORITY: undetected_chromedriver > selenium_stealth
        
        undetected_chromedriver provides:
        - Auto-patched ChromeDriver to evade detection
        - Regular updates to counter new detection methods
        - Less manual configuration needed
        - Better success rate against Cloudflare, Recaptcha, etc.
        
        Returns:
            webdriver.Chrome: Undetected Chrome driver instance
        """
        try:
            logger.info("🚀 Using undetected_chromedriver for stealth mode...")
            
            # Configure undetected_chromedriver options
            uc_options = uc.ChromeOptions()
            
            # Basic stealth arguments
            uc_options.add_argument('--no-sandbox')
            uc_options.add_argument('--disable-dev-shm-usage')
            uc_options.add_argument('--disable-gpu')
            uc_options.add_argument('--start-maximized')
            
            # Headless mode if requested
            if self.headless:
                uc_options.add_argument('--headless=new')  # New headless mode
                logger.info("👻 Headless mode enabled")
            
            # Profile settings
            if self.use_profile and self.profile_path:
                user_data_dir = os.path.join(self.profile_path, self.profile_name)
                uc_options.add_argument(f'--user-data-dir={user_data_dir}')
                logger.info(f"📁 Using Chrome profile: {user_data_dir}")
            
            # Proxy settings if enabled
            if self.use_proxy and self.proxy_data:
                proxy_url = self._get_proxy_url()
                if proxy_url:
                    uc_options.add_argument(f'--proxy-server={proxy_url}')
                    logger.info(f"🌐 Using proxy: {proxy_url.split('://')[-1]}")
            
            # Preferences
            prefs = {
                'profile.default_content_setting_values.notifications': 2,
                'download.default_directory': self.download_path,
                'download.prompt_for_download': False,
                'profile.default_content_settings.popups': 0,
                'credentials_enable_service': False,
                'profile.password_manager_enabled': False,
            }
            uc_options.add_experimental_option('prefs', prefs)
            
            # Chrome binary path (if specified)
            if os.path.exists(self.chrome_binary_path):
                uc_options.binary_location = self.chrome_binary_path
                logger.info(f"🌐 Using Chrome binary: {self.chrome_binary_path}")
            
            # Create undetected Chrome driver
            driver = uc.Chrome(
                options=uc_options,
                driver_executable_path=self.chromedriver_path,
                version_main=142,  # Chỉ định version Chrome để tải đúng ChromeDriver
                use_subprocess=True,  # Better process management
            )
            
            logger.info("✅ undetected_chromedriver initialized successfully")
            logger.info("🔒 Bot detection bypass: ACTIVE (auto-patched ChromeDriver)")
            
            # Additional manual overrides (optional, undetected_chromedriver handles most)
            try:
                driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': '''
                        // Additional stealth (undetected_chromedriver already handles most)
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['en-US', 'en', 'vi-VN', 'vi']
                        });
                        
                        // Ensure window.chrome exists
                        if (!window.chrome) {
                            window.chrome = { runtime: {} };
                        }
                    '''
                })
                logger.info("✅ Additional stealth overrides applied")
            except Exception as override_error:
                logger.debug(f"Minor: Additional overrides failed: {override_error}")
            
            return driver
            
        except Exception as uc_error:
            logger.error(f"❌ undetected_chromedriver failed: {uc_error}")
            logger.warning("🔄 Falling back to standard Selenium WebDriver...")
            
            # Fallback to standard Selenium with manual stealth
            return self._setup_chrome_driver_fallback()
    
    def _setup_chrome_driver_fallback(self) -> webdriver.Chrome:
        """
        Fallback method using standard Selenium WebDriver with manual stealth
        Used when undetected_chromedriver fails
        
        Returns:
            webdriver.Chrome: Standard Chrome driver with manual stealth config
        """
        logger.info("🔄 Using fallback: standard Selenium with manual stealth...")
        
        options = Options()
        
        # Anti-detection options
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--start-maximized')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        # Profile settings
        if self.use_profile and self.profile_path:
            user_data_dir = os.path.join(self.profile_path, self.profile_name)
            options.add_argument(f'--user-data-dir={user_data_dir}')
            
        # Proxy settings if enabled
        if self.use_proxy and self.proxy_data:
            proxy_url = self._get_proxy_url()
            if proxy_url:
                options.add_argument(f'--proxy-server={proxy_url}')
                logger.info(f"🌐 Using proxy: {proxy_url.split('://')[-1]}")
        
        # Preferences
        prefs = {
            'profile.default_content_setting_values.notifications': 2,
            'download.default_directory': self.download_path,
            'download.prompt_for_download': False,
        }
        options.add_experimental_option('prefs', prefs)
        
        # Binary path
        if os.path.exists(self.chrome_binary_path):
            options.binary_location = self.chrome_binary_path
        
        # Create driver
        service = Service(self.chromedriver_path) if os.path.exists(self.chromedriver_path) else Service()
        driver = webdriver.Chrome(service=service, options=options)
        
        # Manual stealth overrides
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                window.chrome = { runtime: {} };
            '''
        })
        
        logger.info("✅ Fallback driver setup with manual stealth")
        return driver

    def _connect_to_chrome(self) -> webdriver.Chrome:
        """
        ⚠️ DEPRECATED: Use _setup_chrome_driver() instead for stealth mode
        
        This method does NOT include stealth configuration.
        Use _setup_chrome_driver() for proper bot detection bypass.
        
        Returns:
            webdriver.Chrome: Chrome driver instance (WITHOUT stealth)
        """
        logger.warning("⚠️ _connect_to_chrome() is deprecated. Use _setup_chrome_driver() for stealth mode.")
        
        # Redirect to _setup_chrome_driver() which has stealth enabled
        return self._setup_chrome_driver()


    def _get_random_proxy(self) -> Optional[ProxyData]:
        """
        Lấy ngẫu nhiên một proxy từ ProxyManager hoặc proxy_data

        Returns:
            Optional[ProxyData]: Proxy data hoặc None
        """
        # Nếu có proxy_data sẵn, convert sang ProxyData
        if self.proxy_data:
            if isinstance(self.proxy_data, ProxyData):
                logger.info(f"🌐 Using provided proxy: {self.proxy_data.host}:{self.proxy_data.port}")
                return self.proxy_data
            elif isinstance(self.proxy_data, dict):
                # Convert dict to ProxyData
                proxy = ProxyData.from_dict(self.proxy_data)
                logger.info(f"🌐 Using provided proxy: {proxy.host}:{proxy.port}")
                return proxy

        # Sử dụng ProxyManager để lấy random proxy
        if self.proxy_manager:
            # Nếu ProxyManager chưa có proxy, thử import từ CSV
            if self.proxy_manager.get_proxy_count() == 0:
                csv_file = os.path.join(self._get_project_root(), 'proxy_ipv6.csv')
                if os.path.exists(csv_file):
                    logger.info(f"📥 Importing proxies from {csv_file}")
                    success, error = self.proxy_manager.import_from_csv(csv_file)
                    logger.info(f"✅ Imported {success} proxies, {error} errors")

            # Lấy random proxy
            proxy = self.proxy_manager.get_random_proxy()
            if proxy:
                return proxy

        logger.warning("⚠️ No proxy available")
        return None

    def setup_driver(self) -> bool:
        """
        Setup undetected-chromedriver
        Hiệu quả 90%+ với Google login

        Returns:
            bool: True nếu setup thành công, False nếu thất bại
        """
        max_retries = 2

        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    logger.info(f"� Retry setup driver (Attempt {attempt}/{max_retries})")
                else:
                    logger.info("�🚀 Setting up undetected-chromedriver...")

                # Chrome options
                options = uc.ChromeOptions()

                # Window settings
                if not self.headless:
                    options.add_argument('--start-maximized')
                    options.add_argument('--window-size=1920,1080')

                # 🛡️ Enable Performance Logging để monitor network requests (detect 403)
                options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

                # ⚠️ CRITICAL: undetected_chromedriver has issues with user-data-dir
                # Use user_data_dir parameter in uc.Chrome() instead of options
                user_data_dir_path = None
                if self.use_profile:
                    user_data_dir_path = os.path.join(self.profile_path, self.profile_name)
                    logger.info(f"📁 Using profile: {user_data_dir_path}")
                    # Ensure profile directory exists
                    os.makedirs(user_data_dir_path, exist_ok=True)

                # 🌐 Proxy configuration - Random proxy mỗi lần setup
                if self.use_proxy:
                    proxy = self._get_random_proxy()
                    if proxy:
                        protocol = proxy.protocol.lower() if proxy.protocol else 'http'

                        # ✅ SOCKS5 - Best choice, no SSL issues
                        # No authentication needed - security via IP whitelist on VPS
                        if protocol in ['socks5', 'socks']:
                            logger.info(f"🌐 Configuring SOCKS5 proxy: {proxy.host}:{proxy.port}")

                            # SOCKS5 without authentication (IP whitelist on server)
                            options.add_argument(f'--proxy-server=socks5://{proxy.host}:{proxy.port}')
                            logger.info(f"✅ SOCKS5 proxy configured: {proxy.host}:{proxy.port}")
                            logger.info(f"🔒 Security: IP whitelist on VPS (no password needed)")

                            # SOCKS5 handles DNS automatically - no special flags needed
                            logger.info("✅ SOCKS5: No SSL bypass needed - Full HTTPS support")

                        # ⚠️ HTTP/HTTPS - Requires SSL bypass
                        elif protocol in ['http', 'https']:
                            logger.info(f"🌐 Configuring HTTP proxy: {proxy.host}:{proxy.port}")

                            if proxy.username and proxy.password:
                                # HTTP with auth - use extension
                                from create_proxy_auth_extension import create_proxy_auth_extension
                                extension_path = create_proxy_auth_extension(
                                    proxy_host=proxy.host,
                                    proxy_port=proxy.port,
                                    proxy_username=proxy.username,
                                    proxy_password=proxy.password,
                                    output_dir=os.path.join(self._get_project_root(), 'chrome_extensions'),
                                    protocol='http'
                                )
                                options.add_argument(f'--load-extension={extension_path}')
                                logger.info(f"✅ HTTP auth extension loaded")
                            else:
                                # HTTP without auth
                                options.add_argument(f'--proxy-server={protocol}://{proxy.host}:{proxy.port}')

                            # Fix SSL issues for HTTP proxy
                            options.add_argument('--ignore-certificate-errors')
                            options.add_argument('--ignore-ssl-errors')
                            options.add_argument('--allow-insecure-localhost')
                            logger.warning("⚠️ HTTP proxy: SSL bypass enabled")

                        else:
                            logger.warning(f"⚠️ Unknown proxy protocol: {protocol}, defaulting to HTTP")
                            options.add_argument(f'--proxy-server=http://{proxy.host}:{proxy.port}')
                    else:
                        logger.warning("⚠️ Proxy enabled but no proxy available, continuing without proxy")

                # Download and security settings
                prefs = {
                    'download.default_directory': self.download_path,
                    'download.prompt_for_download': False,
                    'download.directory_upgrade': True,
                    'safebrowsing.enabled': False,
                    'profile.default_content_setting_values.notifications': 2,
                    'credentials_enable_service': False,
                    'profile.password_manager_enabled': False,
                }
                options.add_argument(f'--user-data-dir={user_data_dir_path}')
                options.add_experimental_option('prefs', prefs)
                
                # ⭐ Tạo driver với undetected-chromedriver
                # Use user_data_dir parameter for better compatibility
                self.driver = uc.Chrome(
                    options=options,
                    headless=self.headless,
                    use_subprocess=False,  # Tăng stability
                    version_main=142,  # Chỉ định version Chrome để tải đúng ChromeDriver
                    browser_executable_path=self.chrome_binary_path,
                )
                
                # Set implicit wait
                self.driver.implicitly_wait(10)
                
                # WebDriverWait
                self.wait = WebDriverWait(self.driver, 30)
                
                # logger.info("🛡️ Applying browser fingerprint...")
                # try:
                #     fingerprint = self.fingerprint_manager.get_or_create_fingerprint(
                #         profile_name=self.profile_name,
                #         timezone="Asia/Ho_Chi_Minh"  # Default timezone, có thể customize
                #     )
                    
                #     self.fingerprint_manager.apply_fingerprint_to_driver(
                #         self.driver, 
                #         fingerprint
                #     )
                #     logger.info("✅ Browser fingerprint applied successfully")
                # except Exception as fp_error:
                #     logger.warning(f"⚠️ Failed to apply fingerprint: {fp_error}")
                #     logger.info("ℹ️ Continuing without fingerprint (basic stealth still active)")
                
                logger.info("✅ Driver setup thành công")
                logger.info(f"🌐 Chrome version: {self.driver.capabilities.get('browserVersion', 'Unknown')}")
                logger.info(f"🔧 ChromeDriver version: {self.driver.capabilities.get('chrome', {}).get('chromedriverVersion', 'Unknown')}")

                # Initialize InputHandler after driver is ready
                self.input_handler = InputHandler(self.driver)
                logger.info("✅ InputHandler initialized")

                return True
                
            except Exception as e:
                error_msg = str(e).lower()
                logger.error(f"❌ Lỗi setup driver (Attempt {attempt}/{max_retries}): {e}")
                
                # Kiểm tra nếu là lỗi "cannot connect to chrome"
                if any(keyword in error_msg for keyword in ['cannot connect to chrome', 'chrome not reachable', 'session not created']):
                    logger.warning("🔧 Phát hiện lỗi 'cannot connect to chrome' - Cleanup profile và kill processes...")
                    
                    # Cleanup profile và kill processes
                    cleanup_success = self._cleanup_profile_and_processes(user_data_dir_path if self.use_profile else None)
                    
                    if cleanup_success and attempt < max_retries:
                        logger.info("✅ Cleanup thành công, đợi 3s trước khi retry...")
                        time.sleep(3)
                        continue
                    elif not cleanup_success:
                        logger.error("❌ Cleanup thất bại")
                        return False
                
                # Nếu là lần cuối hoặc lỗi khác
                if attempt >= max_retries:
                    logger.error(f"❌ Setup driver thất bại sau {max_retries} lần thử")
                    return False
                else:
                    # Đợi trước khi retry
                    logger.info("⏳ Đợi 2s trước khi retry...")
                    time.sleep(2)
        
        return False
    
    def _cleanup_profile_and_processes(self, profile_path: str = None) -> bool:
        """
        Cleanup profile và kill tất cả browser processes khi gặp lỗi "cannot connect to chrome"
        
        Args:
            profile_path: Đường dẫn đến profile directory cần cleanup
            
        Returns:
            bool: True nếu cleanup thành công
        """
        try:
            logger.info("🧹 Bắt đầu cleanup profile và browser processes...")
            
            # BƯỚC 1: Kill tất cả browser processes (Chrome, Brave, Chromium)
            killed_count = 0
            browser_names = ['chromium', 'brave', 'chromedriver']
            
            try:
                import psutil
                
                logger.info("🔪 Killing browser processes...")
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        proc_name = proc.info['name']
                        if proc_name and any(browser in proc_name.lower() for browser in browser_names):
                            # Kiểm tra nếu process liên quan đến profile
                            if profile_path:
                                cmdline = proc.info.get('cmdline', [])
                                if cmdline and any(profile_path in str(arg) for arg in cmdline):
                                    logger.info(f"🔪 Killing {proc_name} (PID: {proc.info['pid']}) - Using profile")
                                    proc.kill()
                                    proc.wait(timeout=3)
                                    killed_count += 1
                            else:
                                # Nếu không có profile cụ thể, kill tất cả browser processes
                                logger.info(f"🔪 Killing {proc_name} (PID: {proc.info['pid']})")
                                proc.kill()
                                proc.wait(timeout=3)
                                killed_count += 1
                                
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired) as proc_error:
                        logger.debug(f"Process kill failed: {proc_error}")
                        continue
                
                logger.info(f"✅ Killed {killed_count} browser process(es)")
                
                # Đợi processes cleanup hoàn toàn
                if killed_count > 0:
                    logger.info("⏳ Đợi 2s để processes cleanup hoàn toàn...")
                    time.sleep(2)
                    
            except ImportError:
                logger.warning("⚠️ psutil not available, trying alternative method...")
                # Fallback: Use system commands
                try:
                    import subprocess
                    import platform
                    
                    if platform.system() == "Linux":
                        # Kill Chrome/Brave/Chromium processes on Linux
                        for browser in ['chrome', 'brave', 'chromium']:
                            try:
                                subprocess.run(['pkill', '-9', browser], check=False, capture_output=True)
                                logger.info(f"✅ Killed {browser} processes via pkill")
                            except Exception as pkill_error:
                                logger.debug(f"pkill {browser} failed: {pkill_error}")
                        killed_count = 1  # Mark as attempted
                        time.sleep(2)
                except Exception as fallback_error:
                    logger.warning(f"⚠️ Fallback kill method failed: {fallback_error}")
            
            # BƯỚC 2: Clear cache trong profile (GIỮ COOKIES)
            if profile_path and os.path.exists(profile_path):
                logger.info(f"🗑️ Clearing cache in profile: {profile_path}")
                
                # Các thư mục/file cần xóa (KHÔNG BAO GỒM Cookies)
                cache_items = [
                    'Cache',
                    'Code Cache',
                    'GPUCache', 
                    'Service Worker',
                    'Local Storage',
                    'Session Storage',
                    'IndexedDB',
                    'blob_storage',
                    'File System',
                    'Platform Notifications',
                    'Service Worker/CacheStorage',
                    'Service Worker/ScriptCache',
                    'Visited Links',
                    'Web Data',
                    'Favicons',
                    'History',
                    'History-journal',
                    'Top Sites',
                    'Top Sites-journal',
                ]
                
                deleted_count = 0
                for item in cache_items:
                    item_path = os.path.join(profile_path, item)
                    if os.path.exists(item_path):
                        try:
                            import shutil
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path, ignore_errors=True)
                            else:
                                os.remove(item_path)
                            deleted_count += 1
                            logger.debug(f"✅ Deleted: {item}")
                        except Exception as delete_error:
                            logger.debug(f"⚠️ Cannot delete {item}: {delete_error}")
                
                logger.info(f"✅ Cleared {deleted_count} cache items (KEPT Cookies for login)")
                
                # Xóa lock files
                lock_files = ['SingletonLock', 'SingletonCookie', 'SingletonSocket']
                for lock_file in lock_files:
                    lock_path = os.path.join(profile_path, lock_file)
                    if os.path.exists(lock_path):
                        try:
                            os.remove(lock_path)
                            logger.debug(f"✅ Removed lock: {lock_file}")
                        except Exception as lock_error:
                            logger.debug(f"⚠️ Cannot remove lock {lock_file}: {lock_error}")
                
                logger.info("✅ Removed profile lock files")
            else:
                logger.info("ℹ️ No profile path specified or not exists, skipping cache cleanup")
            
            logger.info("✅ Cleanup profile và processes hoàn tất")
            return True
            
        except Exception as e:
            logger.error(f"❌ Lỗi trong cleanup_profile_and_processes: {str(e)}")
            return False
    
    def _get_installed_extensions(self) -> list:
        """
        Lấy danh sách extensions hiện tại đã cài đặt trong Chrome
        
        Returns:
            list: Danh sách thông tin extensions đã cài đặt
        """
        installed_extensions = []
        
        try:
            logger.debug("🔍 Đang kiểm tra extensions đã cài đặt trong Chrome...")
            
            # Navigate to chrome://extensions/ để lấy thông tin extensions
            current_url = self.driver.current_url
            self.driver.get("chrome://extensions/")
            time.sleep(2)
            
            # Method 1: Sử dụng JavaScript để lấy thông tin extensions
            try:
                extensions_script = '''
                    // Tìm extension manager element
                    const extensionsManager = document.querySelector('extensions-manager');
                    if (!extensionsManager || !extensionsManager.shadowRoot) {
                        return [];
                    }
                    
                    // Tìm tất cả extension items
                    const extensionItems = extensionsManager.shadowRoot.querySelectorAll('extensions-item');
                    const extensions = [];
                    
                    extensionItems.forEach(item => {
                        try {
                            const id = item.getAttribute('id') || '';
                            const shadowRoot = item.shadowRoot;
                            if (shadowRoot) {
                                const nameElement = shadowRoot.querySelector('#name');
                                const name = nameElement ? nameElement.textContent.trim() : '';
                                const versionElement = shadowRoot.querySelector('.version');
                                const version = versionElement ? versionElement.textContent.trim() : '';
                                const enabledElement = shadowRoot.querySelector('#enableToggle');
                                const enabled = enabledElement ? enabledElement.checked : false;
                                
                                if (id && name) {
                                    extensions.push({
                                        id: id,
                                        name: name,
                                        version: version,
                                        enabled: enabled
                                    });
                                }
                            }
                        } catch (e) {
                            console.error('Error processing extension item:', e);
                        }
                    });
                    
                    return extensions;
                '''
                
                extensions_data = self.driver.execute_script(extensions_script)
                
                if extensions_data and isinstance(extensions_data, list):
                    installed_extensions = extensions_data
                    logger.debug(f"✅ Tìm thấy {len(installed_extensions)} extensions qua JavaScript")
                else:
                    logger.debug("⚠️ Không lấy được extensions qua JavaScript")
                    
            except Exception as js_error:
                logger.debug(f"⚠️ JavaScript method failed: {js_error}")
            
            # Method 2: Fallback - Parse page source để tìm extension IDs
            if not installed_extensions:
                try:
                    page_source = self.driver.page_source
                    
                    # Tìm các extension IDs trong page source (32 ký tự hex)
                    import re
                    extension_id_pattern = r'[a-z]{32}'
                    found_ids = re.findall(extension_id_pattern, page_source)
                    
                    # Filter unique IDs và tạo basic info
                    unique_ids = list(set(found_ids))
                    for ext_id in unique_ids:
                        installed_extensions.append({
                            'id': ext_id,
                            'name': f'Extension_{ext_id[:8]}...',
                            'version': 'Unknown',
                            'enabled': True  # Assume enabled
                        })
                    
                    logger.debug(f"✅ Fallback method tìm thấy {len(installed_extensions)} extension IDs")
                    
                except Exception as fallback_error:
                    logger.debug(f"⚠️ Fallback method failed: {fallback_error}")
            
            # Navigate back to original URL
            if current_url and current_url != "chrome://extensions/":
                self.driver.get(current_url)
                time.sleep(1)
            
            logger.debug(f"📋 Tổng cộng tìm thấy {len(installed_extensions)} extensions")
            return installed_extensions
            
        except Exception as e:
            logger.warning(f"❌ Lỗi khi lấy danh sách extensions: {str(e)}")
            return []
    
    def _is_extension_installed(self, extension_id: str) -> bool:
        """
        Kiểm tra xem một extension cụ thể đã được cài đặt chưa
        
        Args:
            extension_id: ID của extension cần kiểm tra
            
        Returns:
            bool: True nếu extension đã được cài đặt
        """
        try:
            if not extension_id or len(extension_id) != 32:
                return False
                
            logger.debug(f"🔍 Kiểm tra extension đã cài đặt: {extension_id}")
            
            # Method 1: Quick check via JavaScript
            try:
                check_script = f'''
                    // Quick check trong chrome://extensions/
                    return document.body.innerHTML.includes('{extension_id}');
                '''
                
                current_url = self.driver.current_url
                
                # Navigate to extensions page if not already there
                if current_url != "chrome://extensions/":
                    self.driver.get("chrome://extensions/")
                    time.sleep(2)
                
                result = self.driver.execute_script(check_script)
                
                # Navigate back if needed
                if current_url != "chrome://extensions/" and current_url:
                    self.driver.get(current_url)
                    time.sleep(1)
                
                if result:
                    logger.debug(f"✅ Extension {extension_id} đã được cài đặt")
                    return True
                else:
                    logger.debug(f"❌ Extension {extension_id} chưa được cài đặt")
                    return False
                    
            except Exception as js_error:
                logger.debug(f"⚠️ Quick check failed: {js_error}")
                
                # Method 2: Fallback - sử dụng _get_installed_extensions
                installed_extensions = self._get_installed_extensions()
                for ext in installed_extensions:
                    if ext.get('id') == extension_id:
                        logger.debug(f"✅ Extension {extension_id} found via fallback method")
                        return True
                
                logger.debug(f"❌ Extension {extension_id} not found via fallback method")
                return False
                
        except Exception as e:
            logger.warning(f"❌ Lỗi khi kiểm tra extension {extension_id}: {str(e)}")
            return False
    
    def _handle_autosave_popup(self) -> bool:
        """
        Xử lý popup "Auto-save is now enabled by default" của Google AI Studio
        Popup có thể xuất hiện chậm, cần check nhiều lần
        
        Returns:
            bool: True nếu đã xử lý popup hoặc không có popup, False nếu lỗi
        """
        try:
            logger.info("🔍 Checking for auto-save popup (max 3 seconds)...")
            
            # Selectors for the popup
            popup_selectors = [
                "mat-dialog-container",
                "ms-autosave-enabled-by-default-dialog",
                ".mat-mdc-dialog-container"
            ]
            
            # ⚡ OPTIMIZED: Wait up to 3 seconds for popup to appear
            # If no popup after 3s, safe to skip this step
            max_wait_time = 3  # seconds
            check_interval = 0.5  # check every 500ms
            checks = int(max_wait_time / check_interval)
            
            popup_found = False
            popup_element = None
            
            for check in range(checks):
                # Check if popup exists
                for selector in popup_selectors:
                    try:
                        popup = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if popup.is_displayed():
                            logger.info(f"✓ Found auto-save popup with selector: {selector} (after {check * check_interval:.1f}s)")
                            popup_found = True
                            popup_element = popup
                            break
                    except NoSuchElementException:
                        continue
                
                if popup_found:
                    break
                
                # Wait before next check
                time.sleep(check_interval)
            
            if not popup_found:
                logger.info("✓ No auto-save popup appeared after 3 seconds, continuing...")
                return True
            
            # Find and click "Got it" button
            button_selectors = [
                "//button[contains(text(), 'Got it')]",
                "button.ms-button-primary",
                "mat-dialog-actions button",
                "button[type='button']"
            ]
            
            button_clicked = False
            for selector in button_selectors:
                try:
                    if selector.startswith("//"):
                        # XPath selector
                        button = self.driver.find_element(By.XPATH, selector)
                    else:
                        # CSS selector
                        button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if button.is_displayed():
                        logger.info(f"✓ Found 'Got it' button with selector: {selector}")
                        
                        # Try normal click first
                        try:
                            button.click()
                            logger.info("✓ Clicked 'Got it' button (normal click)")
                            button_clicked = True
                            break
                        except Exception as click_error:
                            logger.debug(f"Normal click failed: {click_error}, trying JavaScript...")
                            try:
                                self.driver.execute_script("arguments[0].click();", button)
                                logger.info("✓ Clicked 'Got it' button (JavaScript click)")
                                button_clicked = True
                                break
                            except Exception as js_error:
                                logger.debug(f"JavaScript click failed: {js_error}")
                                continue
                        
                except NoSuchElementException:
                    continue
            
            if not button_clicked:
                logger.warning("⚠️ Could not find or click 'Got it' button, trying ESC key...")
                # Try to close popup by pressing ESC
                try:
                    from selenium.webdriver.common.keys import Keys
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    body.send_keys(Keys.ESCAPE)
                    logger.info("✓ Sent ESC key to close popup")
                    time.sleep(0.5)
                except Exception as esc_error:
                    logger.debug(f"ESC key failed: {esc_error}")
            
            # ⚡ OPTIMIZED: Quick verify popup is closed (max 1s)
            # Don't wait long - if button clicked, popup should close immediately
            time.sleep(0.5)
            
            # Verify popup is closed with quick check
            try:
                # Set implicit wait to 0 for this check to avoid hanging
                original_implicit_wait = self.driver.timeouts.implicit_wait
                self.driver.implicitly_wait(0)
                
                popup = self.driver.find_element(By.CSS_SELECTOR, "mat-dialog-container")
                if popup.is_displayed():
                    logger.warning("⚠️ Popup still visible after closing attempt")
                    self.driver.implicitly_wait(original_implicit_wait)
                    return True  # Don't fail - continue anyway
                    
                self.driver.implicitly_wait(original_implicit_wait)
            except NoSuchElementException:
                logger.info("✓ Auto-save popup closed successfully")
            
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Error handling auto-save popup: {e}")
            # Don't fail the entire flow if popup handling fails
            return True
    
    
    def navigate_to_generate_speech(self) -> bool:
        """
        Điều hướng đến trang Generate Speech với human-like behavior và advanced error handling
        
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"🔄 Attempt {attempt + 1}/{max_retries} to navigate...")
                
                logger.info(f"Đang điều hướng đến {self.base_url}")
                
                # 🚨 CRITICAL: Check if driver exists first
                if not self.driver:
                    logger.warning("❌ Driver is None, setting up new driver...")
                    try:
                        self.setup_driver()
                        if not self.driver:
                            logger.error("❌ Driver setup failed, driver still None")
                            if attempt < max_retries - 1:
                                time.sleep(2)
                                continue
                            else:
                                return False
                    except Exception as setup_error:
                        logger.error(f"❌ Exception during driver setup: {setup_error}")
                        if attempt < max_retries - 1:
                            time.sleep(2)
                            continue
                        else:
                            return False
                
                # Kiểm tra session validity chỉ khi driver đã tồn tại
                if not self._check_session_validity():
                    logger.warning("❌ Session invalid, attempting recovery...")
                    if not self._recover_session():
                        logger.error("❌ Session recovery failed")
                        if attempt < max_retries - 1:
                            continue
                        else:
                            return False
                
                # Đầu tiên vào Google.com để thiết lập session như người thật
                logger.info("Thiết lập Google session...")
                self.driver.get("https://www.google.com")
                self._human_delay(2, 4)  # Đợi như người thật
                
                # Sau đó mới vào AI Studio
                logger.info("Navigating to AI Studio...")
                self.driver.get(self.base_url)
                # Đợi trang tải xong với human delay
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                
                                # Sau đó mới vào AI Studio
                logger.info("Navigating to AI Studio...")
                self.driver.get(self.base_url)
                # Đợi trang tải xong với human delay
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                                # Sau đó mới vào AI Studio
                logger.info("Navigating to AI Studio...")
                self.driver.get(self.base_url)
                # Đợi trang tải xong với human delay
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                
                # # 🔥 CRITICAL: Handle auto-save popup if it appears
                # if self._handle_autosave_popup():
                #     logger.info("✅ Auto-save popup handled (if appeared)")
                
                # Kiểm tra xem có bị redirect đến login không
                current_url = self.driver.current_url
                if "accounts.google.com" in current_url:
                    logger.info("Đã được redirect đến trang đăng nhập Google")
                
                logger.info("✅ Đã điều hướng thành công đến trang Generate Speech")
                return True
                
            except TimeoutException as timeout_error:
                logger.error(f"⏰ Timeout khi tải trang Generate Speech (attempt {attempt + 1}): {str(timeout_error)}")
                if attempt < max_retries - 1:
                    logger.info("🔄 Retrying navigation after timeout...")
                    self._human_delay(2, 4)
                    continue
                else:
                    return False
                    
            except WebDriverException as webdriver_error:
                error_msg = str(webdriver_error).lower()
                
                # Handle specific WebDriver errors
                if any(keyword in error_msg for keyword in ['invalid session id', 'session deleted', 'chrome not reachable', 'disconnected']):
                    logger.error(f"🔌 Chrome session lost (attempt {attempt + 1}): {str(webdriver_error)}")
                    
                    # Force new driver setup
                    logger.info("🔧 Emergency driver setup...")
                    self.setup_driver()
                    logger.info("✅ Emergency restart successful, continuing...")
                    continue
                        
                elif 'target window already closed' in error_msg:
                    logger.error(f"🪟 Browser window closed (attempt {attempt + 1}): {str(webdriver_error)}")
                    if attempt < max_retries - 1:
                        logger.info("🔄 Attempting to restart browser...")
                        try:
                            self.setup_driver()
                            continue
                        except Exception as restart_error:
                            logger.error(f"❌ Browser restart failed: {str(restart_error)}")
                            continue
                    else:
                        return False
                        
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Unexpected error during navigation (attempt {attempt + 1}): {error_msg}")
                return False
        
        logger.error(f"❌ Navigation failed after {max_retries} attempts")
        return False
    
    def check_and_handle_auth_error(self) -> bool:
        """
        Kiểm tra và xử lý authentication error một cách chi tiết
        
        Returns:
            bool: True nếu không có error hoặc đã xử lý thành công
        """
        try:
            # Kiểm tra authentication error
            page_text = self.driver.page_source.lower()
            current_url = self.driver.current_url
            
            # Expanded error detection patterns
            error_patterns = [
                "failed to list models: authentication error",
                "failed to list models",
                "authentication error", 
                "please try again",
                "access denied",
                "unauthorized",
                "you don't have access",
                "sign in required",
                "login required"
            ]
            
            # Check for specific error messages
            detected_errors = []
            for pattern in error_patterns:
                if pattern in page_text:
                    detected_errors.append(pattern)
            
            if detected_errors:
                logger.warning("⚠️ Phát hiện authentication errors:")
                for error in detected_errors:
                    logger.warning(f"   • {error}")
                
                logger.info("🔧 Đang thử các giải pháp...")
                
                # Solution 1: Check if we're on wrong page
                if "accounts.google.com" in current_url:
                    logger.info("1. Đang ở trang Google login - redirect...")
                    self.driver.get(self.base_url)
                    time.sleep(5)
                    return self.check_and_handle_auth_error()  # Recursive check
                
                # Solution 2: Reload page
                logger.info("2. Thử reload trang...")
                self.driver.refresh()
                time.sleep(5)
                
                # Check again after reload
                page_text_after_reload = self.driver.page_source.lower()
                errors_after_reload = [p for p in error_patterns if p in page_text_after_reload]
                
                if not errors_after_reload:
                    logger.info("✅ Reload trang thành công!")
                    return True
                
                # Solution 3: MakerSuite workaround
                logger.info("3. Thử MakerSuite workaround...")
                makersuite_success = self._try_makersuite_workaround()
                
                if makersuite_success:
                    return True
                
                # Solution 4: Detailed error analysis and user guidance
                logger.warning("4. Cần intervention thủ công...")
                self._provide_detailed_auth_guidance(detected_errors)
                
                return False
            
            # Additional checks for page state
            if self._is_page_functional():
                logger.info("✅ Trang hoạt động bình thường")
                return True
            else:
                logger.warning("⚠️ Trang có vấn đề - có thể cần authentication")
                return False
            
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra auth error: {str(e)}")
            return False
    
    def _is_page_functional(self) -> bool:
        """
        Kiểm tra xem trang có hoạt động bình thường không
        
        Returns:
            bool: True nếu trang functional
        """
        try:
            # Look for functional elements
            functional_indicators = [
                "textarea",
                "[contenteditable='true']",
                "[role='textbox']",
                "button[aria-label*='Generate']"
            ]
            
            for selector in functional_indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            return True
                except NoSuchElementException:
                    continue
            
            return False
            
        except Exception:
            return False
    
    def _provide_detailed_auth_guidance(self, detected_errors: list) -> None:
        """
        Cung cấp hướng dẫn chi tiết dựa trên lỗi phát hiện được
        
        Args:
            detected_errors: List các lỗi đã phát hiện
        """
        logger.info("=" * 60)
        logger.error("🚨 AUTHENTICATION ERROR DETECTED!")
        logger.info("=" * 60)
        
        # Primary error
        if "failed to list models" in str(detected_errors):
            logger.info("🎯 Lỗi chính: 'Failed to list models: authentication error'")
            logger.info("💡 Nguyên nhân: Tài khoản Google chưa được kích hoạt cho AI Studio")
        
        logger.info("\n🔧 GIẢI PHÁP BƯỚC 1: Setup MakerSuite Account")
        logger.info("   1. Mở browser thường (không automation)")
        logger.info("   2. Vào: https://makersuite.google.com/")
        logger.info("   3. Đăng nhập với CÙNG tài khoản Google")
        logger.info("   4. Accept Terms of Service")
        logger.info("   5. Complete account setup")
        
        logger.info("\n🔧 GIẢI PHÁP BƯỚC 2: Verify AI Studio Access")
        logger.info("   1. Vào: https://aistudio.google.com/")
        logger.info("   2. Kiểm tra không còn 'Failed to list models'")
        logger.info("   3. Có thể tạo text input và generate button")
        
        logger.info("\n🔧 GIẢI PHÁP BƯỚC 3: Alternative Actions")
        logger.info("   • Thử tài khoản Google khác")
        logger.info("   • Clear browser cache/cookies")
        logger.info("   • Đợi 30-60 phút cho activation")
        logger.info("   • Verify phone number nếu được yêu cầu")
        
        logger.info("\n📞 SUPPORT:")
        logger.info("   • Chạy: python fix_auth_error.py")
        logger.info("   • Hoặc: python quick_start.py")
        logger.info("=" * 60)
    
    def _try_makersuite_workaround(self) -> bool:
        """
        Thử workaround qua MakerSuite
        
        Returns:
            bool: True nếu thành công
        """
        try:
            # Navigate đến MakerSuite trước
            logger.info("Đang navigate đến MakerSuite...")
            self.driver.get("https://makersuite.google.com/")
            time.sleep(5)
            
            # Thử tìm và click vào "Get started" hoặc tương tự
            get_started_selectors = [
                "//button[contains(text(), 'Get started')]",
                "//button[contains(text(), 'Continue')]",
                "//button[contains(text(), 'Try it')]",
                "//a[contains(text(), 'Generate speech')]",
                "//a[contains(@href, 'generate-speech')]"
            ]
            
            for xpath in get_started_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            logger.info(f"Found and clicking: {element.text[:50]}")
                            self.driver.execute_script("arguments[0].click();", element)
                            time.sleep(3)
                            break
                except NoSuchElementException:
                    continue
            
            # Thử navigate trực tiếp đến generate speech
            logger.info("Navigate trực tiếp đến generate speech...")
            self.driver.get(self.base_url)
            time.sleep(5)
            
            # Kiểm tra xem còn error không
            page_text = self.driver.page_source.lower()
            error_messages = [
                "failed to list models: authentication error",
                "authentication error"
            ]
            
            has_error = any(msg in page_text for msg in error_messages)
            
            if not has_error:
                logger.info("✅ MakerSuite workaround thành công!")
                return True
            else:
                logger.warning("❌ Vẫn còn authentication error")
                
                # Last resort: Hướng dẫn user
                logger.info("🔧 Vui lòng thực hiện manual setup:")
                logger.info("1. Đăng nhập https://makersuite.google.com/")
                logger.info("2. Accept terms of service")
                logger.info("3. Sau đó quay lại automation")
                
                return False
                
        except Exception as e:
            logger.error(f"Lỗi trong MakerSuite workaround: {str(e)}")
            return False
    
    def handle_google_signin_security(self) -> bool:
        """
        Handle Google security warnings và signin issues
        
        Returns:
            bool: True nếu handled successfully
        """
        try:
            current_url = self.driver.current_url
            page_content = self.driver.page_source.lower()
            
            # Check for common security warnings
            security_indicators = [
                "this browser or app may not be secure",
                "couldn't sign you in",
                "browser or app may not be secure",
                "try using a different browser"
            ]
            
            for indicator in security_indicators:
                if indicator in page_content:
                    logger.warning(f"Phát hiện Google security warning: {indicator}")
                    
                    # Try to find and click "Advanced" or "Continue anyway" buttons
                    try_continue_selectors = [
                        "//button[contains(text(), 'Advanced')]",
                        "//a[contains(text(), 'Continue')]",
                        "//button[contains(text(), 'Continue')]",
                        "//a[contains(text(), 'Try again')]",
                        "#advanced-button",
                        "[data-testid='advanced-button']"
                    ]
                    
                    for selector in try_continue_selectors:
                        try:
                            if selector.startswith("//"):
                                element = self.driver.find_element(By.XPATH, selector)
                            else:
                                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                            
                            if element.is_displayed() and element.is_enabled():
                                logger.info(f"Clicking security bypass button: {selector}")
                                element.click()
                                time.sleep(2)
                                return True
                        except:
                            continue
                    
                    # If no continue button found, provide instructions
                    logger.warning("Không tìm thấy nút continue. User cần xử lý thủ công.")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi handle Google security: {str(e)}")
            return False
    
    def wait_for_authentication(self, timeout: int = 300) -> bool:
        """
        Đợi người dùng đăng nhập thủ công (nếu cần)
        
        Args:
            timeout: Thời gian timeout (giây)
            
        Returns:
            bool: True nếu đã đăng nhập, False nếu timeout
        """
        try:
            logger.info("Đang kiểm tra trạng thái đăng nhập...")
            
            # Kiểm tra ngay xem đã đăng nhập chưa (nếu có profile)
            if self.use_profile:
                # Restart driver nếu cần
                if not self._restart_driver_if_needed():
                    logger.error("❌ Cannot restart driver, authentication failed")
                    return False
                    
                if self._is_logged_in():
                    logger.info("✅ Đã đăng nhập từ profile đã lưu!")
                    return True
            
            logger.info("Chưa đăng nhập, đang đợi user đăng nhập thủ công...")
            
            # Check for Google security warnings first
            self.handle_google_signin_security()
            
            # Show helpful message
            current_url = self.driver.current_url
            if "accounts.google.com" in current_url:
                logger.info("🔑 Browser đã mở trang đăng nhập Google")
                logger.info("📝 Vui lòng:")
                logger.info("   1. Đăng nhập với tài khoản Google của bạn")
                logger.info("   2. Nếu gặp cảnh báo bảo mật, chọn 'Advanced' -> 'Continue'")
                logger.info("   3. Hoặc thử sử dụng browser mode khác")
                
                # Provide alternative suggestion
                logger.info("💡 Gợi ý: Nếu bị chặn, có thể:")
                logger.info("   - Sử dụng tài khoản Google khác")
                logger.info("   - Thử trong incognito mode")
                logger.info("   - Hoặc đăng nhập trước trong browser thường")
            
            # Đợi user đăng nhập thủ công
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    # Handle security warnings periodically
                    if int(time.time() - start_time) % 10 == 0:
                        self.handle_google_signin_security()
                    
                    # Restart driver nếu session invalid
                    if not self._restart_driver_if_needed():
                        logger.error("❌ Cannot restart driver during authentication")
                        return False
                    
                    # Kiểm tra xem đã đăng nhập chưa
                    if self._is_logged_in():
                        logger.info("✅ Đã đăng nhập thành công!")
                        
                        # Nếu sử dụng profile, profile sẽ tự động lưu session
                        if self.use_profile:
                            logger.info(f"Session đã được lưu vào profile: {self.profile_path}")
                        
                        return True
                        
                except NoSuchElementException:
                    pass
                
                # Hiển thị message để user biết
                elapsed = int(time.time() - start_time)
                if elapsed % 30 == 0:  # Mỗi 30 giây hiển thị 1 lần
                    logger.info(f"Đang đợi đăng nhập... ({elapsed}/{timeout}s)")
                
                time.sleep(2)
            
            logger.warning("Timeout khi đợi xác thực")
            return False
            
        except Exception as e:
            logger.error(f"Lỗi khi đợi xác thực: {str(e)}")
            return False
        
    def select_voice(self, voice_name: str = "Leda") -> bool:
        """
        Chọn giọng nói cho VOICE 1 (selector đầu tiên) sau khi click Multi-speaker audio button
        
        Args:
            voice_name: Tên giọng nói cần chọn (default: "Leda")
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            logger.info(f"🎭 Đang chọn giọng nói cho VOICE 1: {voice_name}")
            
            # BƯỚC 1: Tìm voice selector container và chọn selector đầu tiên (voice 1)
            logger.info("🔍 Tìm voice selector đầu tiên (Voice 1) bằng cách tìm trong voice container...")
            
            voice_selector = None
            
            # Method 1: Tìm trong ms-voice-selector container
            try:
                voice_containers = self.driver.find_elements(By.CSS_SELECTOR, "ms-voice-selector")
                logger.info(f"🔍 Tìm thấy {len(voice_containers)} ms-voice-selector containers")
                
                if len(voice_containers) >= 1:
                    # Chọn container đầu tiên cho Voice 1
                    voice_1_container = voice_containers[0]
                    # Tìm mat-select trong container đó
                    voice_selector = voice_1_container.find_element(By.CSS_SELECTOR, "mat-select")
                    logger.info(f"✅ Tìm thấy Voice 1 selector trong container đầu tiên")
                else:
                    logger.warning("⚠️ Không tìm thấy voice container nào")
            except NoSuchElementException:
                logger.debug("Không tìm thấy ms-voice-selector containers")
            
            # Method 2: Fallback - tìm bằng XPath với speaker icon
            if not voice_selector:
                try:
                    # Tìm tất cả voice selector có icon speaker
                    speaker_selectors = self.driver.find_elements(By.XPATH, 
                        "//mat-select[contains(@class, 'mat-mdc-select') and .//span[contains(@class, 'material-symbols-outlined') and contains(text(), 'voice_selection')]]")
                    
                    logger.info(f"🔍 Tìm thấy {len(speaker_selectors)} voice selectors với speaker icon")
                    
                    if len(speaker_selectors) >= 1:
                        voice_selector = speaker_selectors[0]  # Chọn đầu tiên
                        logger.info("✅ Chọn voice selector đầu tiên với speaker icon")
                    else:
                        logger.warning("⚠️ Không tìm thấy voice selector với speaker icon")
                except Exception as e:
                    logger.debug(f"Method 2 failed: {e}")
            
            # Method 3: Fallback cuối - tìm theo text content "Puck" hoặc giọng hiện tại
            if not voice_selector:
                try:
                    all_selects = self.driver.find_elements(By.CSS_SELECTOR, "mat-select[role='combobox']")
                    voice_selects = []
                    
                    for select in all_selects:
                        if select.is_displayed() and select.is_enabled():
                            text_content = select.text.strip().lower()
                            # Kiểm tra xem có chứa tên giọng nói không
                            voice_names = ['puck', 'Leda', 'altair', 'antares', 'vega', 'sirius']
                            if any(voice_name.lower() in text_content for voice_name in voice_names):
                                voice_selects.append(select)
                                logger.debug(f"Found voice select with text: {text_content}")
                    
                    logger.info(f"🔍 Tìm thấy {len(voice_selects)} voice selectors với giọng nói")
                    
                    if len(voice_selects) >= 1:
                        voice_selector = voice_selects[0]  # Chọn đầu tiên
                        logger.info("✅ Chọn voice selector đầu tiên dựa trên text content")
                    else:
                        logger.warning("⚠️ Không tìm thấy voice selector nào")
                        
                except Exception as e:
                    logger.debug(f"Method 3 failed: {e}")
            
            if not voice_selector:
                logger.error("❌ Không tìm thấy voice selector đầu tiên (Voice 1)")
                # Debug: Log tất cả mat-select elements để kiểm tra
                try:
                    all_selects = self.driver.find_elements(By.TAG_NAME, "mat-select")
                    logger.info(f"🔍 Debug - Tìm thấy {len(all_selects)} mat-select elements:")
                    for i, select in enumerate(all_selects):
                        if select.is_displayed():
                            role = select.get_attribute('role')
                            aria_label = select.get_attribute('aria-labelledby')
                            element_id = select.get_attribute('id')
                            class_name = select.get_attribute('class')
                            current_text = select.text.strip() if select.text else 'no-text'
                            parent_class = select.find_element(By.XPATH, "..").get_attribute('class') if select else 'no-parent'
                            logger.info(f"  Select {i+1}: id='{element_id}', text='{current_text[:30]}', parent_class='{parent_class[:50]}'")
                    
                    # Cũng debug ms-voice-selector containers
                    voice_containers = self.driver.find_elements(By.CSS_SELECTOR, "ms-voice-selector")
                    logger.info(f"🔍 Debug - Tìm thấy {len(voice_containers)} ms-voice-selector containers")
                    for i, container in enumerate(voice_containers):
                        container_text = container.text.strip() if container.text else 'no-text'
                        logger.info(f"  Container {i+1}: text='{container_text[:50]}'")
                        
                    return False
                        
                except Exception as debug_error:
                    logger.error(f"Debug error: {debug_error}")
                return False
            
            # BƯỚC 2: Click vào voice selector để mở dropdown (pure Selenium)
            try:
                # Scroll và click bằng ActionChains
                self._scroll_to_element(voice_selector)
                self._human_click(voice_selector)
                logger.info("✅ Đã click vào voice selector đầu tiên (pure Selenium)")
                
                # Đợi dropdown mở
                self._human_delay(1.0, 2.0)
            except Exception as e:
                logger.warning(f"⚠️ Lỗi khi click voice selector: {str(e)}")
                return False
            
            # BƯỚC 3: Tìm và click option với giọng nói mong muốn
            logger.info(f"🔍 Tìm option giọng nói: {voice_name}")
            
            # Đợi dropdown options xuất hiện
            try:
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "mat-option")))
                logger.info("✅ Dropdown options đã xuất hiện")
            except TimeoutException:
                logger.warning("⚠️ Timeout chờ dropdown options")
            
            # Tìm option với tên giọng nói
            voice_option_selectors = [
                # Selector chính - tìm theo text content
                f"mat-option:has(.name:contains('{voice_name}'))",
                f"mat-option .name:contains('{voice_name}')",
                # Fallback với XPath
                f"//mat-option[.//div[@class='name' and contains(text(), '{voice_name}')]]",
                f"//mat-option[.//div[contains(@class, 'name') and contains(text(), '{voice_name}')]]"
            ]
            
            voice_option = None
            for selector in voice_option_selectors:
                try:
                    if selector.startswith("//") or ":contains" in selector:
                        # Sử dụng XPath
                        xpath_variants = [
                            f"//mat-option[.//div[@class='name' and contains(text(), '{voice_name}')]]",
                            f"//mat-option[.//div[contains(@class, 'name') and contains(text(), '{voice_name}')]]",
                            f"//mat-option[contains(., '{voice_name}')]",
                            f"//mat-option[.//text()[contains(., '{voice_name}')]]"
                        ]
                        
                        for xpath in xpath_variants:
                            try:
                                elements = self.driver.find_elements(By.XPATH, xpath)
                                for element in elements:
                                    if element.is_displayed() and element.is_enabled():
                                        # Kiểm tra thêm text content để chắc chắn
                                        element_text = element.text
                                        if voice_name.lower() in element_text.lower():
                                            voice_option = element
                                            logger.info(f"✅ Tìm thấy voice option với XPath: {xpath}")
                                            logger.info(f"   Option text: {element_text[:100]}")
                                            break
                                if voice_option:
                                    break
                            except NoSuchElementException:
                                continue
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                element_text = element.text
                                if voice_name.lower() in element_text.lower():
                                    voice_option = element
                                    logger.info(f"✅ Tìm thấy voice option với CSS: {selector}")
                                    break
                    
                    if voice_option:
                        break
                except NoSuchElementException:
                    continue
            
            # Nếu không tìm thấy giọng cụ thể, tìm bất kỳ option nào
            if not voice_option:
                logger.warning(f"⚠️ Không tìm thấy giọng '{voice_name}', tìm option đầu tiên...")
                try:
                    all_options = self.driver.find_elements(By.CSS_SELECTOR, "mat-option")
                    logger.info(f"🔍 Debug - Tìm thấy {len(all_options)} options:")
                    
                    for i, option in enumerate(all_options):
                        if option.is_displayed() and option.is_enabled():
                            option_text = option.text.strip()
                            logger.info(f"  Option {i+1}: {option_text[:100]}")
                            
                            # Nếu không có giọng cụ thể, chọn option đầu tiên có thể click
                            if not voice_option and option_text:
                                voice_option = option
                                logger.info(f"✅ Chọn option đầu tiên khả dụng: {option_text[:50]}")
                                break
                except Exception as debug_error:
                    logger.error(f"Debug error: {debug_error}")
            
            if not voice_option:
                logger.error("❌ Không tìm thấy option nào khả dụng")
                return False
            
            # BƯỚC 4: Click vào option đã chọn (pure Selenium)
            try:
                # Scroll và click bằng ActionChains
                self._scroll_to_element(voice_option)
                self._human_click(voice_option)
                logger.info(f"✅ Đã chọn giọng nói cho Voice 1 thành công (pure Selenium)")
                
                # Đợi dropdown đóng và UI update
                self._human_delay(1.0, 2.0)
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Lỗi khi click voice option: {str(e)}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi chọn giọng nói cho Voice 1: {str(e)}")
            return False
        
    def select_voice_2(self, voice_name: str = "Leda") -> bool:
        """
        Chọn giọng nói cho VOICE 2 (selector thứ 2) sau khi click Multi-speaker audio button
        
        Args:
            voice_name: Tên giọng nói cần chọn (default: "Leda")
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            logger.info(f"🎭 Đang chọn giọng nói cho VOICE 2: {voice_name}")
            
            # BƯỚC 1: Tìm voice selector container và chọn selector thứ 2 (voice 2)
            logger.info("🔍 Tìm voice selector thứ 2 (Voice 2) bằng cách tìm trong voice container...")
            
            voice_selector = None
            
            # Method 1: Tìm trong ms-voice-selector container
            try:
                voice_containers = self.driver.find_elements(By.CSS_SELECTOR, "ms-voice-selector")
                logger.info(f"🔍 Tìm thấy {len(voice_containers)} ms-voice-selector containers")
                
                if len(voice_containers) >= 2:
                    # Chọn container thứ 2 cho Voice 2
                    voice_2_container = voice_containers[1]
                    # Tìm mat-select trong container đó
                    voice_selector = voice_2_container.find_element(By.CSS_SELECTOR, "mat-select")
                    logger.info(f"✅ Tìm thấy Voice 2 selector trong container thứ 2")
                elif len(voice_containers) == 1:
                    logger.warning("⚠️ Chỉ có 1 voice container - có thể chưa bật Multi-speaker mode")
            except NoSuchElementException:
                logger.debug("Không tìm thấy ms-voice-selector containers")
            
            # Method 2: Fallback - tìm bằng XPath với speaker icon
            if not voice_selector:
                try:
                    # Tìm tất cả voice selector có icon speaker
                    speaker_selectors = self.driver.find_elements(By.XPATH, 
                        "//mat-select[contains(@class, 'mat-mdc-select') and .//span[contains(@class, 'material-symbols-outlined') and contains(text(), 'voice_selection')]]")
                    
                    logger.info(f"🔍 Tìm thấy {len(speaker_selectors)} voice selectors với speaker icon")
                    
                    if len(speaker_selectors) >= 2:
                        voice_selector = speaker_selectors[1]  # Chọn thứ 2
                        logger.info("✅ Chọn voice selector thứ 2 với speaker icon")
                    elif len(speaker_selectors) == 1:
                        logger.warning("⚠️ Chỉ có 1 voice selector với speaker icon")
                except Exception as e:
                    logger.debug(f"Method 2 failed: {e}")
            
            # Method 3: Fallback cuối - tìm theo text content "Puck" hoặc giọng hiện tại
            if not voice_selector:
                try:
                    all_selects = self.driver.find_elements(By.CSS_SELECTOR, "mat-select[role='combobox']")
                    voice_selects = []
                    
                    for select in all_selects:
                        if select.is_displayed() and select.is_enabled():
                            text_content = select.text.strip().lower()
                            # Kiểm tra xem có chứa tên giọng nói không
                            voice_names = ['puck', 'Leda', 'altair', 'antares', 'vega', 'sirius']
                            if any(voice_name.lower() in text_content for voice_name in voice_names):
                                voice_selects.append(select)
                                logger.debug(f"Found voice select with text: {text_content}")
                    
                    logger.info(f"🔍 Tìm thấy {len(voice_selects)} voice selectors với giọng nói")
                    
                    if len(voice_selects) >= 2:
                        voice_selector = voice_selects[1]  # Chọn thứ 2
                        logger.info("✅ Chọn voice selector thứ 2 dựa trên text content")
                    elif len(voice_selects) == 1:
                        logger.warning("⚠️ Chỉ có 1 voice selector - có thể chưa bật Multi-speaker")
                        
                except Exception as e:
                    logger.debug(f"Method 3 failed: {e}")
            
            if not voice_selector:
                logger.error("❌ Không tìm thấy voice selector thứ 2 (Voice 2)")
                # Debug: Log tất cả mat-select elements để kiểm tra
                try:
                    all_selects = self.driver.find_elements(By.TAG_NAME, "mat-select")
                    logger.info(f"🔍 Debug - Tìm thấy {len(all_selects)} mat-select elements:")
                    for i, select in enumerate(all_selects):
                        if select.is_displayed():
                            role = select.get_attribute('role')
                            aria_label = select.get_attribute('aria-labelledby')
                            element_id = select.get_attribute('id')
                            class_name = select.get_attribute('class')
                            current_text = select.text.strip() if select.text else 'no-text'
                            parent_class = select.find_element(By.XPATH, "..").get_attribute('class') if select else 'no-parent'
                            logger.info(f"  Select {i+1}: id='{element_id}', text='{current_text[:30]}', parent_class='{parent_class[:50]}'")
                    
                    # Cũng debug ms-voice-selector containers
                    voice_containers = self.driver.find_elements(By.CSS_SELECTOR, "ms-voice-selector")
                    logger.info(f"🔍 Debug - Tìm thấy {len(voice_containers)} ms-voice-selector containers")
                    for i, container in enumerate(voice_containers):
                        container_text = container.text.strip() if container.text else 'no-text'
                        logger.info(f"  Container {i+1}: text='{container_text[:50]}'")
                        
                    return False
                        
                except Exception as debug_error:
                    logger.error(f"Debug error: {debug_error}")
                return False
            
            # BƯỚC 2: Click vào voice selector để mở dropdown (pure Selenium)
            try:
                # Scroll và click bằng ActionChains
                self._scroll_to_element(voice_selector)
                self._human_click(voice_selector)
                logger.info("✅ Đã click vào voice selector thứ 2 (pure Selenium)")
                
                # Đợi dropdown mở
                self._human_delay(1.0, 2.0)
            except Exception as e:
                logger.warning(f"⚠️ Lỗi khi click voice selector: {str(e)}")
                return False
            
            # BƯỚC 3: Tìm và click option với giọng nói mong muốn
            logger.info(f"🔍 Tìm option giọng nói: {voice_name}")
            
            # Đợi dropdown options xuất hiện
            try:
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "mat-option")))
                logger.info("✅ Dropdown options đã xuất hiện")
            except TimeoutException:
                logger.warning("⚠️ Timeout chờ dropdown options")
            
            # Tìm option với tên giọng nói
            voice_option_selectors = [
                # Selector chính - tìm theo text content
                f"mat-option:has(.name:contains('{voice_name}'))",
                f"mat-option .name:contains('{voice_name}')",
                # Fallback với XPath
                f"//mat-option[.//div[@class='name' and contains(text(), '{voice_name}')]]",
                f"//mat-option[.//div[contains(@class, 'name') and contains(text(), '{voice_name}')]]"
            ]
            
            voice_option = None
            for selector in voice_option_selectors:
                try:
                    if selector.startswith("//") or ":contains" in selector:
                        # Sử dụng XPath
                        xpath_variants = [
                            f"//mat-option[.//div[@class='name' and contains(text(), '{voice_name}')]]",
                            f"//mat-option[.//div[contains(@class, 'name') and contains(text(), '{voice_name}')]]",
                            f"//mat-option[contains(., '{voice_name}')]",
                            f"//mat-option[.//text()[contains(., '{voice_name}')]]"
                        ]
                        
                        for xpath in xpath_variants:
                            try:
                                elements = self.driver.find_elements(By.XPATH, xpath)
                                for element in elements:
                                    if element.is_displayed() and element.is_enabled():
                                        # Kiểm tra thêm text content để chắc chắn
                                        element_text = element.text
                                        if voice_name.lower() in element_text.lower():
                                            voice_option = element
                                            logger.info(f"✅ Tìm thấy voice option với XPath: {xpath}")
                                            logger.info(f"   Option text: {element_text[:100]}")
                                            break
                                if voice_option:
                                    break
                            except NoSuchElementException:
                                continue
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                element_text = element.text
                                if voice_name.lower() in element_text.lower():
                                    voice_option = element
                                    logger.info(f"✅ Tìm thấy voice option với CSS: {selector}")
                                    break
                    
                    if voice_option:
                        break
                except NoSuchElementException:
                    continue
            
            # Nếu không tìm thấy giọng cụ thể, tìm bất kỳ option nào
            if not voice_option:
                logger.warning(f"⚠️ Không tìm thấy giọng '{voice_name}', tìm option đầu tiên...")
                try:
                    all_options = self.driver.find_elements(By.CSS_SELECTOR, "mat-option")
                    logger.info(f"🔍 Debug - Tìm thấy {len(all_options)} options:")
                    
                    for i, option in enumerate(all_options):
                        if option.is_displayed() and option.is_enabled():
                            option_text = option.text.strip()
                            logger.info(f"  Option {i+1}: {option_text[:100]}")
                            
                            # Nếu không có giọng cụ thể, chọn option đầu tiên có thể click
                            if not voice_option and option_text:
                                voice_option = option
                                logger.info(f"✅ Chọn option đầu tiên khả dụng: {option_text[:50]}")
                                break
                except Exception as debug_error:
                    logger.error(f"Debug error: {debug_error}")
            
            if not voice_option:
                logger.error("❌ Không tìm thấy option nào khả dụng")
                return False
            
            # BƯỚC 4: Click vào option đã chọn
            try:
                # Scroll to option trước
                self.driver.execute_script("arguments[0].scrollIntoView(true);", voice_option)
                self._human_delay(0.5, 1.0)
                
                # Click với human-like behavior
                self._human_click(voice_option)
                logger.info(f"✅ Đã chọn giọng nói cho Voice 2 thành công")
                
                # Đợi dropdown đóng và UI update
                self._human_delay(1.0, 2.0)
                
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ Lỗi khi click voice option: {str(e)}")
                # Thử JavaScript click fallback
                try:
                    self.driver.execute_script("arguments[0].click();", voice_option)
                    logger.info("✅ Đã chọn giọng nói cho Voice 2 bằng JavaScript")
                    self._human_delay(1.0, 2.0)
                    return True
                except Exception as js_error:
                    logger.error(f"❌ Không thể chọn giọng nói: {str(js_error)}")
                    return False
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi chọn giọng nói cho Voice 2: {str(e)}")
            return False
        
    def input_text(self, text: str, voice_name_1: str = "Leda", voice_name_2: str = "Leda", use_fast_paste: bool = True) -> bool:
        """
        Nhập text vào form với tùy chọn fast paste
        
        Args:
            text: Nội dung text cần convert sang audio
            voice_name: Tên giọng nói (default: "Leda")
            use_fast_paste: True = paste nhanh, False = typing như người thật
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            # Kiểm tra session validity trước khi thực hiện
            if not self._check_session_validity():
                logger.warning("⚠️ Session không hợp lệ, thử recovery...")
                if not self._recover_session():
                    logger.error("❌ Không thể recovery session")
                    return False

            # Đợi trang ready trước khi thực hiện thao tác
            if not self._wait_for_page_ready():
                logger.warning("⚠️ Trang chưa ready hoàn toàn, vẫn tiếp tục...")
            
            # Tìm các loại input field có thể có với retry mechanism
            selectors = [
                "textarea",
                "input[type='text']",
                "[contenteditable='true']",
                "[role='textbox']",
                ".text-input",
                "#text-input",
                # Thêm selector cho AI Studio
                "textarea[placeholder*='text']",
                "textarea[aria-label*='text']",
                "div[contenteditable='true']"
            ]
            
            text_input = None
            max_retries = 3
            
            for retry in range(max_retries):
                if retry > 0:
                    logger.info(f"🔄 Retry {retry}/{max_retries-1} tìm text input...")
                    self._human_delay(2, 3)
                
                for selector in selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                text_input = element
                                logger.info(f"✅ Tìm thấy text input với selector: {selector}")
                                break
                        if text_input:
                            break
                    except NoSuchElementException:
                        continue
                    except Exception as e:
                        logger.debug(f"Lỗi khi tìm element với selector {selector}: {str(e)}")
                        continue
                
                if text_input:
                    break
            
            if not text_input:
                logger.error("❌ Không tìm thấy field nhập text sau nhiều lần thử")
                
                # Debug: Log thông tin trang hiện tại
                try:
                    current_url = self.driver.current_url
                    page_title = self.driver.title
                    logger.debug(f"Current URL: {current_url}")
                    logger.debug(f"Page title: {page_title}")
                    
                    # Tìm tất cả textarea và input elements
                    all_textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
                    all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
                    logger.debug(f"Found {len(all_textareas)} textarea và {len(all_inputs)} input elements")
                    
                except Exception as debug_error:
                    logger.debug(f"Debug error: {str(debug_error)}")
                
                return False
            
            # Scroll to element bằng ActionChains
            self._scroll_to_element(text_input)

            # 🎲 Random delay trước khi click để mô phỏng hành vi người thật
            self._human_delay(0.5, 1.5)

            # Click vào text field trước
            self._human_click(text_input)

            # 🎲 Delay sau click, trước khi nhập text
            self._human_delay(0.3, 0.8)

            # Nhập text với tốc độ được chọn
            self._human_type(text_input, text, use_fast_paste=use_fast_paste)
            
            if use_fast_paste:
                logger.info("✅ Đã paste text thành công")
            else:
                logger.info("✅ Đã nhập text với human typing thành công")
            # Đợi trang ready trước khi thực hiện thao tác
            if not self._wait_for_page_ready():
                logger.warning("⚠️ Trang chưa ready hoàn toàn, vẫn tiếp tục...")
                self._human_delay(1.0, 2.0)
                
            # BƯỚC 1: Tìm và click button "Multi-speaker audio" trước
            logger.info("🎯 Tìm và click button Multi-speaker audio...")
            
            multi_speaker_button = None
            
            # Method 1: Tìm theo ms-toggle-button với symbol="group"
            try:
                ms_toggle_selectors = [
                    "ms-toggle-button[symbol='group']",
                    "ms-toggle-button[text='Multi-speaker audio']", 
                    "ms-toggle-button[symbol='group'][text='Multi-speaker audio']"
                ]
                
                for selector in ms_toggle_selectors:
                    try:
                        toggle_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for toggle_element in toggle_elements:
                            if toggle_element.is_displayed():
                                # Tìm button con bên trong ms-toggle-button
                                button = toggle_element.find_element(By.CSS_SELECTOR, "button[ms-button]")
                                if button and button.is_enabled():
                                    multi_speaker_button = button
                                    logger.info(f"✅ Tìm thấy Multi-speaker button trong ms-toggle-button: {selector}")
                                    break
                        if multi_speaker_button:
                            break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                logger.debug(f"Method 1 failed: {e}")
            
            # Method 2: Tìm trực tiếp button có icon "group" và text "Multi-speaker audio"
            if not multi_speaker_button:
                try:
                    xpath_selectors = [
                        # Tìm button có icon "group" và text "Multi-speaker audio"
                        "//button[@ms-button and .//span[@class='material-symbols-outlined notranslate ms-button-icon-symbol ng-star-inserted' and contains(text(), 'group')] and contains(text(), 'Multi-speaker audio')]",
                        # Fallback - tìm button chứa icon "group"  
                        "//button[@ms-button and .//span[contains(@class, 'material-symbols-outlined') and contains(text(), 'group')]]",
                        # Fallback - tìm button có text "Multi-speaker audio"
                        "//button[@ms-button and contains(text(), 'Multi-speaker audio')]",
                        # Fallback - tìm trong ms-toggle-button
                        "//ms-toggle-button[@symbol='group']//button[@ms-button]",
                        "//ms-toggle-button[contains(@text, 'Multi-speaker')]//button[@ms-button]"
                    ]
                    
                    for xpath in xpath_selectors:
                        try:
                            elements = self.driver.find_elements(By.XPATH, xpath)
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    multi_speaker_button = element
                                    logger.info(f"✅ Tìm thấy Multi-speaker button với XPath: {xpath}")
                                    break
                            if multi_speaker_button:
                                break
                        except NoSuchElementException:
                            continue
                except Exception as e:
                    logger.debug(f"Method 2 failed: {e}")
            
            # Method 3: Fallback - tìm theo CSS selector với class pattern
            if not multi_speaker_button:
                try:
                    css_selectors = [
                        # Button với class ms-button và có icon group
                        "button[ms-button] .material-symbols-outlined:contains('group')",
                        # Button borderless có chứa text Multi-speaker
                        "button.ms-button-borderless:contains('Multi-speaker')",
                        # Button trong ms-toggle-button
                        "ms-toggle-button button[ms-button]",
                        # Button có variant borderless
                        "button[ms-button][variant='borderless']:contains('Multi-speaker')"
                    ]
                    
                    for selector in css_selectors:
                        try:
                            if ":contains" in selector:
                                # Convert CSS :contains to XPath
                                if "Multi-speaker" in selector:
                                    xpath_equivalent = f"//button[contains(text(), 'Multi-speaker')]"
                                elif "group" in selector:
                                    xpath_equivalent = f"//button[.//span[contains(text(), 'group')]]"
                                else:
                                    continue
                                    
                                elements = self.driver.find_elements(By.XPATH, xpath_equivalent)
                            else:
                                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            
                            for element in elements:
                                if ":contains" not in selector:
                                    # Với CSS selector thông thường, tìm parent button
                                    parent_button = element.find_element(By.XPATH, ".//ancestor-or-self::button[@ms-button]")
                                    if parent_button and parent_button.is_displayed() and parent_button.is_enabled():
                                        multi_speaker_button = parent_button
                                        logger.info(f"✅ Tìm thấy Multi-speaker button với CSS parent: {selector}")
                                        break
                                else:
                                    # Với XPath đã có button
                                    if element.is_displayed() and element.is_enabled():
                                        multi_speaker_button = element
                                        logger.info(f"✅ Tìm thấy Multi-speaker button với XPath converted: {selector}")
                                        break
                                        
                            if multi_speaker_button:
                                break
                        except NoSuchElementException:
                            continue
                except Exception as e:
                    logger.debug(f"Method 3 failed: {e}")
            
            # Click Multi-speaker button nếu tìm thấy
            if multi_speaker_button:
                try:
                    # Scroll to button trước
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", multi_speaker_button)
                    self._human_delay(0.5, 1.0)
                    
                    # Kiểm tra xem button có đang active không
                    button_classes = multi_speaker_button.get_attribute('class') or ''
                    if 'ms-button-active' in button_classes:
                        logger.info("✅ Multi-speaker button đã được kích hoạt")
                    else:
                        logger.info("🔄 Multi-speaker button chưa active, đang click...")
                        
                        # Ưu tiên JavaScript click để tránh mất focus
                        try:
                            self.driver.execute_script("arguments[0].click();", multi_speaker_button)
                            logger.info("✅ Đã click Multi-speaker button bằng JavaScript (focus-safe)")
                        except Exception as js_error:
                            # Fallback to human click nếu JS fail
                            logger.warning("⚠️ JavaScript click failed, fallback to human click...")
                            self._human_click(multi_speaker_button)
                            logger.info("✅ Đã click button Multi-speaker audio với human-like behavior")
                        
                        # Đợi UI update sau khi click
                        self._human_delay(1.0, 2.0)
                except Exception as e:
                    logger.warning(f"⚠️ Lỗi khi click Multi-speaker button: {str(e)}")
                    # Thử JavaScript click fallback
                    try:
                        self.driver.execute_script("arguments[0].click();", multi_speaker_button)
                        logger.info("✅ Đã click Multi-speaker button bằng JavaScript")
                        self._human_delay(1.0, 2.0)
                    except Exception as js_error:
                        logger.error(f"❌ Không thể click Multi-speaker button: {str(js_error)}")
            else:
                logger.warning("⚠️ Không tìm thấy button Multi-speaker audio")
                # Debug: Log tất cả ms-toggle-button và buttons có thể
                try:
                    # Debug ms-toggle-button elements
                    ms_toggles = self.driver.find_elements(By.TAG_NAME, "ms-toggle-button")
                    logger.info(f"🔍 Debug - Tìm thấy {len(ms_toggles)} ms-toggle-button elements:")
                    for i, toggle in enumerate(ms_toggles):
                        if toggle.is_displayed():
                            symbol = toggle.get_attribute('symbol') or ''
                            text = toggle.get_attribute('text') or ''
                            logger.info(f"  Toggle {i+1}: symbol='{symbol}', text='{text}'")
                    
                    # Debug buttons with ms-button attribute
                    ms_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[ms-button]")
                    logger.info(f"🔍 Debug - Tìm thấy {len(ms_buttons)} button[ms-button] elements:")
                    for i, btn in enumerate(ms_buttons[:10]):  # Chỉ log 10 buttons đầu
                        if btn.is_displayed():
                            text = btn.text.strip()[:50] if btn.text else ""
                            variant = btn.get_attribute('variant') or ""
                            class_name = btn.get_attribute('class') or ""
                            logger.info(f"  Button {i+1}: text='{text}', variant='{variant}', class='{class_name[:50]}'")
                except Exception as debug_error:
                    logger.error(f"Debug error: {debug_error}")
                    
            logger.info(f"🎭 Tiến hành chọn giọng nói 1: {voice_name_1}")
            if not self.select_voice(voice_name_1):
                logger.warning(f"⚠️ Không thể chọn giọng '{voice_name_1}', tiếp tục với giọng mặc định...")
            logger.info(f"🎭 Tiến hành chọn giọng nói 2: {voice_name_2}")
            if not self.select_voice_2(voice_name_2):
                logger.warning(f"⚠️ Không thể chọn giọng '{voice_name_2}', tiếp tục với giọng mặc định...")
            return True
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Lỗi khi nhập text: {error_msg}")
            
            if "element not interactable" in error_msg:
                logger.warning("⚠️ Element không thể tương tác, đợi thêm...")
                self._human_delay(3, 5)
                return self.input_text(text, voice_name_1, voice_name_2=voice_name_2, use_fast_paste=use_fast_paste)  # Retry một lần
                
            return False
    
    def click_generate_button(self) -> bool:
        """
        Click nút Run để tạo audio với human-like behavior (pure Selenium, no JavaScript)
        
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            logger.info("Đang tìm và click nút Run")
            
            # Các XPath selector để tìm button
            xpath_selectors = [
                # Tìm button có text "Run" hoặc aria-label="Run"
                "//button[contains(text(), 'Run') or contains(@aria-label, 'Run')]",
                # Fallback cho "Generate"
                "//button[contains(text(), 'Generate') or contains(@aria-label, 'Generate')]",
                # Fallback với class
                "//button[contains(@class, 'run-button')]",
                "//button[contains(@class, 'generate-button')]",
                # Fallback với type submit
                "//button[@type='submit']"
            ]
            
            generate_button = None
            for xpath in xpath_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            # Kiểm tra thêm nếu element có chứa text "Run" hoặc "Generate"
                            element_text = element.text.strip().lower()
                            aria_label = element.get_attribute('aria-label')
                            if aria_label:
                                aria_label = aria_label.lower()
                            
                            # Ưu tiên button có text "Run" hoặc aria-label="Run"
                            if ('run' in element_text or (aria_label and 'run' in aria_label)):
                                generate_button = element
                                logger.info(f"Tìm thấy button Run: text='{element.text}', aria-label='{element.get_attribute('aria-label')}'")
                                break
                            # Fallback cho "Generate"
                            elif ('generate' in element_text or (aria_label and 'generate' in aria_label)):
                                generate_button = element
                                logger.info(f"Tìm thấy button Generate: text='{element.text}', aria-label='{element.get_attribute('aria-label')}'")
                                break
                    
                    if generate_button:
                        break
                except NoSuchElementException:
                    continue
            
            if not generate_button:
                logger.error("Không tìm thấy nút Run hoặc Generate")
                # Debug: In ra tất cả buttons có thể
                try:
                    all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    logger.info("Tất cả buttons trên trang:")
                    for btn in all_buttons[:10]:  # Chỉ log 10 buttons đầu
                        if btn.is_displayed():
                            logger.info(f"  - Text: '{btn.text}', aria-label: '{btn.get_attribute('aria-label')}', class: '{btn.get_attribute('class')}'")
                except:
                    pass
                return False
            
            # KHÔNG dùng JavaScript scroll - dùng ActionChains
            # Scroll to view bằng ActionChains
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(self.driver)
            actions.move_to_element(generate_button).perform()
            self._human_delay(0.5, 1.0)
            
            # 🎲 Random delay trước khi click để giảm bot detection
            # Delay 2-5 giây để mô phỏng người dùng đọc/kiểm tra trước khi click
            pre_click_delay = 2.0 + (3.0 * __import__('random').random())  # 2-5 giây
            logger.info(f"⏳ Đợi {pre_click_delay:.1f}s trước khi click (giảm bot detection)...")
            time.sleep(pre_click_delay)

            # Click bằng Selenium native (đã có trong _human_click)
            self._human_click(generate_button)
            logger.info("Đã click nút Run/Generate với human-like behavior (pure Selenium)")

            # Tăng delay sau click để tránh rate limiting
            self._human_delay(2.0, 4.0)  # Tăng từ 1-2s lên 2-4s
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi click nút Run/Generate: {str(e)}")
            return False
    
    def wait_for_audio_generation(self, text_length: int = None, max_wait_minutes: int = 30) -> bool:
        """
        Đợi quá trình tạo audio hoàn thành - adaptive timeout dựa trên độ dài text
        
        Args:
            text_length: Độ dài text để tính timeout adaptive (số ký tự)
            max_wait_minutes: Thời gian chờ tối đa (phút)
            
        Returns:
            bool: True nếu thành công, False nếu timeout hoặc lỗi
        """
        try:
            # Tính timeout adaptive dựa trên độ dài text
            if text_length:
                # Công thức: ~2-3 giây/ký tự + buffer time
                base_time = max(60, text_length * 2.5)  # Tối thiểu 60s
                adaptive_timeout = min(base_time, max_wait_minutes * 60)  # Tối đa max_wait_minutes
                logger.info(f"📏 Text length: {text_length} chars → Adaptive timeout: {int(adaptive_timeout/60)}m {int(adaptive_timeout%60)}s")
            else:
                adaptive_timeout = max_wait_minutes * 60  # Default fallback
                logger.info(f"📏 No text length provided → Default timeout: {max_wait_minutes}m")
            
            logger.info("Đang đợi quá trình tạo audio...")

            start_time = time.time()
            last_log_time = start_time
            check_interval = 3  # Kiểm tra mỗi 3 giây
            consecutive_no_loading = 0  # Đếm số lần liên tiếp không thấy loading

            # ⭐ Progressive verification: Theo dõi duration tăng dần
            last_duration = 0
            duration_stable_count = 0  # Đếm số lần duration không đổi

            while time.time() - start_time < adaptive_timeout:
                elapsed = time.time() - start_time

                # Log progress theo % và thời gian thực
                if elapsed - (last_log_time - start_time) >= 15:  # Log mỗi 15 giây
                    progress_percent = min(95, (elapsed / adaptive_timeout) * 100)
                    logger.info(f"🔄 Audio generation progress: {progress_percent:.1f}% ({int(elapsed/60)}m {int(elapsed%60)}s / ~{int(adaptive_timeout/60)}m)")
                    last_log_time = time.time()

                # ⭐ Progressive check: Kiểm tra duration đang tăng dần
                current_duration = self._get_audio_duration()
                if current_duration and current_duration > 0:
                    if current_duration > last_duration:
                        logger.debug(f"📈 Audio duration đang tăng: {last_duration:.1f}s → {current_duration:.1f}s")
                        last_duration = current_duration
                        duration_stable_count = 0  # Reset counter
                    elif current_duration == last_duration and last_duration > 0:
                        duration_stable_count += 1
                        logger.debug(f"⏸️ Audio duration ổn định ở {current_duration:.1f}s ({duration_stable_count}/5)")

                        # Nếu duration không đổi trong 5 lần liên tiếp (15 giây)
                        # có thể audio đã hoàn thành
                        if duration_stable_count >= 5:
                            logger.info(f"📊 Audio duration đã ổn định ở {current_duration:.1f}s, kiểm tra final...")
                            # Double check với _check_audio_ready()
                            time.sleep(2)
                            if self._check_audio_ready():
                                logger.info(f"✅ Audio đã hoàn thành với duration = {current_duration:.1f}s!")
                                return True
                            # Nếu chưa ready, reset counter và tiếp tục
                            duration_stable_count = 0

                # Kiểm tra audio element đã hoàn thành
                audio_ready = self._check_audio_ready()
                if audio_ready:
                    logger.info(f"✅ Audio đã được tạo thành công sau {int(elapsed/60)}m {int(elapsed%60)}s!")
                    return True
                
                # Kiểm tra error messages
                if self._check_generation_errors():
                    return False

                # 🛡️ Kiểm tra network 403 errors
                if self._check_network_403_errors():
                    logger.error("🚫 Phát hiện lỗi 403 - Có thể do rate limiting hoặc vi phạm policy")
                    return False
                
                # Kiểm tra trạng thái loading
                is_loading = self._check_loading_indicators()
                
                if not is_loading:
                    self._ensure_window_focus()
                    consecutive_no_loading += 1
                    logger.debug(f"Không thấy loading indicator ({consecutive_no_loading}/3)")
                    
                    # Nếu không thấy loading indicator liên tiếp 3 lần (9 giây), 
                    # có thể đã hoàn thành hoặc bị lỗi
                    if consecutive_no_loading >= 3:
                        logger.info("🔍 Không thấy loading indicator, kiểm tra kỹ lưỡng...")
                        
                        # Double-check audio một lần nữa
                        time.sleep(2)
                        if self._check_audio_ready():
                            logger.info("✅ Audio đã sẵn sàng!")
                            return True
                        
                        # Kiểm tra có thể generation đã dừng do lỗi
                        if self._check_generation_stopped():
                            logger.warning("⚠️ Generation có vẻ đã dừng mà không có audio")
                            return False
                        
                        # Reset counter và tiếp tục
                        consecutive_no_loading = 0
                else:
                    self._ensure_window_focus()
                    consecutive_no_loading = 0
                    logger.debug("Vẫn đang loading...")
                
                time.sleep(check_interval)
            
            # Timeout - nhưng check cuối cùng một lần nữa
            logger.warning(f"⏰ Đã đợi {int(adaptive_timeout/60)}m, kiểm tra cuối cùng...")
            if self._check_audio_ready():
                logger.info("✅ Audio có sẵn ngay sau timeout!")
                return True
            
            logger.warning(f"❌ Timeout ({int(adaptive_timeout/60)}m {int(adaptive_timeout%60)}s) - audio chưa sẵn sàng")
            
            # Debug information
            self._log_audio_debug_info()
            
            return False
            
        except Exception as e:
            logger.error(f"Lỗi khi đợi tạo audio: {str(e)}")
            return False

    def _check_audio_ready(self) -> bool:
        """Kiểm tra xem audio đã sẵn sàng chưa và verify rằng audio đã được generate hoàn toàn"""
        audio_selectors = [
            ".speech-prompt-footer-actions-left audio[controls]",
            ".speech-prompt-footer-actions-left audio",
            "audio[controls][src]",
            "audio[controls]",
            ".ng-star-inserted audio",
            "div[class*='footer-actions'] audio",
            "div[class*='speech-prompt'] audio"
        ]

        for selector in audio_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        src = element.get_attribute('src')
                        if src and src.strip() and src != "":
                            # ⭐ CRITICAL: Verify audio duration to ensure it's fully generated
                            try:
                                # Get audio metadata using JavaScript
                                audio_info = self.driver.execute_script("""
                                    const audio = arguments[0];
                                    return {
                                        duration: audio.duration,
                                        readyState: audio.readyState,
                                        buffered: audio.buffered.length > 0 ? {
                                            start: audio.buffered.start(0),
                                            end: audio.buffered.end(audio.buffered.length - 1)
                                        } : null,
                                        currentTime: audio.currentTime,
                                        networkState: audio.networkState
                                    };
                                """, element)

                                duration = audio_info.get('duration')
                                ready_state = audio_info.get('readyState')
                                buffered = audio_info.get('buffered')
                                network_state = audio_info.get('networkState')

                                # Check if duration is valid (not NaN, not 0, not Infinity)
                                if duration and duration > 0 and duration != float('inf'):
                                    logger.debug(f"🎵 Audio metadata: duration={duration:.2f}s, readyState={ready_state}, networkState={network_state}")

                                    # ⭐ FIX: Chỉ chấp nhận readyState = 4 (HAVE_ENOUGH_DATA)
                                    # readyState = 3 (HAVE_FUTURE_DATA) có thể chưa tải hết audio!
                                    if ready_state != 4:
                                        logger.debug(f"⏳ Audio chưa sẵn sàng: readyState={ready_state} (cần = 4)")
                                        return False

                                    # ⭐ Kiểm tra buffered ranges - đảm bảo toàn bộ audio đã được buffer
                                    if buffered:
                                        buffered_start = buffered.get('start', 0)
                                        buffered_end = buffered.get('end', 0)
                                        buffer_coverage = (buffered_end - buffered_start) / duration * 100

                                        logger.debug(f"📊 Buffered: {buffered_start:.2f}s - {buffered_end:.2f}s ({buffer_coverage:.1f}% of {duration:.2f}s)")

                                        # Yêu cầu ít nhất 95% audio đã được buffer
                                        if buffer_coverage < 95:
                                            logger.debug(f"⏳ Audio chưa buffer đủ: {buffer_coverage:.1f}% < 95%")
                                            return False
                                    else:
                                        logger.debug(f"⚠️ Không có thông tin buffered ranges")
                                        # Không có buffered info, chỉ dựa vào readyState

                                    # ⭐ Kiểm tra network state
                                    # networkState: 0=EMPTY, 1=IDLE, 2=LOADING, 3=NO_SOURCE
                                    if network_state == 2:  # LOADING
                                        logger.debug(f"⏳ Audio vẫn đang loading (networkState=2)")
                                        return False

                                    # ⭐ Tất cả kiểm tra đã pass
                                    logger.debug(f"✅ Audio hoàn toàn sẵn sàng!")
                                    return True
                                else:
                                    logger.debug(f"⏳ Audio duration không hợp lệ: {duration}")
                                    return False
                            except Exception as duration_error:
                                logger.debug(f"⚠️ Không thể verify audio metadata: {duration_error}")
                                # KHÔNG fallback - nếu không verify được thì chưa ready
                                return False

            except NoSuchElementException:
                continue
        return False

    def _get_audio_duration(self) -> float:
        """
        Lấy duration hiện tại của audio element (nếu có)
        Returns: duration in seconds, hoặc 0 nếu không tìm thấy
        """
        audio_selectors = [
            ".speech-prompt-footer-actions-left audio[controls]",
            ".speech-prompt-footer-actions-left audio",
            "audio[controls][src]",
            "audio[controls]",
            ".ng-star-inserted audio",
            "div[class*='footer-actions'] audio",
            "div[class*='speech-prompt'] audio"
        ]

        for selector in audio_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        src = element.get_attribute('src')
                        if src and src.strip() and src != "":
                            try:
                                duration = self.driver.execute_script(
                                    "return arguments[0].duration;", element
                                )
                                if duration and duration > 0 and duration != float('inf'):
                                    return duration
                            except:
                                pass
            except NoSuchElementException:
                continue
        return 0

    def _check_generation_errors(self) -> bool:
        """Kiểm tra có lỗi generation không"""
        error_selectors = [
            "[class*='error']",
            "[class*='Error']",
            ".alert-danger",
            ".error-message",
            "[role='alert']"
        ]

        for selector in error_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.text.strip():
                        error_text = element.text.strip()
                        # Kiểm tra các từ khóa lỗi
                        error_keywords = ['error', 'failed', 'lỗi', 'thất bại', 'forbidden', '403', 'rate limit', 'quota', 'permission denied']
                        if any(word in error_text.lower() for word in error_keywords):
                            config.kill_browser_instances(self.chrome_binary_path, verbose=True)
                            logger.error(f"❌ Phát hiện lỗi generation: {error_text}")

                            # 🚫 Phân tích lỗi cụ thể
                            if '403' in error_text.lower() or 'forbidden' in error_text.lower():
                                logger.error("🚫 Lỗi 403 Forbidden - Nguyên nhân có thể:")
                                logger.error("   1. Rate limiting: Quá nhiều requests trong thời gian ngắn")
                                logger.error("   2. Quota exceeded: Đã hết quota miễn phí của Google AI Studio")
                                logger.error("   3. Policy violation: Nội dung vi phạm chính sách của Google")
                                logger.error("   4. Authentication issue: Session hết hạn hoặc không đủ quyền")
                                logger.error("💡 Giải pháp:")
                                logger.error("   - Đợi 15-30 phút trước khi thử lại")
                                logger.error("   - Kiểm tra quota tại: https://aistudio.google.com/")
                                logger.error("   - Thử đổi tài khoản Google khác")
                                logger.error("   - Kiểm tra nội dung có vi phạm policy không")

                            elif 'rate' in error_text.lower() or 'quota' in error_text.lower():
                                logger.error("⚠️ Lỗi Rate Limit/Quota - Nguyên nhân:")
                                logger.error("   - Đã vượt giới hạn số requests cho phép")
                                logger.error("💡 Giải pháp:")
                                logger.error("   - Hệ thống sẽ tự động retry với exponential backoff")
                                logger.error("   - Nếu vẫn lỗi, đợi 30-60 phút")

                            return True
            except NoSuchElementException:
                continue
        return False

    def _check_loading_indicators(self) -> bool:
        """Kiểm tra các loading indicators"""
        loading_selectors = [
            "[class*='loading']",
            "[class*='Loading']",
            "[class*='spinner']",
            "[class*='Spinner']", 
            "[aria-label*='Loading']",
            "[aria-label*='loading']",
            "[class*='progress']",
            "[class*='Progress']",
            ".mat-spinner",
            ".mat-progress-spinner",
            # Thêm selector cho generate button disabled state
            "button[aria-label='Run'][disabled]",
            "button[aria-label*='Run'][disabled]"
        ]
        
        for selector in loading_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        return True
            except NoSuchElementException:
                continue
        return False

    def _check_generation_stopped(self) -> bool:
        """Kiểm tra generation có bị dừng không (button Run lại enable)"""
        try:
            # Nếu button Run lại có thể click được, có thể generation đã dừng
            run_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Run']:not([disabled])")
            for button in run_buttons:
                if button.is_displayed() and button.is_enabled():
                    logger.debug("Button Run đã enable lại - generation có thể đã dừng")
                    return True
        except:
            pass
        return False

    def _log_audio_debug_info(self):
        """Log debug information về audio elements"""
        try:
            all_audio = self.driver.find_elements(By.TAG_NAME, "audio")
            logger.info(f"🔍 Debug: Tìm thấy {len(all_audio)} audio elements:")
            for i, audio in enumerate(all_audio):
                src = audio.get_attribute('src')
                controls = audio.get_attribute('controls')
                visible = audio.is_displayed()
                class_name = audio.get_attribute('class')
                logger.info(f"  Audio {i+1}: src='{src}', controls={controls}, visible={visible}, class='{class_name}'")
        except Exception as debug_error:
            logger.error(f"Debug error: {debug_error}")

    def _check_network_403_errors(self) -> bool:
        """
        Kiểm tra network logs để phát hiện lỗi 403 Forbidden

        Returns:
            bool: True nếu phát hiện lỗi 403, False nếu không
        """
        try:
            import json

            logs = self.driver.get_log('performance')

            for entry in logs:
                try:
                    log_data = json.loads(entry['message'])
                    message = log_data.get('message', {})
                    method = message.get('method')

                    # Kiểm tra response received
                    if method == 'Network.responseReceived':
                        response = message.get('params', {}).get('response', {})
                        status = response.get('status')
                        url = response.get('url', '')

                        # Phát hiện lỗi 403
                        if status == 403:
                            logger.error(f"🚫 Phát hiện lỗi 403 Forbidden từ network!")
                            logger.error(f"   URL: {url}")
                            logger.error(f"   Status: {status}")
                            logger.error(f"   Status Text: {response.get('statusText', 'N/A')}")

                            # Log headers để debug
                            headers = response.get('headers', {})
                            if headers:
                                logger.debug(f"   Response Headers: {headers}")

                            # Phân tích nguyên nhân
                            logger.error("🔍 Phân tích nguyên nhân:")
                            logger.error("   ✓ Đây là lỗi từ Google AI Studio server")
                            logger.error("   ✓ Có thể do rate limiting hoặc quota vượt ngưỡng")
                            logger.error("   ✓ Hoặc nội dung vi phạm policy của Google")
                            logger.error("💡 Hệ thống sẽ tự động retry với exponential backoff...")

                            return True

                        # Phát hiện các lỗi khác liên quan
                        elif status in [429, 401]:  # 429 = Too Many Requests, 401 = Unauthorized
                            logger.warning(f"⚠️ Phát hiện lỗi {status}!")
                            logger.warning(f"   URL: {url}")
                            logger.warning(f"   Status Text: {response.get('statusText', 'N/A')}")

                except json.JSONDecodeError:
                    continue
                except Exception as parse_error:
                    logger.debug(f"Error parsing log entry: {parse_error}")
                    continue

            return False

        except Exception as e:
            logger.debug(f"Error checking network logs: {str(e)}")
            return False

    def download_audio(self, order_in_story: int, output_filename: str = None) -> Optional[str]:
        """
        Tải file audio về máy - dựa trên cấu trúc HTML thực tế của AI Studio
        
        Args:
            story_id: ID của story để tạo filename
            chapter_number: Số chương để tạo filename
        
        Returns:
            Optional[str]: Đường dẫn file audio nếu thành công, None nếu thất bại
        """
        try:
            logger.info("Đang tìm audio element đã được tạo...")
            
            # ⭐ CRITICAL: Đợi thêm để đảm bảo audio hoàn toàn ready
            logger.info("⏳ Đợi thêm 3s để đảm bảo audio đã sẵn sàng hoàn toàn...")
            time.sleep(3)

            # Tìm audio element dựa trên cấu trúc HTML thực tế
            audio_selectors = [
                # Audio element chính trong footer actions
                ".speech-prompt-footer-actions-left audio[controls]",
                ".speech-prompt-footer-actions-left audio",
                # Fallback selectors
                "audio[controls][src]",
                "audio[controls]",
                "audio[src]",
                ".ng-star-inserted audio",
                "div[class*='footer-actions'] audio"
            ]

            audio_element = None
            audio_duration = 0
            for selector in audio_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            # Kiểm tra audio có src không (đã được load)
                            src = element.get_attribute('src')
                            if src and src.strip() and src != "":
                                # ⭐ Verify audio metadata trước khi download
                                try:
                                    duration = self.driver.execute_script("return arguments[0].duration;", element)
                                    ready_state = self.driver.execute_script("return arguments[0].readyState;", element)
                                    logger.info(f"📊 Audio metadata: duration={duration:.2f}s, readyState={ready_state}")

                                    # ⭐ FIX: Yêu cầu readyState = 4 để đảm bảo audio đã tải hoàn toàn
                                    if ready_state < 4:
                                        logger.info(f"⏳ Audio chưa hoàn toàn sẵn sàng (readyState={ready_state}), đợi thêm...")
                                        # Đợi tối đa 30 giây để readyState = 4
                                        wait_count = 0
                                        while ready_state < 4 and wait_count < 10:
                                            time.sleep(3)
                                            ready_state = self.driver.execute_script("return arguments[0].readyState;", element)
                                            wait_count += 1
                                            logger.debug(f"⏳ Waiting for readyState=4... current={ready_state} ({wait_count}/10)")

                                        if ready_state < 4:
                                            logger.warning(f"⚠️ Timeout waiting for readyState=4, proceeding with readyState={ready_state}")

                                    audio_duration = duration  # Lưu duration để tính thời gian đợi sau
                                except Exception as meta_error:
                                    logger.debug(f"Cannot get audio metadata: {meta_error}")

                                audio_element = element
                                logger.info(f"Tìm thấy audio element với src: {src[:100]}...")
                                break
                    if audio_element:
                        break
                except NoSuchElementException:
                    continue
            
            if not audio_element:
                logger.error("Không tìm thấy audio element với src")
                # Debug: log tất cả audio elements
                try:
                    all_audio = self.driver.find_elements(By.TAG_NAME, "audio")
                    logger.info(f"Tìm thấy {len(all_audio)} audio elements:")
                    for i, audio in enumerate(all_audio):
                        src = audio.get_attribute('src')
                        controls = audio.get_attribute('controls')
                        visible = audio.is_displayed()
                        logger.info(f"  Audio {i+1}: src='{src}', controls={controls}, visible={visible}")
                except Exception as e:
                    self.close() 
                    logger.error(f"Debug error: {e}")
            
            # Lấy audio source URL
            audio_src = audio_element.get_attribute('src')
            if not audio_src or audio_src.strip() == "":
                logger.error("Audio element không có src")
                return None
            
            logger.info(f"Đã tìm thấy audio source")
            
            # Kiểm tra nếu src là blob URL hoặc data URL
            if audio_src.startswith('blob:') or audio_src.startswith('data:'):
                logger.info("Audio là blob/data URL, tải trực tiếp...")
                return self._download_blob_audio(audio_src, audio_duration=audio_duration, order_in_story=order_in_story, output_filename=output_filename)

            # Thử right-click context menu để download
            logger.info("Thử right-click download...")
            return self._download_via_context_menu(audio_element, order_in_story=order_in_story, output_filename=output_filename)
            
        except Exception as e:
            logger.error(f"Lỗi khi tải audio: {str(e)}")
            return None

    def _download_blob_audio(self, blob_url: str, audio_duration: float = 0, order_in_story: int = None, output_filename: str = None) -> Optional[str]:
        """
        Tải audio từ blob URL bằng Python - sử dụng JavaScript để convert blob thành base64

        Args:
            blob_url: Blob URL của audio
            audio_duration: Duration của audio (seconds) để tính adaptive wait time
            story_id: ID của story để tạo filename
            chapter_number: Số chương để tạo filename

        Returns:
            Optional[str]: Đường dẫn file đã tải
        """
        try:
            logger.info(f"🎵 Tải audio từ blob URL bằng Python: {blob_url[:50]}...")

            # Đảm bảo download directory tồn tại
            if not os.path.exists(self.download_path):
                os.makedirs(self.download_path, exist_ok=True)
                logger.info(f"📁 Đã tạo download directory: {self.download_path}")

            # Tạo tên file với định dạng <story_id>_<chapter_number>.wav
            if output_filename:
                filename = output_filename
            else:
                filename = f"segment_{order_in_story}.wav"

            filepath = os.path.join(self.download_path, filename)

            # Method 1: Sử dụng JavaScript để convert blob thành base64 và Python để lưu
            logger.info("🔄 Method 1: Convert blob to base64...")
            success = self._download_blob_via_base64(blob_url, filepath, audio_duration=audio_duration)
            if success:
                return filepath
            
            # Method 2: Fallback - sử dụng JavaScript download như cũ
            logger.info("🔄 Method 2: Fallback to JavaScript download...")
            success = self._download_blob_via_javascript(blob_url, filename)
            if success:
                return success
            
            # Method 3: Sử dụng fetch API để lấy data
            logger.info("🔄 Method 3: Fetch API approach...")
            success = self._download_blob_via_fetch(blob_url, filepath)
            if success:
                return filepath
                
            logger.warning("❌ Tất cả methods thất bại")
            return None
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tải blob audio: {str(e)}")
            return None

    def _download_blob_via_base64(self, blob_url: str, filepath: str, audio_duration: float = 0) -> bool:
        """Convert blob URL thành base64 và lưu bằng Python"""
        try:
            # ⭐ CRITICAL: Adaptive wait time dựa trên audio duration
            if audio_duration > 0:
                # Công thức: Đợi tối thiểu 10s, hoặc 20% duration (whichever is larger)
                # Ví dụ: 5 phút audio (300s) → đợi max(10, 60) = 60 giây
                adaptive_wait = max(10, int(audio_duration * 0.2))
                logger.info(f"⏳ Audio duration = {audio_duration:.1f}s → Đợi thêm {adaptive_wait}s để đảm bảo buffer hoàn toàn...")
                time.sleep(adaptive_wait)
            else:
                logger.info("⏳ Đợi thêm 10s để đảm bảo audio đã được generate hoàn toàn...")
                time.sleep(10)

            # Set timeout cao hơn cho async script (240 giây cho audio dài)
            original_timeout = self.driver.timeouts.script
            script_timeout = max(120, int(audio_duration * 0.5)) if audio_duration > 0 else 120
            self.driver.set_script_timeout(script_timeout)
            logger.info(f"⏱️ Set script timeout = {script_timeout}s")
            
            # JavaScript để convert blob thành base64 với progress tracking
            convert_script = f"""
            const callback = arguments[arguments.length - 1];
            
            console.log('Starting blob conversion...');
            
            fetch('{blob_url}')
            .then(response => {{
                console.log('Fetch response received, converting to blob...');
                if (!response.ok) {{
                    throw new Error(`HTTP error! status: ${{response.status}}`);
                }}
                return response.blob();
            }})
            .then(blob => {{
                console.log(`Blob received, size: ${{blob.size}} bytes`);
                const reader = new FileReader();
                
                reader.onload = function() {{
                    console.log('FileReader completed successfully');
                    const result = reader.result;
                    if (result && result.includes(',')) {{
                        const base64Data = result.split(',')[1]; // Remove data URL prefix
                        console.log(`Base64 data length: ${{base64Data.length}}`);
                        callback(base64Data);
                    }} else {{
                        console.error('Invalid FileReader result:', result);
                        callback(null);
                    }}
                }};
                
                reader.onerror = function(error) {{
                    console.error('FileReader error:', error);
                    callback(null);
                }};
                
                reader.onprogress = function(e) {{
                    if (e.lengthComputable) {{
                        const progress = (e.loaded / e.total) * 100;
                        console.log(`Reading progress: ${{progress.toFixed(1)}}%`);
                    }}
                }};
                
                reader.readAsDataURL(blob);
            }})
            .catch(error => {{
                console.error('Blob conversion error:', error);
                callback(null);
            }});
            """
            
            # Execute JavaScript và lấy base64 data
            logger.debug("🔄 Converting blob to base64 (timeout: 60s)...")
            
            try:
                base64_data = self.driver.execute_async_script(convert_script)
            finally:
                # Restore original timeout
                self.driver.set_script_timeout(original_timeout)
            
            if not base64_data or not isinstance(base64_data, str):
                logger.warning(f"⚠️ Invalid base64 data received: {type(base64_data)}")
                return False
            
            logger.debug(f"📊 Base64 data length: {len(base64_data)} characters")
            
            # Decode base64 và lưu file
            try:
                audio_data = base64.b64decode(base64_data)
                logger.debug(f"📊 Decoded audio data size: {len(audio_data)} bytes")
            except Exception as decode_error:
                logger.warning(f"⚠️ Base64 decode failed: {str(decode_error)}")
                return False
            
            # Write file
            with open(filepath, 'wb') as f:
                f.write(audio_data)
            
            # Verify file
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                if file_size > 0:
                    logger.info(f"✅ Base64 method thành công: {filepath} ({file_size:,} bytes)")
                    return True
                else:
                    logger.warning("⚠️ File audio có kích thước 0")
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    return False
            else:
                logger.warning("⚠️ File không được tạo")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ Method base64 failed: {str(e)}")
            return False

    def _download_blob_via_javascript(self, blob_url: str, filename: str) -> Optional[str]:
        """Fallback method - sử dụng JavaScript download như cũ"""
        try:
            logger.debug("🔄 Using JavaScript download fallback...")
            
            # JavaScript để download blob
            download_script = f"""
            const link = document.createElement('a');
            link.href = '{blob_url}';
            link.download = '{filename}';
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            """
            
            # Track files trước khi download
            initial_files = set(os.listdir(self.download_path))
            
            # Execute download script
            self.driver.execute_script(download_script)
            
            # Đợi file download với progress
            max_wait = 30
            for i in range(max_wait):
                time.sleep(1)
                current_files = set(os.listdir(self.download_path))
                new_files = current_files - initial_files
                
                if new_files:
                    # Tìm file audio mới nhất
                    for new_filename in new_files:
                        if new_filename.endswith(('.mp3', '.wav', '.m4a', '.ogg')) or new_filename == filename:
                            filepath = os.path.join(self.download_path, new_filename)
                            file_size = os.path.getsize(filepath)
                            logger.info(f"✅ JavaScript download thành công: {filepath} ({file_size} bytes)")
                            return filepath
                
                # Progress indicator
                if i % 5 == 0:
                    logger.debug(f"⏳ Waiting for download... {i}/{max_wait}s")
            
            logger.warning("⚠️ JavaScript download timeout")
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ JavaScript download failed: {str(e)}")
            return None

    def _download_blob_via_fetch(self, blob_url: str, filepath: str) -> bool:
        """Sử dụng fetch API để lấy blob data với enhanced timeout"""
        try:
            logger.debug("🔄 Using fetch API approach...")
            
            # Set timeout cao hơn
            original_timeout = self.driver.timeouts.script
            self.driver.set_script_timeout(120)
            
            # JavaScript sử dụng fetch API
            fetch_script = f"""
            const callback = arguments[arguments.length - 1];
            
            fetch('{blob_url}')
            .then(response => {{
                console.log('Fetch response status:', response.status);
                if (!response.ok) {{
                    throw new Error(`Network response was not ok: ${{response.status}}`);
                }}
                return response.arrayBuffer();
            }})
            .then(buffer => {{
                console.log('ArrayBuffer received, size:', buffer.byteLength);
                const uint8Array = new Uint8Array(buffer);
                
                // Convert to base64 in chunks to avoid memory issues
                const chunkSize = 1024 * 1024; // 1MB chunks
                let binaryString = '';
                
                for (let i = 0; i < uint8Array.length; i += chunkSize) {{
                    const chunk = uint8Array.slice(i, i + chunkSize);
                    binaryString += String.fromCharCode.apply(null, chunk);
                }}
                
                const base64String = btoa(binaryString);
                console.log('Base64 conversion completed, length:', base64String.length);
                callback(base64String);
            }})
            .catch(error => {{
                console.error('Fetch API error:', error);
                callback(null);
            }});
            """
            
            # Execute và lấy data
            try:
                base64_data = self.driver.execute_async_script(fetch_script)
            finally:
                # Restore timeout
                self.driver.set_script_timeout(original_timeout)
            
            if not base64_data:
                logger.warning("⚠️ Fetch API không trả về data")
                return False
            
            # Decode và lưu file
            try:
                audio_data = base64.b64decode(base64_data)
                logger.debug(f"📊 Decoded audio size: {len(audio_data)} bytes")
            except Exception as decode_error:
                logger.warning(f"⚠️ Base64 decode failed: {str(decode_error)}")
                return False
            
            with open(filepath, 'wb') as f:
                f.write(audio_data)
            
            file_size = os.path.getsize(filepath)
            if file_size > 0:
                logger.info(f"✅ Fetch API download thành công: {filepath} ({file_size:,} bytes)")
                return True
            else:
                logger.warning("⚠️ File audio có kích thước 0")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ Fetch API failed: {str(e)}")
            return False
    
    def _verify_audio_file(self, filepath: str) -> bool:
        """Verify file là audio hợp lệ"""
        try:
            # Basic check: file size
            file_size = os.path.getsize(filepath)
            if file_size < 1024:  # Ít nhất 1KB
                logger.debug("File quá nhỏ để là audio")
                return False
            
            # Check file signature/magic bytes
            with open(filepath, 'rb') as f:
                header = f.read(12)
                
            # Common audio file signatures
            audio_signatures = [
                b'RIFF',      # WAV
                b'ID3',       # MP3 with ID3
                b'\xff\xfb',  # MP3 
                b'\xff\xf3',  # MP3
                b'\xff\xf2',  # MP3
                b'OggS',      # OGG
                b'fLaC',      # FLAC
                b'ftypM4A',   # M4A
            ]
            
            for signature in audio_signatures:
                if header.startswith(signature):
                    logger.debug(f"✅ Verified audio file signature: {signature}")
                    return True
            
            # Check for WAV format specifically
            if header.startswith(b'RIFF') and b'WAVE' in header:
                logger.debug("✅ Verified WAV format")
                return True
            
            logger.debug(f"⚠️ Unknown file signature: {header[:8]}")
            # Return True anyway vì có thể là format không phổ biến nhưng vẫn valid
            return True
            
        except Exception as e:
            logger.debug(f"⚠️ Cannot verify audio file: {str(e)}")
            return True  # Assume valid nếu không verify được

    def _download_via_context_menu(self, audio_element, order_in_story: int = None, output_filename: str = None) -> Optional[str]:
        """
        Thử download bằng context menu (right-click)
        
        Args:
            audio_element: Audio web element
            story_id: ID của story để tạo filename
            chapter_number: Số chương để tạo filename
            
        Returns:
            Optional[str]: Đường dẫn file đã tải
        """
        try:
            logger.info("Thử download bằng context menu...")
            
            # Đảm bảo download directory tồn tại
            if not os.path.exists(self.download_path):
                os.makedirs(self.download_path, exist_ok=True)
                logger.info(f"Đã tạo download directory: {self.download_path}")
            
            # Track files trước download
            initial_files = set(os.listdir(self.download_path))
            
            # Right click vào audio element
            actions = ActionChains(self.driver)
            actions.context_click(audio_element).perform()
            
            # Đợi context menu xuất hiện và tìm "Save audio as" hoặc tương tự
            time.sleep(1)
            
            # Thử các text có thể có trong context menu
            save_options = [
                "Save audio as",
                "Save as", 
                "Download",
                "Lưu âm thanh",
                "Lưu dưới dạng",
                "Tải xuống"
            ]
            
            for option_text in save_options:
                try:
                    # Tìm menu item
                    menu_item = self.driver.find_element(By.XPATH, f"//*[contains(text(), '{option_text}')]")
                    if menu_item.is_displayed():
                        menu_item.click()
                        logger.info(f"Clicked context menu: {option_text}")
                        break
                except NoSuchElementException:
                    continue
            
            # Đợi file download
            max_wait = 30
            for i in range(max_wait):
                time.sleep(1)
                current_files = set(os.listdir(self.download_path))
                new_files = current_files - initial_files
                
                if new_files:
                    for filename in new_files:
                        if filename.endswith(('.mp3', '.wav', '.m4a', '.ogg')):
                            filepath = os.path.join(self.download_path, filename)
                            
                            # Rename file to proper format if story_id and chapter_number are provided
                            new_filename = f"segment_{order_in_story}.wav"
                            if output_filename:
                                new_filename = output_filename
                            new_filepath = os.path.join(self.download_path, new_filename)
                            try:
                                os.rename(filepath, new_filepath)
                                logger.info(f"Đã đổi tên file từ {filename} thành {new_filename}")
                                filepath = new_filepath
                            except Exception as rename_error:
                                logger.warning(f"Không thể đổi tên file: {rename_error}")
                            
                            logger.info(f"Đã tải audio qua context menu: {filepath}")
                            return filepath
            
            logger.warning("Không download được qua context menu")
            return None
            
        except Exception as e:
            logger.error(f"Lỗi khi download qua context menu: {str(e)}")
            return None

    def generate_audio_from_text(self, text: str, wait_for_auth: bool = True, voice_name_1: str = None, voice_name_2: str = None, order_in_story: int = None, use_fast_paste: bool = True, output_filename = None) -> Dict[str, Any]:
        """
        Tạo audio từ text - tự động thử lại tối đa 3 lần nếu thất bại
        
        Args:
            text: Nội dung text cần convert
            wait_for_auth: Có đợi user đăng nhập thủ công không
            voice_name_1: Tên giọng nói 1
            voice_name_2: Tên giọng nói 2
            order_in_story: Thứ tự trong story để tạo filename
            use_fast_paste: True = paste nhanh, False = typing như người thật
            
        Returns:
            Dict[str, Any]: Kết quả với status và thông tin
        """
        max_retries = 3
        failure_logs = []  # Lưu lý do thất bại các lần
        backoff_time = 5  # Thời gian backoff ban đầu (giây)

        for attempt in range(1, max_retries + 1):
            result = {
                'success': False,
                'audio_path': None,
                'error': None,
                'message': ''
            }
            
            try:
                logger.info(f"🎯 Bắt đầu tạo audio (Lần thử {attempt}/{max_retries})")
                
                # Nếu không phải lần đầu, tắt và khởi động lại trình duyệt với profile khác
                if attempt > 1:
                    logger.info(f"🔄 Lần thử {attempt}: Tắt và khởi động lại trình duyệt...")
                    try:
                        self.close()
                        time.sleep(3)  # Đợi trình duyệt đóng hoàn toàn
                        # 🔥 Kill all existing browser instances before starting
                        logger.info("🧹 Killing all existing browser instances...")
                        config.kill_browser_instances(self.chrome_binary_path, verbose=True)
                    except Exception as close_error:
                        logger.warning(f"⚠️ Lỗi khi đóng trình duyệt: {str(close_error)}")

                    # 🎲 Chọn random profile khác từ pool
                    try:
                        from profile_pool_manager import get_profile_pool_manager
                        pool_manager = get_profile_pool_manager()
                        random_profile = pool_manager.get_random_profile(only_active=True)

                        if random_profile and random_profile != self.profile_name:
                            old_profile = self.profile_name
                            self.profile_name = random_profile
                            logger.info(f"🎲 Đổi profile từ '{old_profile}' sang '{self.profile_name}'")
                        else:
                            logger.warning("⚠️ Không tìm thấy profile khác trong pool, giữ nguyên profile hiện tại")
                    except Exception as profile_error:
                        logger.warning(f"⚠️ Lỗi khi chọn random profile: {str(profile_error)}")
                        logger.info("ℹ️ Tiếp tục với profile hiện tại")

                    # Reset driver về None để setup lại từ đầu
                    self.driver = None
                    self.wait = None
                    time.sleep(2)
                
                # Thiết lập driver
                if not self.driver:
                    logger.info(f"🚀 Khởi động trình duyệt Chrome...")
                    self.setup_driver()
                
                # Điều hướng đến trang
                logger.info(f"🌐 Điều hướng đến trang Generate Speech...")
                if not self.navigate_to_generate_speech():
                    raise Exception('Không thể tải trang Generate Speech')
                
                # Đợi xác thực nếu cần
                if wait_for_auth:
                    logger.info(f"🔐 Đợi xác thực...")
                    if not self.wait_for_authentication():
                        raise Exception('Timeout khi đợi xác thực')
                
                # Nhập text
                logger.info(f"⌨️ Nhập text vào form...")
                if not self.input_text(text, use_fast_paste=use_fast_paste, voice_name_1=voice_name_1, voice_name_2=voice_name_2):
                    raise Exception('Không thể nhập text')
                
                # Click generate
                logger.info(f"🖱️ Click nút Generate...")
                if not self.click_generate_button():
                    raise Exception('Không thể click nút Generate')
                
                # Đợi tạo audio với adaptive timeout
                logger.info(f"⏳ Đợi tạo audio...")
                text_length = len(text) if text else None
                if not self.wait_for_audio_generation(text_length=text_length):
                    raise Exception('Timeout khi đợi tạo audio')
                
                # Tải audio
                logger.info(f"💾 Tải file audio...")
                audio_path = self.download_audio(order_in_story=order_in_story, output_filename = output_filename)
                if not audio_path:
                    raise Exception('Không thể tải file audio')
                
                # Thành công
                result['success'] = True
                result['audio_path'] = audio_path
                result['message'] = f'Tạo audio thành công qua AI Studio (Lần thử {attempt}/{max_retries})'
                
                logger.info(f"✅ Hoàn thành tạo audio: {audio_path}")
                
                # ♻️ Giữ Chrome instance cho lần sau nếu thành công
                logger.info("♻️ Keeping Chrome instance alive for reuse...")
                
                self._human_delay(1, 2)
                return result
                
            except Exception as e:
                error_msg = str(e)
                failure_reason = f"Lần {attempt}/{max_retries}: {error_msg}"
                failure_logs.append(failure_reason)
                
                logger.error(f"❌ {failure_reason}")
                
                # Nếu chưa hết số lần thử, log và tiếp tục
                if attempt < max_retries:
                    # 🔥 Exponential backoff: Tăng thời gian chờ sau mỗi lần thất bại
                    # Nếu lỗi chứa "403" hoặc "rate limit", áp dụng backoff dài hơn
                    if '403' in error_msg.lower() or 'rate' in error_msg.lower() or 'quota' in error_msg.lower():
                        backoff_multiplier = 2 ** attempt  # 2^1, 2^2, 2^3... = 2s, 4s, 8s...
                        wait_time = backoff_time * backoff_multiplier
                        logger.warning(f"⚠️ Phát hiện lỗi rate limiting/403, áp dụng exponential backoff...")
                        logger.warning(f"⏳ Đợi {wait_time}s trước khi thử lại (lần {attempt}/{max_retries})...")
                        time.sleep(wait_time)
                    else:
                        logger.warning(f"⚠️ Thất bại lần {attempt}, sẽ thử lại sau khi khởi động lại trình duyệt...")
                        time.sleep(2)  # Đợi trước khi thử lại
                else:
                    # Hết số lần thử, return kết quả thất bại
                    logger.error(f"❌ Đã thất bại {max_retries} lần, dừng thử lại")
                    
                    # Log tất cả lý do thất bại
                    logger.error("📋 Tổng hợp lý do thất bại:")
                    for i, log in enumerate(failure_logs, 1):
                        logger.error(f"  {i}. {log}")
                    
                    result['success'] = False
                    result['error'] = error_msg
                    result['message'] = f'Thất bại sau {max_retries} lần thử'
                    result['failure_logs'] = failure_logs
                    
                    # Cleanup trình duyệt sau khi thất bại hoàn toàn
                    try:
                        logger.info("🧹 Cleanup trình duyệt sau khi thất bại hoàn toàn...")
                        self.close()
                    except Exception as cleanup_error:
                        logger.warning(f"⚠️ Lỗi khi cleanup: {str(cleanup_error)}")
                    
                    return result
        
        # Fallback (không nên đến đây)
        result['success'] = False
        result['error'] = 'Unknown error'
        result['message'] = 'Lỗi không xác định'
        result['failure_logs'] = failure_logs
        return result
    
    def _check_session_validity(self) -> bool:
        """
        Kiểm tra xem Chrome session có còn hợp lệ không
        
        Returns:
            bool: True nếu session hợp lệ hoặc chưa setup driver (có thể reuse)
        """
        try:
            # 🚨 CRITICAL: Prevent recovery loop during validation check
            if hasattr(self, '_recovery_attempts') and self._recovery_attempts > 2:
                logger.warning("❌ Recovery loop detected, session marked as invalid")
                return False
            
            # Nếu driver chưa được khởi tạo, return False để trigger setup mới
            if not self.driver:
                logger.debug("💤 Driver chưa được khởi tạo - cần setup driver mới")
                return False  # Changed to False để trigger setup_driver()
                
            # Nếu đã có driver, kiểm tra thực sự
            # Kiểm tra driver có còn kết nối không
            current_url = self.driver.current_url
            logger.debug(f"Current URL: {current_url}")
            
            # Kiểm tra window handles có còn không
            windows = self.driver.window_handles
            if not windows:
                logger.warning("Không còn window handles")
                return False
                
            # Thử thực hiện một thao tác đơn giản
            self.driver.execute_script("return document.readyState;")
            
            logger.debug("✅ Session hợp lệ")
            return True
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"❌ Session không hợp lệ: {error_msg}")
            
            # Classify error type for better handling
            error_type = self._classify_session_error(error_msg)
            logger.debug(f"🔍 Error type: {error_type}")
            
            # Mark session as invalid for recovery
            self._session_invalid = True
            
            return False
    
    def _classify_session_error(self, error_msg: str) -> str:
        """
        Phân loại loại lỗi session để xử lý phù hợp
        
        Args:
            error_msg: Error message từ exception
            
        Returns:
            str: Loại lỗi ('session_deleted', 'chrome_closed', 'connection_lost', 'unknown')
        """
        error_lower = error_msg.lower()
        
        if any(keyword in error_lower for keyword in ['invalid session id', 'session deleted']):
            return 'session_deleted'
        elif any(keyword in error_lower for keyword in ['target window already closed', 'window closed']):
            return 'chrome_closed'
        elif any(keyword in error_lower for keyword in ['chrome not reachable', 'disconnected', 'connection refused']):
            return 'connection_lost'
        elif any(keyword in error_lower for keyword in ['web view not found', 'no such window']):
            return 'webview_lost'
        else:
            return 'unknown'
    
    def _wait_for_page_ready(self, timeout: int = 30) -> bool:
        """
        Đợi trang load hoàn tất và sẵn sàng để tương tác
        
        Args:
            timeout: Thời gian chờ tối đa (giây)
            
        Returns:
            bool: True nếu trang đã sẵn sàng
        """
        try:
            logger.debug("🔄 Đợi trang load hoàn tất...")
            
            # Đợi document ready
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Đợi jQuery load xong (nếu có)
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda driver: driver.execute_script("return typeof jQuery === 'undefined' || jQuery.active === 0")
                )
            except:
                pass  # jQuery có thể không có
            
            # Đợi Angular load xong (nếu có)
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda driver: driver.execute_script("return typeof angular === 'undefined' || angular.element(document).injector().get('$http').pendingRequests.length === 0")
                )
            except:
                pass  # Angular có thể không có
            
            # Đợi thêm một chút để đảm bảo UI render xong
            self._human_delay(1, 2)
            
            logger.debug("✅ Trang đã sẵn sàng")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Timeout chờ trang ready: {str(e)}")
            return False
    
    def _recover_session(self) -> bool:
        """
        Khôi phục Chrome session khi bị mất kết nối
        
        Returns:
            bool: True nếu recovery thành công
        """
        try:
            # 🚨 CRITICAL: Prevent recovery loop
            if hasattr(self, '_recovery_attempts'):
                self._recovery_attempts += 1
                if self._recovery_attempts > 2:
                    logger.error("❌ Recovery loop detected, stopping recovery attempts")
                    self._recovery_attempts = 999  # Mark as failed permanently
                    return False
            else:
                self._recovery_attempts = 1
            
            logger.info(f"🔄 Bắt đầu recovery Chrome session (attempt {self._recovery_attempts}/2)...")
            
            # BƯỚC 1: Cleanup driver cũ nếu có
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                finally:
                    self.driver = None
                    self.wait = None
            
            # BƯỚC 2: Đợi một chút để cleanup hoàn tất
            time.sleep(2)
            
            # BƯỚC 3: Thiết lập lại driver
            logger.info("🔄 Thiết lập lại Chrome driver...")
            try:
                self.setup_driver()
            except Exception as setup_error:
                logger.error(f"❌ Setup driver failed during recovery: {setup_error}")
                return False
            
            # 🚨 CRITICAL: Check driver was created successfully
            if not self.driver:
                logger.error("❌ Driver is None after setup, recovery failed")
                return False
            
            # BƯỚC 4: Navigate lại đến trang cần thiết
            logger.info("🔄 Navigate lại đến AI Studio...")
            if not self.navigate_to_generate_speech():
                logger.error("❌ Không thể navigate đến AI Studio sau recovery")
                return False
                
            # BƯỚC 5: Kiểm tra authentication nếu cần
            logger.info("🔄 Kiểm tra authentication...")
            if self._is_signin_page():
                logger.info("🔑 Cần đăng nhập lại...")
                if not self.wait_for_authentication(timeout=120):
                    logger.error("❌ Đăng nhập thất bại sau recovery")
                    return False
            
            # BƯỚC 6: Kiểm tra và xử lý auth error
            if not self.check_and_handle_auth_error():
                logger.error("❌ Vẫn còn auth error sau recovery")
                return False
                
            logger.info("✅ Recovery session thành công!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Recovery session thất bại: {str(e)}")
            return False
    
    def close(self) -> None:
        """
        Đóng browser và dọn dẹp resources
        """
        try:
            if self.driver:
                try:
                    self.driver.quit()
                    logger.info("Đã đóng browser")
                except WebDriverException as e:
                    if "invalid session id" in str(e).lower():
                        logger.info("Browser session đã bị đóng trước đó")
                    else:
                        logger.warning(f"Lỗi khi đóng browser: {str(e)}")
                except Exception as e:
                    logger.warning(f"Lỗi khi đóng browser: {str(e)}")
                finally:
                    self.driver = None
                    self.wait = None
                    self._session_invalid = False
                
            # Nếu có Chrome process được khởi động bởi chúng ta, đóng nó
            if hasattr(self, 'chrome_process') and self.chrome_process and self.chrome_process.poll() is None:
                logger.info("Đang đóng Chrome process...")
                try:
                    # Thử terminate trước
                    self.chrome_process.terminate()
                    # Đợi 3 giây
                    self.chrome_process.wait(timeout=3)
                    logger.info("Chrome process đã được đóng")
                except subprocess.TimeoutExpired:
                    # Nếu không terminate được, kill
                    logger.warning("Force kill Chrome process...")
                    self.chrome_process.kill()
                    self.chrome_process.wait()
                    logger.info("Chrome process đã được force killed")
                except Exception as e:
                    logger.error(f"Lỗi khi đóng Chrome process: {str(e)}")
            
        except Exception as e:
            logger.error(f"Lỗi khi đóng browser: {str(e)}")
    