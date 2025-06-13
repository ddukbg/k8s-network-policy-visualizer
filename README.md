# Kubernetes Network Policy Visualizer 🚀

![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0.0-brightgreen.svg)
![Socket.IO](https://img.shields.io/badge/Socket.IO-5.3.6-blue.svg)

> **실제 Kubernetes 클러스터의 네트워크 정책을 시각화하는 현대적인 웹 애플리케이션**

Kubernetes 클러스터의 Pod, Deployment, NetworkPolicy를 실시간으로 수집하여 직관적인 그래프로 시각화합니다. 복잡한 네트워크 구성을 쉽게 이해하고 네트워크 정책의 영향을 시뮬레이션할 수 있습니다.

## ✨ 주요 기능

### 🎯 핵심 기능
- **실시간 클러스터 연동**: `kubectl`을 통한 실제 클러스터 데이터 수집
- **Pod & Deployment 시각화**: 두 가지 리소스 타입 간 전환 가능
- **네트워크 정책 매핑**: NetworkPolicy와 리소스 간의 관계 시각화
- **통신 시뮬레이션**: 실제 네트워크 정책 기반 통신 가능성 검증

### 🎨 사용자 경험
- **현대적인 UI**: Material Design 기반의 직관적인 인터페이스
- **실시간 업데이트**: WebSocket을 통한 실시간 상태 반영
- **상세 정보 패널**: 클릭으로 리소스/정책 상세 정보 확인
- **반응형 디자인**: 모든 디바이스에서 완벽한 사용 경험

### ⚡ 성능 최적화
- **스마트 캐싱**: 클러스터 데이터 캐싱으로 빠른 응답 (1-2초)
- **비동기 처리**: 백그라운드 데이터 수집
- **효율적인 렌더링**: Cytoscape.js 기반 고성능 그래프 렌더링

## 🖼️ 스크린샷

### Pod 뷰
- 🟢 Pod 노드 (원형)
- 🔷 NetworkPolicy 노드 (다이아몬드)
- 실시간 클러스터 데이터 (30+ Pod, 4개 정책)

### Deployment 뷰  
- 🟣 Deployment 노드 (육각형)
- 🔷 NetworkPolicy 노드 (다이아몬드)
- 논리적 그룹핑으로 간소화된 뷰

## 🚀 빠른 시작

### 전제 조건

- **Python 3.11+**
- **kubectl** 설치 및 클러스터 접근 권한 설정
- **활성화된 Kubernetes 클러스터** (로컬 또는 원격)

### 설치 및 실행

#### 1. 로컬 설치

```bash
# 저장소 클론
git clone https://github.com/your-username/k8s-network-policy-visualizer.git
cd k8s-network-policy-visualizer

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt

# kubectl 연결 확인
kubectl cluster-info

# 애플리케이션 실행
python app.py
```

#### 2. Docker 실행

```bash
# 이미지 빌드
docker build -t k8s-netpol-visualizer .

# 컨테이너 실행 (kubeconfig 마운트 필요)
docker run -d \
  --name netpol-visualizer \
  -p 5000:5000 \
  -v ~/.kube:/home/appuser/.kube:ro \
  k8s-netpol-visualizer
```

#### 3. 환경 변수 설정 (선택사항)

```bash
# .env 파일 생성
export SECRET_KEY="your-secret-key"
export FLASK_ENV="development"
export KUBECTL_TIMEOUT=30
export LOG_LEVEL="INFO"
```

## 🎯 사용법

### 기본 사용법
1. **웹 브라우저**에서 `http://localhost:5000` 접속
2. **리소스 타입** 선택 (Pod ↔ Deployment 전환)
3. **그래프에서 노드 클릭**하여 상세 정보 확인
4. **실시간 업데이트**로 클러스터 변경사항 자동 반영

### 고급 기능
- **통신 시뮬레이션**: 소스/대상 선택 후 통신 가능성 검증
- **정책 분석**: NetworkPolicy 클릭으로 적용 범위 확인
- **헬스 체크**: `/api/health`로 클러스터 연결 상태 확인

## 🛠️ API 엔드포인트

| 엔드포인트 | 메서드 | 설명 | 응답 시간 |
|------------|--------|------|-----------|
| `/` | GET | 메인 웹 인터페이스 | - |
| `/api/health` | GET | 클러스터 연결 상태 확인 | ~100ms |
| `/api/data?resource_type=pod` | GET | Pod 그래프 데이터 | ~1.5s |
| `/api/data?resource_type=deployment` | GET | Deployment 그래프 데이터 | ~0.8s |
| `/api/policy/<namespace>/<name>` | GET | NetworkPolicy 상세 정보 | ~200ms |
| `/api/resource/<type>/<namespace>/<name>` | GET | 리소스 상세 정보 | ~200ms |
| `/api/simulate` | POST | 네트워크 통신 시뮬레이션 | ~300ms |

### 실제 성능 데이터
- **클러스터 규모**: 57개 Pod, 30개 Deployment, 4개 NetworkPolicy
- **응답 시간**: Pod 뷰 1.79s, Deployment 뷰 0.76s
- **그래프 크기**: Pod 뷰 61 nodes/30 edges, Deployment 뷰 34 nodes/10 edges

## 🏗️ 아키텍처

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask Backend  │    │   Kubernetes    │
│   (Cytoscape.js)│◄──►│   (Socket.IO)    │◄──►│   Cluster       │
│   + Material UI │    │   + 실시간 캐싱   │    │   (kubectl)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 기술 스택

**Backend**
- Flask 3.0 + Socket.IO (실시간 통신)
- Pydantic (데이터 검증)
- Structlog (구조화된 로깅)
- Subprocess + kubectl (클러스터 연동)

**Frontend**
- Cytoscape.js (그래프 시각화)
- Material Icons + Modern CSS
- WebSocket (실시간 업데이트)

**Infrastructure**
- Docker 지원
- Kubernetes 네이티브

## 🔧 개발자 가이드

### 프로젝트 구조

```
k8s-network-policy-visualizer/
├── src/
│   ├── models/           # Pydantic 데이터 모델
│   │   ├── __init__.py
│   │   ├── graph.py      # 그래프 데이터 모델
│   │   ├── kubernetes.py # K8s 리소스 모델
│   │   └── network.py    # 네트워크 정책 모델
│   └── services/         # 비즈니스 로직
│       ├── __init__.py
│       ├── kubernetes_service.py  # 클러스터 연동
│       └── graph_service.py       # 그래프 생성
├── templates/
│   └── index.html        # 메인 웹 인터페이스
├── static/
│   ├── styles.css        # 스타일시트
│   └── scripts.js        # 프론트엔드 로직
├── tests/                # 테스트 코드
├── samples/              # 샘플 데이터
├── app.py                # 메인 애플리케이션
├── config.py             # 설정 관리
├── requirements.txt      # Python 의존성
├── Dockerfile           # Docker 이미지
└── .gitignore           # Git 제외 파일
```

### 로컬 개발 환경

```bash
# 개발 모드 실행
export FLASK_ENV=development
python app.py

# 로그 확인
tail -f server.log

# 테스트 실행 (구현 예정)
pytest tests/
```

## 📊 성능 최적화

### 구현된 최적화
- **메모리 캐싱**: 클러스터 데이터 캐싱으로 반복 요청 최적화
- **비동기 처리**: kubectl 명령어 비동기 실행
- **데이터 압축**: JSON 응답 최적화
- **스마트 렌더링**: 노드 타입별 차별화된 렌더링

### 성능 지표
- **초기 로딩**: 1-2초 (클러스터 크기에 따라)
- **리소스 타입 전환**: 0.5-1초
- **상세 정보 조회**: 200-300ms
- **실시간 업데이트**: WebSocket 기반 즉시 반영

## 🔍 문제 해결

### 일반적인 문제

**1. kubectl 연결 오류**
```bash
# 클러스터 연결 확인
kubectl cluster-info
kubectl get nodes

# kubeconfig 경로 확인
echo $KUBECONFIG
```

**2. 포트 충돌 (5000번 포트)**
```bash
# macOS AirPlay 수신기 비활성화
# 시스템 환경설정 > 일반 > AirDrop 및 Handoff

# 또는 다른 포트 사용
export PORT=8080
python app.py
```

**3. 권한 오류**
```bash
# 클러스터 권한 확인
kubectl auth can-i get pods --all-namespaces
kubectl auth can-i get networkpolicies --all-namespaces
```

## 🤝 기여하기

1. Fork 프로젝트
2. Feature 브랜치 생성: `git checkout -b feature/AmazingFeature`
3. 변경사항 커밋: `git commit -m 'Add some AmazingFeature'`
4. 브랜치에 Push: `git push origin feature/AmazingFeature`
5. Pull Request 생성

### 개발 가이드라인
- 코드 스타일: Black 포맷터 사용
- 타입 힌트: 모든 함수에 타입 힌트 추가
- 로깅: Structlog를 사용한 구조화된 로깅
- 테스트: 새로운 기능에 대한 테스트 코드 작성

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🆘 지원 및 문의

- **Issues**: [GitHub Issues](https://github.com/your-username/k8s-network-policy-visualizer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/k8s-network-policy-visualizer/discussions)

## 🙏 감사의 말

- [Cytoscape.js](https://cytoscape.org/) - 강력한 그래프 시각화 라이브러리
- [Flask](https://flask.palletsprojects.com/) - 유연한 웹 프레임워크
- [Kubernetes](https://kubernetes.io/) - 컨테이너 오케스트레이션 플랫폼

---

⭐ **이 프로젝트가 도움이 되었다면 별표를 눌러주세요!**
