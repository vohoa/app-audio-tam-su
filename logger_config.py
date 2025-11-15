"""
Logging Configuration for Audio Generator Desktop App
Cấu hình logging tập trung với rotation và multiple handlers
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


class LoggerConfig:
    """Centralized logging configuration"""
    
    # Log directory
    LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
    
    # Log files
    MAIN_LOG_FILE = os.path.join(LOG_DIR, 'app.log')
    ERROR_LOG_FILE = os.path.join(LOG_DIR, 'error.log')
    SELENIUM_LOG_FILE = os.path.join(LOG_DIR, 'selenium.log')
    API_LOG_FILE = os.path.join(LOG_DIR, 'api.log')
    
    # Log format
    DETAILED_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    SIMPLE_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Max file size (10 MB)
    MAX_BYTES = 10 * 1024 * 1024
    
    # Backup count
    BACKUP_COUNT = 5
    
    @classmethod
    def setup_logging(cls):
        """Setup logging configuration for the entire application"""
        # Create logs directory if not exists
        os.makedirs(cls.LOG_DIR, exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler (INFO and above)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(cls.SIMPLE_FORMAT))
        root_logger.addHandler(console_handler)
        
        # Main file handler (DEBUG and above) - all logs
        main_file_handler = RotatingFileHandler(
            cls.MAIN_LOG_FILE,
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT,
            encoding='utf-8'
        )
        main_file_handler.setLevel(logging.DEBUG)
        main_file_handler.setFormatter(logging.Formatter(cls.DETAILED_FORMAT))
        root_logger.addHandler(main_file_handler)
        
        # Error file handler (ERROR and above only)
        error_file_handler = RotatingFileHandler(
            cls.ERROR_LOG_FILE,
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT,
            encoding='utf-8'
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(logging.Formatter(cls.DETAILED_FORMAT))
        root_logger.addHandler(error_file_handler)
        
        # Suppress verbose DEBUG logs from third-party libraries
        # Selenium logs are too verbose at DEBUG level
        logging.getLogger('selenium').setLevel(logging.WARNING)
        logging.getLogger('selenium.webdriver').setLevel(logging.WARNING)
        logging.getLogger('selenium.webdriver.remote').setLevel(logging.WARNING)
        logging.getLogger('selenium.webdriver.remote.remote_connection').setLevel(logging.WARNING)
        logging.getLogger('selenium.webdriver.common.service').setLevel(logging.WARNING)
        
        # Also suppress urllib3 (used by selenium)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
        
        # Log startup
        logging.info("=" * 80)
        logging.info(f"Application started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info("=" * 80)
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get a logger with the specified name"""
        return logging.getLogger(name)
    
    @classmethod
    def setup_module_logger(cls, module_name: str, log_file: str, level=logging.DEBUG):
        """
        Setup a dedicated logger for a specific module
        
        Args:
            module_name: Name of the module (e.g., 'selenium', 'api')
            log_file: Path to the log file
            level: Logging level
        """
        logger = logging.getLogger(module_name)
        logger.setLevel(level)
        
        # Module-specific file handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(cls.DETAILED_FORMAT))
        logger.addHandler(file_handler)
        
        return logger
    
    @classmethod
    def log_exception(cls, logger: logging.Logger, message: str, exc_info=True):
        """
        Log an exception with full traceback
        
        Args:
            logger: Logger instance
            message: Error message
            exc_info: Include exception info (default: True)
        """
        logger.error(message, exc_info=exc_info)
    
    @classmethod
    def log_function_call(cls, logger: logging.Logger, func_name: str, **kwargs):
        """
        Log a function call with parameters
        
        Args:
            logger: Logger instance
            func_name: Name of the function
            **kwargs: Function parameters
        """
        params = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
        logger.debug(f"Calling {func_name}({params})")
    
    @classmethod
    def log_function_result(cls, logger: logging.Logger, func_name: str, result: any, success: bool = True):
        """
        Log a function result
        
        Args:
            logger: Logger instance
            func_name: Name of the function
            result: Function result
            success: Whether the function succeeded
        """
        status = "SUCCESS" if success else "FAILED"
        logger.debug(f"{func_name} {status}: {result}")


# Decorator for automatic function logging
def log_function_execution(logger: logging.Logger):
    """
    Decorator to automatically log function execution
    
    Usage:
        @log_function_execution(logger)
        def my_function(arg1, arg2):
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(f"→ Entering {func_name}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"← Exiting {func_name} [SUCCESS]")
                return result
            except Exception as e:
                logger.error(f"← Exiting {func_name} [FAILED]: {str(e)}", exc_info=True)
                raise
        return wrapper
    return decorator


# Context manager for logging blocks
class LogBlock:
    """
    Context manager for logging blocks of code
    
    Usage:
        with LogBlock(logger, "Processing chapters"):
            # code here
    """
    def __init__(self, logger: logging.Logger, block_name: str):
        self.logger = logger
        self.block_name = block_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"▶ START: {self.block_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        if exc_type is None:
            self.logger.info(f"✓ END: {self.block_name} (Duration: {duration:.2f}s)")
        else:
            self.logger.error(f"✗ FAILED: {self.block_name} (Duration: {duration:.2f}s)", exc_info=True)
        return False  # Don't suppress exceptions


# Initialize logging on module import
def initialize_logging():
    """Initialize logging when module is imported"""
    LoggerConfig.setup_logging()
    
    # Setup module-specific loggers
    LoggerConfig.setup_module_logger('selenium', LoggerConfig.SELENIUM_LOG_FILE)
    LoggerConfig.setup_module_logger('api', LoggerConfig.API_LOG_FILE)
    
    return LoggerConfig.get_logger(__name__)


# Auto-initialize
logger = initialize_logging()
