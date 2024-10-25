from app import create_app, socketio
from app.utils.helpers import monitor_changes
from app.utils.logger import logger
from threading import Thread
from app.config import config

app = create_app()

if __name__ == '__main__':
    logger.info("Starting application...")
    
    # 모니터링 스레드 시작
    monitor_thread = Thread(target=monitor_changes)
    monitor_thread.daemon = True
    monitor_thread.start()
    logger.info("Monitoring thread started")

    # 애플리케이션 실행
    host = '0.0.0.0'
    port = 5000
    logger.info(f"Starting server on {host}:{port}")
    socketio.run(app, host=host, port=port, debug=config.DEBUG)