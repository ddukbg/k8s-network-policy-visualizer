from flask import Flask
from flask_socketio import SocketIO
from threading import Lock
from .config import config
from .utils.logger import logger

socketio = SocketIO(async_mode='threading')
cache_lock = Lock()
cached_graph_data = {
    'deployment': None,
    'pod': None
}

def create_app():
    app = Flask(__name__, 
                template_folder='templates',    # 명시적으로 템플릿 폴더 지정
                static_folder='static')         # 명시적으로 정적 파일 폴더 지정
    
    # 설정 적용
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['DEBUG'] = config.DEBUG

    # 블루프린트 등록
    from .routes.api import api
    app.register_blueprint(api, url_prefix='/')  # url_prefix 추가

    # 에러 핸들러 등록
    from .routes.error_handlers import register_error_handlers
    register_error_handlers(app)

    socketio.init_app(app)
    
    logger.info('Application initialized successfully')
    return app