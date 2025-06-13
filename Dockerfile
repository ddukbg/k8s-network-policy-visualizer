# Kubernetes Network Policy Visualizer 2.0
FROM python:3.11-slim

# 메타데이터
LABEL version="2.0.0"
LABEL description="Kubernetes Network Policy Visualizer"

# 환경 변수
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV DEBIAN_FRONTEND=noninteractive

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# kubectl 설치
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 권한 설정
RUN chmod +x app.py

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# 포트 노출
EXPOSE 5000

# 사용자 생성 및 권한 설정 (보안)
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# 엔트리포인트
CMD ["python", "app.py"] 