import os
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Config:
    """애플리케이션 설정"""
    SECRET_KEY: str
    DEBUG: bool
    MONITOR_INTERVAL: int  # 모니터링 간격(초)
    LOG_LEVEL: str
    
    @classmethod
    def from_env(cls) -> 'Config':
        """환경 변수에서 설정을 로드합니다."""
        return cls(
            SECRET_KEY=os.getenv('SECRET_KEY', 'your-secret-key-change-it'),
            DEBUG=os.getenv('DEBUG', 'False').lower() == 'true',
            MONITOR_INTERVAL=int(os.getenv('MONITOR_INTERVAL', '60')),
            LOG_LEVEL=os.getenv('LOG_LEVEL', 'INFO')
        )

class ProductionConfig(Config):
    """운영 환경 설정"""
    @classmethod
    def from_env(cls) -> 'Config':
        config = super().from_env()
        config.DEBUG = False
        return config

# 설정 인스턴스 생성
config = Config.from_env() if os.getenv('FLASK_ENV') != 'production' else ProductionConfig.from_env()