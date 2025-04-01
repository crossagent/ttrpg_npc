import logging
import os
# Removed RotatingFileHandler, using FileHandler now
# from logging.handlers import RotatingFileHandler
from datetime import datetime # Import datetime

LOG_DIR = "logs"
# LOG_FILENAME = "debug.log" # Removed fixed filename
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

def setup_logging(level=logging.INFO):
    """
    配置全局日志记录器。

    将日志输出到 rotating 文件，文件名包含当前日期。

    Args:
        level: 要设置的日志级别 (例如 logging.INFO, logging.DEBUG)。
    """
    # 创建日志目录
    os.makedirs(LOG_DIR, exist_ok=True)

    # --- Generate timestamp-based filename ---
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"debug_{timestamp_str}.log" # Include HHMMSS
    log_filepath = os.path.join(LOG_DIR, log_filename)
    # --- End filename generation ---

    # 获取根日志记录器
    logger = logging.getLogger()
    logger.setLevel(level) # 设置根日志记录器的级别

    # Since filename changes each time, we don't need to check for existing handlers for the *same* file.
    # However, we might want to clear previous handlers if the setup is called multiple times in one process.
    # For simplicity now, assume setup_logging is called once per process start.
    # If handlers exist, remove them to avoid duplication if setup is called again unexpectedly.
    if logger.handlers:
        logger.warning("Removing existing logging handlers before re-configuring.")
        for handler in logger.handlers[:]: # Iterate over a copy
            logger.removeHandler(handler)

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # --- 文件处理器 (Simple FileHandler, no rotation) ---
    # Using FileHandler because RotatingFileHandler requires a fixed base filename
    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    file_handler.setLevel(level) # 文件处理器也设置级别
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.warning("Debug log rotation is disabled due to timestamp in filename. Each run creates a new file.") # Warn user

    # --- 控制台处理器 (可选) ---
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(logging.WARNING)
    # console_handler.setFormatter(formatter)
    # logger.addHandler(console_handler)

    logger.info(f"Logging setup complete for file: {log_filepath}")

if __name__ == '__main__':
    # 简单测试日志配置
    print("Testing logging setup...")
    setup_logging(level=logging.DEBUG)
    logging.debug("This is a debug message.")
    logging.info("This is an info message.")
    logging.warning("This is a warning message.")
    logging.error("This is an error message.")
    logging.critical("This is a critical message.")
    # Update the test print message to reflect the new filename format
    print(f"Log messages should be in {os.path.join(LOG_DIR, f'debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')}")
