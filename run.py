import uvicorn
from dotenv import load_dotenv
from loguru import logger

# 加载 .env 环境变量
load_dotenv()

if __name__ == "__main__":
    # 配置loguru
    logger.remove()
    logger.add(
        "logs/uvicorn.log",
        rotation="500 MB",
        retention="10 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    )

    logger.info("Starting uvicorn server")

    uvicorn.run("apps.main:app", host="0.0.0.0", port=9999, reload=True)
