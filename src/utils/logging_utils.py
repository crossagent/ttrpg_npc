import logging
import os
from logging.handlers import RotatingFileHandler
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

    # --- Generate date-based filename ---
    current_date_str = datetime.now().strftime("%Y%m%d")
    log_filename = f"debug_{current_date_str}.log"
    log_filepath = os.path.join(LOG_DIR, log_filename)
    # --- End filename generation ---

    # 获取根日志记录器
    logger = logging.getLogger()
    logger.setLevel(level) # 设置根日志记录器的级别

    # 如果已经有处理器，则不重复添加，避免日志重复
    # 检查处理器是否已经是针对今天的文件，如果是，则不添加
    # （更复杂的场景可能需要移除旧日期的处理器，但这里简化处理）
    already_configured = False
    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler) and handler.baseFilename == log_filepath:
            already_configured = True
            break
        # Optional: Remove handlers for previous dates if needed
        # elif isinstance(handler, RotatingFileHandler) and os.path.basename(handler.baseFilename).startswith("debug_"):
        #     logger.removeHandler(handler)

    if already_configured:
        logger.debug("Logging already configured for today's file.")
        return

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # --- 文件处理器 (Rotating) ---
    file_handler = RotatingFileHandler(
        log_filepath,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(level) # 文件处理器也设置级别
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

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
    print(f"Log messages should be in {os.path.join(LOG_DIR, f'debug_{datetime.now().strftime("%Y%m%d")}.log')}")
