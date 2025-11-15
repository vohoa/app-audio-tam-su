"""
Human-like delay utilities for automation
Provides realistic delays to mimic human behavior
"""

import time
import random
import logging
from automation_constants import Delays

logger = logging.getLogger(__name__)


class HumanDelay:
    """
    Utility class for adding human-like delays to automation
    """

    @staticmethod
    def standard(min_seconds: float = None, max_seconds: float = None) -> None:
        """
        Add a standard human-like delay

        Args:
            min_seconds: Minimum delay in seconds (default from Delays.HUMAN_MIN)
            max_seconds: Maximum delay in seconds (default from Delays.HUMAN_MAX)
        """
        min_sec = min_seconds if min_seconds is not None else Delays.HUMAN_MIN
        max_sec = max_seconds if max_seconds is not None else Delays.HUMAN_MAX
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    @staticmethod
    def typing_char() -> None:
        """
        Delay for typing a single character (80-120ms)
        Mimics average typing speed of 50-75 WPM
        """
        delay = random.uniform(Delays.TYPING_MIN, Delays.TYPING_MAX)
        time.sleep(delay)

    @staticmethod
    def typing_punctuation() -> None:
        """
        Delay for typing punctuation (150-300ms)
        Longer pause at punctuation marks
        """
        delay = random.uniform(Delays.PUNCTUATION_MIN, Delays.PUNCTUATION_MAX)
        time.sleep(delay)

    @staticmethod
    def click() -> None:
        """
        Delay after clicking an element (200-500ms)
        """
        delay = random.uniform(Delays.CLICK_MIN, Delays.CLICK_MAX)
        time.sleep(delay)

    @staticmethod
    def scroll() -> None:
        """
        Delay after scrolling (300-600ms)
        """
        delay = random.uniform(Delays.SCROLL_MIN, Delays.SCROLL_MAX)
        time.sleep(delay)

    @staticmethod
    def paste() -> None:
        """
        Delay after pasting text (200-400ms)
        """
        delay = random.uniform(Delays.PASTE_MIN, Delays.PASTE_MAX)
        time.sleep(delay)

    @staticmethod
    def element_interaction() -> None:
        """
        Short delay between element interactions (100-300ms)
        """
        delay = random.uniform(Delays.ELEMENT_MIN, Delays.ELEMENT_MAX)
        time.sleep(delay)

    @staticmethod
    def custom(min_seconds: float, max_seconds: float) -> None:
        """
        Custom delay with specified range

        Args:
            min_seconds: Minimum delay in seconds
            max_seconds: Maximum delay in seconds
        """
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)

    @staticmethod
    def for_text_length(text: str) -> None:
        """
        Calculate and apply delay based on text length
        Simulates realistic typing time

        Args:
            text: The text that would be typed
        """
        # Count punctuation marks for longer delays
        from automation_constants import PUNCTUATION_CHARS

        char_count = len(text)
        punct_count = sum(1 for c in text if c in PUNCTUATION_CHARS)
        regular_chars = char_count - punct_count

        # Calculate total typing time
        char_delay = regular_chars * random.uniform(Delays.TYPING_MIN, Delays.TYPING_MAX)
        punct_delay = punct_count * random.uniform(Delays.PUNCTUATION_MIN, Delays.PUNCTUATION_MAX)
        total_delay = char_delay + punct_delay

        # Cap at reasonable max (5 seconds for very long text)
        total_delay = min(total_delay, 5.0)

        logger.debug(f"Calculated typing delay: {total_delay:.2f}s for {char_count} chars")
        time.sleep(total_delay)


class DelayContext:
    """
    Context manager for timed operations with automatic logging

    Usage:
        with DelayContext("Loading page"):
            # operation
            pass
    """

    def __init__(self, operation_name: str):
        """
        Args:
            operation_name: Name of the operation for logging
        """
        self.operation_name = operation_name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        logger.debug(f"⏱️ Starting: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        if exc_type is None:
            logger.debug(f"✅ Completed: {self.operation_name} ({elapsed:.2f}s)")
        else:
            logger.debug(f"❌ Failed: {self.operation_name} ({elapsed:.2f}s)")
        return False  # Don't suppress exceptions
