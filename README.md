# Kubernetes Network Policy Visualizer

[한국어](#한국어) | [English](#english)

![License](https://img.shields.io/badge/license-MIT-green.svg)
![Flask](https://img.shields.io/badge/Flask-2.3.2-brightgreen.svg)
![Socket.IO](https://img.shields.io/badge/Socket.IO-4.7.2-blue.svg)
![Cytoscape.js](https://img.shields.io/badge/Cytoscape.js-3.19.1-orange.svg)

---
# *Kubectl이 설치된 환경에서 사용 가능합니다.(개발 진행중)*

## 한국어

### 목차

- [소개](#소개)
- [특징](#특징)
- [사용된 기술](#사용된-기술)
- [설치](#설치)
- [구성](#구성)
- [사용법](#사용법)
- [아키텍처](#아키텍처)
- [API 엔드포인트](#api-엔드포인트)
- [프론트엔드 개요](#프론트엔드-개요)
- [백엔드 개요](#백엔드-개요)
- [테스트](#테스트)
- [기여](#기여)
- [라이선스](#라이선스)
- [문의](#문의)

### 소개
<img width="922" alt="image" src="https://github.com/user-attachments/assets/76eed3e3-df8f-432e-9491-53e472b2f557">

**Kubernetes Network Policy Visualizer**는 Kubernetes 클러스터 내의 네트워크 정책을 시각화하고 분석하는 데 도움을 주는 강력한 웹 기반 도구입니다. 네트워크 정책이 Pod와 어떻게 상호 작용하는지를 명확한 그래픽으로 제공하여 복잡한 네트워크 구성을 이해하고 관리하는 것을 간소화합니다. 이 도구는 실시간 업데이트를 통해 시각화가 클러스터의 현재 상태와 항상 동기화되도록 보장합니다.

***프로젝트를 만든 이유:*** 네트워크 정책이 적용된 대상을 YAML 파일을 통해 확인하는 것이 번거로웠습니다. 이를 보다 직관적이고 쉽게 파악할 수 있도록 시각화 도구를 개발하게 되었습니다.

### 특징

- **실시간 시각화:** Kubernetes 클러스터에서 변경 사항이 발생할 때 네트워크 정책 그래프가 자동으로 업데이트됩니다.
- **Ingress 및 Egress 표현:** 서로 다른 화살표 스타일과 색상을 사용하여 Ingress와 Egress 정책을 구분합니다.
- **포트 정보 표시:** 포트 수에 상관없이 각 정책 규칙의 포트 정보를 명확하게 표시합니다.
- **네임스페이스 필터링:** 직관적인 체크박스 인터페이스를 통해 Kubernetes 네임스페이스별로 정책과 Pod를 필터링할 수 있으며, "ALL" 옵션을 포함합니다.
- **검색 기능:** 검색 창을 사용하여 특정 Pod 또는 정책을 쉽게 검색할 수 있습니다.
- **상세 정보 패널:** 정책 또는 Pod 노드를 클릭하면 Ingress 및 Egress 규칙, 관련 포트, 레이블, 상태 등 포괄적인 세부 정보를 확인할 수 있습니다.
- **반응형 디자인:** 다양한 화면 크기에 최적화되어 데스크탑, 태블릿, 모바일 장치에서의 사용성을 보장합니다.
- **Docker 지원:** 컨테이너화되어 손쉬운 배포 및 확장이 가능합니다.

### 사용된 기술

- **백엔드:**
  - [Flask](https://flask.palletsprojects.com/) - 경량 웹 애플리케이션 프레임워크.
  - [Flask-SocketIO](https://flask-socketio.readthedocs.io/) - 클라이언트와 서버 간의 실시간 양방향 통신을 가능하게 합니다.
  - [Kubernetes `kubectl`](https://kubernetes.io/docs/reference/kubectl/overview/) - Kubernetes 클러스터와 상호 작용하는 커맨드라인 도구.
  
- **프론트엔드:**
  - [Cytoscape.js](https://js.cytoscape.org/) - 시각화 및 분석을 위한 그래프 이론 라이브러리.
  - [Socket.IO](https://socket.io/) - 클라이언트와 서버 간의 실시간 통신을 가능하게 합니다.
  - [HTML/CSS/JavaScript](https://developer.mozilla.org/) - 사용자 인터페이스 구축을 위한 표준 웹 기술.

### 설치

#### 사전 요구 사항

- **Python 3.11** 이상
- **Docker** (선택 사항, 컨테이너화된 배포를 위해)
- **Kubernetes 클러스터**와 `kubectl`이 설치되어 있고 접근 가능해야 합니다.
- **Git** (저장소 클론을 위해)

#### 저장소 클론

```bash
git clone https://github.com/ddukbg/k8s-network-policy-visualizer.git
cd k8s-network-policy-visualizer
```

#### 가상 환경 설정

의존성 관리를 위해 가상 환경을 사용하는 것이 권장됩니다.

```bash
# 가상 환경 생성
python3 -m venv venv

# 가상 환경 활성화
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

#### 의존성 설치

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **참고:** `requirements.txt` 파일에는 다음이 포함됩니다:
>
> ```plaintext
> Flask==2.3.2
> Flask-SocketIO==5.3.3
> Cytoscape.js==3.19.1
> ```

### 구성

1. **Kubernetes 접근:**
   
   `kubectl`이 설치되어 있고 Kubernetes 클러스터와 통신할 수 있는지 확인합니다. 다음 명령어를 실행하여 확인할 수 있습니다:
   
   ```bash
   kubectl get nodes
   ```
   
   클러스터의 노드 목록이 반환되어야 합니다.

2. **환경 변수:**
   
   애플리케이션은 현재 하드코딩된 비밀 키를 사용합니다. 프로덕션 환경에서는 `SECRET_KEY`를 환경 변수로 설정하는 것이 권장됩니다.
   
   ```bash
   export SECRET_KEY='your_secure_secret_key'
   ```
   
   필요에 따라 `app.py`를 수정하여 환경 변수에서 비밀 키를 가져오도록 설정할 수 있습니다.

### 사용법

#### 로컬에서 애플리케이션 실행

1. **가상 환경 활성화:**

   ```bash
   # macOS/Linux
   source venv/bin/activate

   # Windows
   venv\Scripts\activate
   ```

2. **Flask 서버 시작:**

   ```bash
   python app.py
   ```

   애플리케이션이 `http://localhost:5000`에서 시작됩니다.

3. **Visualizer 접속:**

   웹 브라우저를 열고 `http://localhost:5000`으로 이동하여 Kubernetes Network Policy Visualizer에 접속합니다.

#### Docker로 실행

1. **Docker 이미지 빌드:**

   ```bash
   docker build -t k8s-network-policy-visualizer .
   ```

2. **Docker 컨테이너 실행:**

   ```bash
   docker run -d -p 5000:5000 --name k8s-netpol-visualizer k8s-network-policy-visualizer
   ```

3. **Visualizer 접속:**

   웹 브라우저를 열고 `http://localhost:5000`으로 이동하여 Kubernetes Network Policy Visualizer에 접속합니다.

### 아키텍처

**Kubernetes Network Policy Visualizer**는 Flask 백엔드를 통해 Kubernetes API와 상호 작용하며, `kubectl` 명령어를 사용하여 네트워크 정책과 Pod 정보를 가져옵니다. 이를 기반으로 정책과 Pod 간의 관계를 맵핑하여 Ingress 및 Egress 규칙을 구분합니다. 프론트엔드는 Cytoscape.js를 활용하여 네트워크 그래프를 렌더링하며, Socket.IO를 통해 실시간 업데이트를 제공합니다. 이를 통해 사용자는 네트워크 정책의 흐름을 직관적으로 이해하고 관리할 수 있습니다.

#### 다이어그램

```
+-----------------+          +-----------------+
|                 |          |                 |
|    Kubernetes    <-------->    Flask Backend |
|   Cluster        |          |  (app.py)        |
|                 |          |                 |
+-----------------+          +-----------------+
                                           |
                                           | WebSocket (Socket.IO)
                                           |
                                +------------------------+
                                |                        |
                                |    Frontend (Cytoscape.js) |
                                |                        |
                                +------------------------+
```

### API 엔드포인트

#### 1. 홈 페이지

- **URL:** `/`
- **메소드:** `GET`
- **설명:** Visualizer의 메인 인터페이스를 렌더링합니다.

#### 2. 데이터 가져오기

- **URL:** `/data`
- **메소드:** `GET`
- **설명:** 노드(정책 및 Pod)와 엣지(Ingress 및 Egress 관계)를 포함한 그래프 데이터를 반환합니다.
- **응답 예시:**
  
  ```json
  {
      "nodes": [
          {"data": {"id": "namespace/policy1", "label": "policy1", "group": "policy"}},
          {"data": {"id": "namespace/pod1", "label": "pod1", "group": "pod"}},
          ...
      ],
      "edges": [
          {"data": {"source": "namespace/policy1", "target": "namespace/pod1", "type": "ingress", "label": "Ingress (TCP/5443)"}},
          {"data": {"source": "namespace/policy1", "target": "namespace/pod2", "type": "egress", "label": "Egress (TCP/80, TCP/443)"}},
          ...
      ]
  }
  ```

#### 3. 네임스페이스

- **URL:** `/namespaces`
- **메소드:** `GET`
- **설명:** 클러스터 내의 모든 네임스페이스 목록을 반환합니다.
- **응답 예시:**
  
  ```json
  {
      "namespaces": ["default", "kube-system", "calico-apiserver", ...]
  }
  ```

#### 4. 정책 상세 정보

- **URL:** `/policy/<policy_name>`
- **메소드:** `GET`
- **설명:** 특정 네트워크 정책의 상세 정보를 반환하며, Ingress 및 Egress 규칙을 포함합니다.
- **매개변수:**
  - `policy_name` (문자열): 네트워크 정책의 이름.
- **응답 예시:**
  
  ```json
  {
      "name": "allow-apiserver",
      "namespace": "calico-apiserver",
      "ingress": [
          {
              "from": [{"namespaceSelector": {"matchLabels": {"projectcalico.org/name": "calico-node"}}}],
              "ports": [{"port": 5443, "protocol": "TCP"}]
          }
      ],
      "egress": []
  }
  ```

#### 5. Pod 상세 정보

- **URL:** `/pod/<path:pod_name>`
- **메소드:** `GET`
- **설명:** 특정 Pod의 상세 정보를 반환하며, 레이블 및 상태를 포함합니다.
- **매개변수:**
  - `pod_name` (문자열): `namespace/pod_name` 형식의 Pod 전체 이름.
- **응답 예시:**
  
  ```json
  {
      "name": "sample-pod",
      "namespace": "calico-apiserver",
      "labels": {"app": "calico"},
      "status": "Running"
  }
  ```

### 프론트엔드 개요

**Kubernetes Network Policy Visualizer**의 프론트엔드는 표준 웹 기술(HTML, CSS, JavaScript)을 사용하여 구축되었으며, [Cytoscape.js](https://js.cytoscape.org/)의 강력한 기능을 활용하여 대화형 네트워크 그래프를 렌더링합니다. [Socket.IO](https://socket.io/)를 통해 실시간 업데이트를 관리하여 시각적 표현이 Kubernetes 클러스터의 현재 상태와 동기화되도록 합니다.

#### 주요 구성 요소

- **그래프 시각화 (`graph-container`):** 정책과 Pod을 Ingress 및 Egress 관계에 따라 서로 다른 스타일로 표시하는 네트워크 그래프를 렌더링합니다.
- **상세 정보 패널 (`details-container`):** 선택한 정책 또는 Pod의 포괄적인 세부 정보를 표시하며, 규칙 및 포트 정보를 포함합니다.
- **컨트롤 섹션 (`controls-section`):** 검색 창과 네임스페이스 필터링 옵션을 포함하여 뷰를 사용자 정의할 수 있습니다.

#### 사용자 상호 작용

- **노드 클릭:** 정책 또는 Pod 노드를 클릭하면 상세 정보 패널에 포괄적인 정보가 표시됩니다.
- **필터링:** 체크박스를 사용하여 네임스페이스별로 표시할 노드를 필터링할 수 있습니다.
- **검색:** 검색 창을 사용하여 특정 정책 또는 Pod을 빠르게 찾을 수 있습니다.
- **실시간 업데이트:** 클러스터 내의 네트워크 정책이나 Pod에 변경 사항이 발생하면 그래프가 실시간으로 업데이트됩니다.

### 백엔드 개요

**Kubernetes Network Policy Visualizer**의 백엔드는 경량 웹 프레임워크인 Flask로 구동됩니다. `kubectl` 명령어를 사용하여 Kubernetes 클러스터의 네트워크 정책과 Pod 정보를 가져옵니다. 이 데이터를 처리하여 정책과 Pod 간의 관계를 맵핑하고, Ingress 및 Egress 규칙을 구분하여 프론트엔드에 제공하는 API 엔드포인트를 구성합니다.

#### 주요 구성 요소

- **데이터 가져오기:** `kubectl`을 사용하여 네트워크 정책과 Pod을 JSON 형식으로 가져옵니다.
- **데이터 매핑:** 가져온 데이터를 처리하여 정책과 Pod 간의 관계를 설정하고, 관련 포트 정보를 추출합니다.
- **실시간 모니터링:** 백그라운드 스레드를 통해 Kubernetes 클러스터의 변화를 주기적으로 감지하고, Socket.IO를 통해 연결된 클라이언트에 업데이트를 전송합니다.
- **API 엔드포인트:** 그래프 데이터, 네임스페이스 목록, 정책 및 Pod의 상세 정보를 제공하는 엔드포인트를 구성합니다.

#### 실시간 업데이트

백엔드의 `monitor_changes` 함수는 주기적으로 네트워크 정책과 Pod을 확인하여 변경 사항을 감지합니다. 변경이 감지되면 그래프 데이터를 재계산하고, 이를 모든 연결된 클라이언트에게 Socket.IO를 통해 업데이트로 전송하여 시각화가 최신 상태를 유지하도록 합니다.

### 테스트

#### 단위 테스트

프로젝트는 백엔드 기능의 신뢰성을 보장하기 위해 단위 테스트를 포함하고 있습니다. 특히, API 엔드포인트와 데이터 매핑 함수에 대한 테스트가 포함됩니다.

##### 테스트 실행

1. **의존성 설치 확인:**

   ```bash
   pip install -r requirements.txt
   ```

2. **테스트 실행:**

   ```bash
   python -m unittest discover tests
   ```

#### 테스트 커버리지

- **네트워크 정책 가져오기:** 네트워크 정책이 올바르게 가져와지고 파싱되는지 확인합니다.
- **Pod 가져오기:** Pod이 정확하게 가져와지고 처리되는지 검증합니다.
- **데이터 매핑:** 정책과 Pod 간의 관계 매핑이 정확한지 테스트합니다.
- **API 엔드포인트:** API 엔드포인트가 예상된 데이터 구조를 반환하고 오류를 적절히 처리하는지 확인합니다.

### 기여

기여를 환영합니다! **Kubernetes Network Policy Visualizer**에 기여하려면 다음 단계를 따라주세요:

1. **저장소 포크:**
   
   저장소 페이지의 오른쪽 상단에 있는 "Fork" 버튼을 클릭하세요.

2. **포크한 저장소 클론:**

   ```bash
   git clone https://github.com/ddukbg/k8s-network-policy-visualizer.git
   cd k8s-network-policy-visualizer
   ```

3. **새 브랜치 생성:**

   ```bash
   git checkout -b feature/YourFeatureName
   ```

4. **변경 사항 적용:**
   
   기능을 구현하거나 버그를 수정하세요.

5. **변경 사항 커밋:**

   ```bash
   git commit -m "Add feature: Your Feature Description"
   ```

6. **포크한 저장소에 푸시:**

   ```bash
   git push origin feature/YourFeatureName
   ```

7. **풀 리퀘스트 생성:**
   
   원본 저장소로 이동하여 포크한 저장소에서 풀 리퀘스트를 생성하세요.

#### 가이드라인

- **코드 품질:** 코드가 최선의 관행을 따르고 잘 문서화되어 있는지 확인하세요.
- **테스트:** 새로운 기능에 대한 테스트를 추가하세요.
- **문서화:** 필요에 따라 README 및 기타 문서를 업데이트하세요.
- **이슈 추적:** 작업을 시작하기 전에 이슈가 이미 보고되었거나 해결되었는지 확인하세요.

### 라이선스

이 프로젝트는 [MIT 라이선스](LICENSE) 하에 라이선스가 부여됩니다. 라이선스 조건에 따라 자유롭게 사용, 수정 및 배포할 수 있습니다.

### 문의

질문, 제안 또는 피드백이 있으시면 언제든지 연락주세요:

- **이메일:** wowrebong@gmail.com
- **GitHub 이슈:** [k8s-network-policy-visualizer/issues](https://github.com/ddukbg/k8s-network-policy-visualizer/issues)

---

*Happy Visualizing!*

---

## English

### Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Technologies Used](#technologies-used)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Architecture](#architecture)
- [API Endpoints](#api-endpoints)
- [Frontend Overview](#frontend-overview)
- [Backend Overview](#backend-overview)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

### Introduction

**Kubernetes Network Policy Visualizer** is a powerful web-based tool designed to help Kubernetes administrators and developers visualize and analyze Network Policies within their clusters. By providing a clear graphical representation of how Network Policies interact with Pods, it simplifies the understanding and management of complex network configurations. The tool leverages real-time updates to ensure that the visualizations are always in sync with the current state of the cluster.

**Reason for Creation:** Viewing Network Policies through YAML files was cumbersome and time-consuming. To make this process more intuitive and user-friendly, we developed a visualization tool.

### Features

- **Real-Time Visualization:** Automatically updates the network policy graph as changes occur in the Kubernetes cluster.
- **Ingress and Egress Representation:** Distinguishes between ingress and egress policies using different arrow styles and colors.
- **Port Information Display:** Clearly displays port information for each policy rule, regardless of the number of ports.
- **Namespace Filtering:** Filter policies and pods based on Kubernetes namespaces with an intuitive checkbox interface, including an "ALL" option.
- **Search Functionality:** Easily search for specific Pods or Policies using the search bar.
- **Detailed Information Panels:** Click on any Policy or Pod node to view comprehensive details, including ingress and egress rules, associated ports, labels, and status.
- **Responsive Design:** Optimized for various screen sizes, ensuring usability across desktops, tablets, and mobile devices.
- **Docker Support:** Containerized for easy deployment and scalability.

### Technologies Used

- **Backend:**
  - [Flask](https://flask.palletsprojects.com/) - A lightweight WSGI web application framework.
  - [Flask-SocketIO](https://flask-socketio.readthedocs.io/) - Enables real-time bi-directional communication between clients and the server.
  - [Kubernetes `kubectl`](https://kubernetes.io/docs/reference/kubectl/overview/) - Command-line tool to interact with Kubernetes clusters.
  
- **Frontend:**
  - [Cytoscape.js](https://js.cytoscape.org/) - A graph theory library for visualization and analysis.
  - [Socket.IO](https://socket.io/) - Enables real-time communication between the client and server.
  - [HTML/CSS/JavaScript](https://developer.mozilla.org/) - Standard web technologies for building the user interface.

### Installation

#### Prerequisites

- **Python 3.11** or higher
- **Docker** (optional, for containerized deployment)
- **Kubernetes Cluster** with `kubectl` configured and accessible
- **Git** (for cloning the repository)

#### Clone the Repository

```bash
git clone https://github.com/ddukbg/k8s-network-policy-visualizer.git
cd k8s-network-policy-visualizer
```

#### Set Up a Virtual Environment

It's recommended to use a virtual environment to manage dependencies.

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS/Linux
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

#### Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Note:** The `requirements.txt` file includes:
>
> ```plaintext
> Flask==2.3.2
> Flask-SocketIO==5.3.3
> Cytoscape.js==3.19.1
> ```

### Configuration

1. **Kubernetes Access:**
   
   Ensure that `kubectl` is installed and configured to communicate with your Kubernetes cluster. You can verify this by running:
   
   ```bash
   kubectl get nodes
   ```
   
   This should return a list of your cluster's nodes.

2. **Environment Variables:**
   
   The application currently uses a hardcoded secret key. For production use, it's recommended to set the `SECRET_KEY` as an environment variable.
   
   ```bash
   export SECRET_KEY='your_secure_secret_key'
   ```
   
   Modify the `app.py` to fetch the secret key from environment variables if needed.

### Usage

#### Running the Application Locally

1. **Activate the Virtual Environment:**

   ```bash
   # On macOS/Linux
   source venv/bin/activate

   # On Windows
   venv\Scripts\activate
   ```

2. **Start the Flask Server:**

   ```bash
   python app.py
   ```

   The application will start on `http://localhost:5000`.

3. **Access the Visualizer:**

   Open your web browser and navigate to `http://localhost:5000` to access the Kubernetes Network Policy Visualizer.

#### Running with Docker

1. **Build the Docker Image:**

   ```bash
   docker build -t k8s-network-policy-visualizer .
   ```

2. **Run the Docker Container:**

   ```bash
   docker run -d -p 5000:5000 --name k8s-netpol-visualizer k8s-network-policy-visualizer
   ```

3. **Access the Visualizer:**

   Navigate to `http://localhost:5000` in your web browser.

### Architecture

The **Kubernetes Network Policy Visualizer** consists of a Flask backend that interacts with the Kubernetes API using `kubectl` commands to fetch Network Policies and Pods. It maps the relationships between Policies and Pods, distinguishing between ingress and egress rules. The frontend utilizes Cytoscape.js to render the network graph, providing interactive features such as node clicking for detailed views, filtering, and searching. Real-time updates are facilitated through Socket.IO, ensuring that the visualization remains current with cluster changes.

#### Diagram

```
+-----------------+          +-----------------+
|                 |          |                 |
|    Kubernetes    <-------->    Flask Backend |
|   Cluster        |          |  (app.py)        |
|                 |          |                 |
+-----------------+          +-----------------+
                                           |
                                           | WebSocket (Socket.IO)
                                           |
                                +------------------------+
                                |                        |
                                |    Frontend (Cytoscape.js) |
                                |                        |
                                +------------------------+
```

### API Endpoints

#### 1. Home Page

- **URL:** `/`
- **Method:** `GET`
- **Description:** Renders the main interface of the visualizer.

#### 2. Data Fetching

- **URL:** `/data`
- **Method:** `GET`
- **Description:** Returns the graph data including nodes (Policies and Pods) and edges (Ingress and Egress relationships).
- **Response Example:**
  
  ```json
  {
      "nodes": [
          {"data": {"id": "namespace/policy1", "label": "policy1", "group": "policy"}},
          {"data": {"id": "namespace/pod1", "label": "pod1", "group": "pod"}},
          ...
      ],
      "edges": [
          {"data": {"source": "namespace/policy1", "target": "namespace/pod1", "type": "ingress", "label": "Ingress (TCP/5443)"}},
          {"data": {"source": "namespace/policy1", "target": "namespace/pod2", "type": "egress", "label": "Egress (TCP/80, TCP/443)"}},
          ...
      ]
  }
  ```

#### 3. Namespaces

- **URL:** `/namespaces`
- **Method:** `GET`
- **Description:** Returns a list of all namespaces in the cluster.
- **Response Example:**
  
  ```json
  {
      "namespaces": ["default", "kube-system", "calico-apiserver", ...]
  }
  ```

#### 4. Policy Details

- **URL:** `/policy/<policy_name>`
- **Method:** `GET`
- **Description:** Returns detailed information about a specific Network Policy, including ingress and egress rules.
- **Parameters:**
  - `policy_name` (string): Name of the Network Policy.
- **Response Example:**
  
  ```json
  {
      "name": "allow-apiserver",
      "namespace": "calico-apiserver",
      "ingress": [
          {
              "from": [{"namespaceSelector": {"matchLabels": {"projectcalico.org/name": "calico-node"}}}],
              "ports": [{"port": 5443, "protocol": "TCP"}]
          }
      ],
      "egress": []
  }
  ```

#### 5. Pod Details

- **URL:** `/pod/<path:pod_name>`
- **Method:** `GET`
- **Description:** Returns detailed information about a specific Pod, including labels and status.
- **Parameters:**
  - `pod_name` (string): Full name of the Pod in the format `namespace/pod_name`.
- **Response Example:**
  
  ```json
  {
      "name": "sample-pod",
      "namespace": "calico-apiserver",
      "labels": {"app": "calico"},
      "status": "Running"
  }
  ```

### Frontend Overview

The frontend of the **Kubernetes Network Policy Visualizer** is built using standard web technologies (HTML, CSS, JavaScript) and leverages the power of [Cytoscape.js](https://js.cytoscape.org/) for rendering interactive network graphs. Real-time updates are managed through [Socket.IO](https://socket.io/), ensuring that the visual representation remains up-to-date with the current state of the Kubernetes cluster.

#### Key Components

- **Graph Visualization (`graph-container`):** Renders the network graph showing Policies and Pods with distinct styles for ingress and egress relationships.
- **Details Panel (`details-container`):** Displays comprehensive details of the selected Policy or Pod, including rules and port information.
- **Controls Section (`controls-section`):** Includes the search bar and namespace filtering options to customize the view.

#### User Interactions

- **Node Clicking:** Clicking on a Policy or Pod node fetches and displays detailed information in the Details Panel.
- **Filtering:** Users can filter the displayed nodes based on namespaces using checkboxes.
- **Searching:** The search bar allows users to quickly locate specific Policies or Pods by name.
- **Real-Time Updates:** The graph updates in real-time to reflect any changes in Network Policies or Pods within the cluster.

### Backend Overview

The backend of the **Kubernetes Network Policy Visualizer** is powered by Flask, a lightweight web framework. It interacts with the Kubernetes cluster using `kubectl` commands to retrieve information about Network Policies and Pods. The backend processes this data to map the relationships between Policies and Pods, distinguishing between ingress and egress rules, and serves this information to the frontend through API endpoints.

#### Key Components

- **Data Fetching:** Utilizes `kubectl` to fetch Network Policies and Pods in JSON format.
- **Data Mapping:** Processes the fetched data to establish relationships and extract relevant details like ports.
- **Real-Time Monitoring:** Continuously monitors the Kubernetes cluster for changes and emits updates to connected clients via Socket.IO.
- **API Endpoints:** Provides endpoints for fetching graph data, namespaces, and detailed information about Policies and Pods.

#### Real-Time Updates

A background thread (`monitor_changes`) periodically checks for changes in Network Policies and Pods. If any changes are detected, the backend recalculates the graph data and emits an update to all connected clients, ensuring that the visualization remains current.

### Testing

#### Unit Tests

The project includes unit tests to ensure the reliability of backend functionalities, particularly the API endpoints and data mapping functions.

##### Running Tests

1. **Ensure Dependencies are Installed:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Tests:**

   ```bash
   python -m unittest discover tests
   ```

#### Test Coverage

- **Network Policies Retrieval:** Ensures that Network Policies are correctly fetched and parsed.
- **Pods Retrieval:** Validates that Pods are accurately retrieved and processed.
- **Data Mapping:** Tests the correctness of the relationship mapping between Policies and Pods.
- **API Endpoints:** Confirms that API endpoints return the expected data structures and handle errors gracefully.

### Contributing

Contributions are welcome! To contribute to the **Kubernetes Network Policy Visualizer**, please follow these steps:

1. **Fork the Repository:**
   
   Click the "Fork" button at the top right corner of the repository page.

2. **Clone Your Fork:**

   ```bash
   git clone https://github.com/ddukbg/k8s-network-policy-visualizer.git
   cd k8s-network-policy-visualizer
   ```

3. **Create a New Branch:**

   ```bash
   git checkout -b feature/YourFeatureName
   ```

4. **Make Your Changes:**
   
   Implement your feature or fix the bug.

5. **Commit Your Changes:**

   ```bash
   git commit -m "Add feature: Your Feature Description"
   ```

6. **Push to Your Fork:**

   ```bash
   git push origin feature/YourFeatureName
   ```

7. **Create a Pull Request:**
   
   Navigate to the original repository and create a pull request from your fork.

#### Guidelines

- **Code Quality:** Ensure that your code follows best practices and is well-documented.
- **Testing:** Add tests for any new functionality.
- **Documentation:** Update the README and other documentation as needed.
- **Issue Tracking:** Before starting, check if the issue has already been reported or addressed.

### License

This project is licensed under the [MIT License](LICENSE). You are free to use, modify, and distribute this software as per the terms of the license.

### Contact

For any questions, suggestions, or feedback, please feel free to reach out:

- **Email:** wowrebong@gmail.com
- **GitHub Issues:** [k8s-network-policy-visualizer/issues](https://github.com/ddukbg/k8s-network-policy-visualizer/issues)

---

*Happy Visualizing!*

---
