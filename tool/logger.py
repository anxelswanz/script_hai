import logging
import os
from datetime import datetime

def setup_logger():
    # 1. 确定日志存放路径
    log_dir = os.path.join(os.getcwd(), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 生成基础文件名 (例如: 2024-05-20_14-30-05)
    base_time_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # 2. 定义两个文件路径
    # 一个存常规日志，一个专门存错误日志
    info_log_path = os.path.join(log_dir, f"{base_time_str}_info.log")
    error_log_path = os.path.join(log_dir, f"{base_time_str}_error.log")

    # 3. 创建日志记录器
    logger = logging.getLogger("AppLogger")
    logger.setLevel(logging.DEBUG) # 总开关开启，允许所有级别流向 Handler

    if not logger.handlers:
        # 定义内容格式
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # --- 4. 常规日志处理器 (Info/Debug) ---
        # 记录 DEBUG 及以上所有信息，但如果你只想看 Info/Debug，可以设置为 INFO
        info_handler = logging.FileHandler(info_log_path, encoding="utf-8")
        info_handler.setLevel(logging.DEBUG)
        info_handler.setFormatter(formatter)

        # --- 5. 错误日志处理器 (Error/Critical) ---
        # 只记录 ERROR 级别及以上的日志
        error_handler = logging.FileHandler(error_log_path, encoding="utf-8")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)

        # --- 6. 控制台处理器 ---
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.DEBUG)

        # 将所有处理器添加到 logger
        logger.addHandler(info_handler)
        logger.addHandler(error_handler)
        logger.addHandler(console_handler)

    return logger

# 初始化
logger = setup_logger()

# --- 测试代码 ---
if __name__ == "__main__":
    logger.debug("这条信息会出现在 _info.log 和 控制台")
    logger.info("这条信息会出现在 _info.log 和 控制台")
    logger.warning("这条警告会出现在 _info.log 和 控制台")
    logger.error("这条错误会出现在 _info.log、_error.log 和 控制台")
    logger.critical("这条严重错误会出现在所有地方")