import os, logging
from datetime import datetime

# 假设 get_abs_path 已经定义好
# from path_tool import get_abs_path

# 1. 基础路径设定
LOG_ROOT = os.path.abspath("logs")

# 2. 定义统一的格式对象（不要用 basicConfig 赋值）
LOG_FORMATTER = logging.Formatter(
    "%(asctime)s-%(name)s-%(levelname)s-%(filename)s:%(lineno)d - %(message)s"
)


def get_logger(name: str = "performance_test/log", log_file=None) -> logging.Logger:
    logger = logging.ge=tLogger(name)

    # 避免重复添加 Handler
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)

    # --- 关键修改部分：处理文件夹层级 ---
    if not log_file:
        # 将 name 中的 '/' 转换为系统路径分隔符
        sub_dir = os.path.join(LOG_ROOT, *name.split('/'))
        # 确保目录存在（例如：logs/performance_test/log/）
        os.makedirs(sub_dir, exist_ok=True)

        file_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}.log"
        log_file = os.path.join(sub_dir, file_name)

    # 控制台 Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(LOG_FORMATTER)
    logger.addHandler(console_handler)

    # 文件 Handler
    file_handler = logging.FileHandler(log_file, mode='a', encoding="utf-8")
    file_handler.setFormatter(LOG_FORMATTER)
    logger.addHandler(file_handler)

    return logger


# 使用方式
logger = get_logger()

if __name__ == "__main__":
    logger.info("测试：日志已存入 performance_test/log 文件夹")