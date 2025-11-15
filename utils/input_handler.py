"""
Input handling strategies for web automation
Provides different methods to input text into web elements
"""

import logging
from abc import ABC, abstractmethod
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.keys import Keys
from automation_constants import PUNCTUATION_CHARS
from .delays import HumanDelay

logger = logging.getLogger(__name__)


class InputStrategy(ABC):
    """
    Abstract base class for text input strategies
    """

    @abstractmethod
    def input_text(self, driver, element: WebElement, text: str) -> bool:
        """
        Input text into the element using a specific strategy

        Args:
            driver: Selenium WebDriver instance
            element: Web element to input text into
            text: Text to input

        Returns:
            bool: True if successful, False otherwise
        """
        pass


class FastPasteStrategy(InputStrategy):
    """
    Fast text input using clipboard paste or JavaScript injection
    Best for long texts where speed is priority
    """

    def input_text(self, driver, element: WebElement, text: str) -> bool:
        """
        Fast paste using JavaScript injection (optimized for long text)

        Priority:
        1. JavaScript injection with value property (fastest, most reliable)
        2. JavaScript injection with textContent (fallback for contenteditable)
        3. Direct send_keys (last resort)
        """
        try:
            # Clear existing text
            element.clear()
            HumanDelay.element_interaction()

            # Click into element
            element.click()
            HumanDelay.element_interaction()

            # Select all and delete
            element.send_keys(Keys.CONTROL + "a")
            HumanDelay.element_interaction()
            element.send_keys(Keys.DELETE)
            HumanDelay.element_interaction()

            # Method 1: JavaScript injection with proper escaping
            try:
                # Use arguments[0] to pass text directly (avoids string length limits)
                js_script = '''
                var element = arguments[0];
                var text = arguments[1];

                // Try setting value (for input/textarea)
                if (element.tagName === 'TEXTAREA' || element.tagName === 'INPUT') {
                    element.value = text;
                } else if (element.isContentEditable) {
                    // For contenteditable elements
                    element.textContent = text;
                } else {
                    element.value = text;
                }

                // Trigger events to notify the page
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
                '''
                driver.execute_script(js_script, element, text)
                logger.info(f"✅ Fast paste via JavaScript successful ({len(text)} chars)")
                HumanDelay.paste()
                return True

            except Exception as js_error:
                logger.warning(f"⚠️ JavaScript method 1 failed: {str(js_error)}")

            # Method 2: Direct send_keys (slowest fallback)
            logger.info("🔄 Fallback: Using direct send_keys...")
            element.send_keys(text)
            logger.info(f"✅ Fallback send_keys successful ({len(text)} chars)")
            HumanDelay.paste()
            return True

        except Exception as e:
            logger.error(f"❌ All paste methods failed: {str(e)}")
            return False


class HumanTypeStrategy(InputStrategy):
    """
    Human-like typing with realistic delays
    Best for short texts where natural behavior is important
    """

    def input_text(self, driver, element: WebElement, text: str) -> bool:
        """
        Type text character by character with human-like delays
        """
        try:
            # Clear existing text
            element.clear()
            HumanDelay.element_interaction()

            # Type character by character
            for char in text:
                try:
                    element.send_keys(char)

                    # Different delays for different character types
                    if char in PUNCTUATION_CHARS:
                        HumanDelay.typing_punctuation()
                    else:
                        HumanDelay.typing_char()

                except Exception as char_error:
                    logger.warning(f"⚠️ Error typing character '{char}': {str(char_error)}")
                    # Fallback: send remaining text at once
                    element.clear()
                    element.send_keys(text)
                    break

            logger.info("✅ Human-like typing completed")
            return True

        except Exception as e:
            logger.error(f"❌ Human typing failed: {str(e)}")
            # Final fallback
            try:
                element.clear()
                element.send_keys(text)
                logger.info("✅ Fallback send_keys successful")
                return True
            except Exception as fallback_error:
                logger.error(f"❌ All typing methods failed: {str(fallback_error)}")
                return False


class InputHandler:
    """
    Main handler for text input with strategy selection
    """

    def __init__(self, driver):
        """
        Args:
            driver: Selenium WebDriver instance
        """
        self.driver = driver
        self.strategies = {
            'fast': FastPasteStrategy(),
            'human': HumanTypeStrategy(),
        }

    def input_text(self, element: WebElement, text: str, mode: str = 'fast') -> bool:
        """
        Input text using the specified strategy

        Args:
            element: Web element to input text into
            text: Text to input
            mode: Input mode - 'fast' or 'human' (default: 'fast')

        Returns:
            bool: True if successful, False otherwise

        Raises:
            ValueError: If mode is not recognized
        """
        if mode not in self.strategies:
            raise ValueError(f"Unknown input mode: {mode}. Available: {list(self.strategies.keys())}")

        strategy = self.strategies[mode]
        logger.info(f"📝 Inputting text using '{mode}' strategy ({len(text)} chars)")

        return strategy.input_text(self.driver, element, text)

    def add_strategy(self, name: str, strategy: InputStrategy) -> None:
        """
        Add a custom input strategy

        Args:
            name: Name for the strategy
            strategy: InputStrategy instance
        """
        self.strategies[name] = strategy
        logger.info(f"✅ Added custom input strategy: {name}")
