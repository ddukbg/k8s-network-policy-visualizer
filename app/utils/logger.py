import logging
import sys
from logging.handlers import RotatingFileHandler
from ..config import config

def setup_logger(name: str) -> logging.Logger:
    """애플리케이션 로거를 설정합니다."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL))

    # 포매터 생성
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 파일 핸들러 설정
    file_handler = RotatingFileHandler(
        'app.log', maxBytes=1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# 로거 인스턴스 생성
logger = setup_logger('k8s-network-policy-visualizer')