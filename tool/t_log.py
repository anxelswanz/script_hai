from logger import logger


def my_function():
    logger.info("这是一条普通信息")
    logger.error("哎呀，程序出错了！")

    x = 10
    logger.debug(f"当前变量 x 的值为: {x}")


if __name__ == "__main__":
    my_function()