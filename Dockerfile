# 멀티스테이지 빌드 사용
FROM python:3.11-slim as builder

WORKDIR /app

# Poetry 설치 및 의존성 관리
RUN pip install --no-cache-dir poetry

# 프로젝트 메타데이터 복사
COPY pyproject.toml poetry.lock ./

# 의존성 설치
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# 런타임 스테이지
FROM python:3.11-slim

WORKDIR /app

# kubectl 설치
RUN apt-get update && apt-get install -y curl \
    && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/ \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 빌더 스테이지에서 설치된 패키지 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# 애플리케이션 코드 복사
COPY . .

# 환경 변수 설정
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# 실행
CMD ["python", "run.py"]