import os
from typing import Dict, Any

class Config:
    """기본 설정 클래스"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Kubernetes 설정
    KUBECTL_TIMEOUT = int(os.environ.get('KUBECTL_TIMEOUT', 5))
    CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 60))
    
    # 애플리케이션 설정
    APP_HOST = os.environ.get('APP_HOST', '0.0.0.0')
    APP_PORT = int(os.environ.get('APP_PORT', 5000))
    
    # Socket.IO 설정
    SOCKETIO_ASYNC_MODE = 'threading'
    SOCKETIO_LOGGER = False
    SOCKETIO_ENGINEIO_LOGGER = False

class DevelopmentConfig(Config):
    """개발 환경 설정"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """프로덕션 환경 설정"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """테스트 환경 설정"""
    TESTING = True
    DEBUG = True

# 환경별 설정 매핑
config_map: Dict[str, Any] = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(env_name: str = None) -> Config:
    """환경에 맞는 설정 객체 반환"""
    if env_name is None:
        env_name = os.environ.get('FLASK_ENV', 'default')
    
    return config_map.get(env_name, DevelopmentConfig) 