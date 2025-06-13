"""
Kubernetes 리소스 모델 정의
Python 표준 dataclass 기반
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime


@dataclass
class PortInfo:
    """포트 정보"""
    port: Optional[Union[int, str]] = None
    protocol: str = "TCP"
    name: Optional[str] = None


@dataclass
class LabelSelector:
    """라벨 셀렉터"""
    match_labels: Optional[Dict[str, str]] = None
    match_expressions: Optional[List[Dict[str, Any]]] = None


@dataclass
class NetworkPolicyPeer:
    """네트워크 정책 피어"""
    pod_selector: Optional[LabelSelector] = None
    namespace_selector: Optional[LabelSelector] = None
    ip_block: Optional[Dict[str, Any]] = None


@dataclass
class NetworkPolicyRule:
    """네트워크 정책 규칙"""
    ports: Optional[List[PortInfo]] = None
    from_: Optional[List[NetworkPolicyPeer]] = None
    to: Optional[List[NetworkPolicyPeer]] = None


@dataclass
class NetworkPolicySpec:
    """네트워크 정책 스펙"""
    pod_selector: LabelSelector
    policy_types: List[str] = field(default_factory=list)
    ingress: Optional[List[NetworkPolicyRule]] = None
    egress: Optional[List[NetworkPolicyRule]] = None


@dataclass
class KubernetesMetadata:
    """Kubernetes 리소스 메타데이터"""
    name: str
    namespace: str
    uid: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
    annotations: Optional[Dict[str, str]] = None
    creation_timestamp: Optional[str] = None
    resource_version: Optional[str] = None


@dataclass
class NetworkPolicy:
    """네트워크 정책"""
    api_version: str = "networking.k8s.io/v1"
    kind: str = "NetworkPolicy"
    metadata: Optional[KubernetesMetadata] = None
    spec: Optional[NetworkPolicySpec] = None
    status: Optional[Dict[str, Any]] = None


@dataclass
class PodStatus:
    """Pod 상태"""
    phase: str = "Unknown"
    conditions: Optional[List[Dict[str, Any]]] = None
    pod_ip: Optional[str] = None
    host_ip: Optional[str] = None


@dataclass
class ContainerSpec:
    """컨테이너 스펙"""
    name: str
    image: str
    ports: Optional[List[PortInfo]] = None
    env: Optional[List[Dict[str, Any]]] = None


@dataclass
class PodSpec:
    """Pod 스펙"""
    containers: List[ContainerSpec] = field(default_factory=list)
    node_name: Optional[str] = None
    service_account: Optional[str] = None


@dataclass
class Pod:
    """Pod 리소스"""
    api_version: str = "v1"
    kind: str = "Pod"
    metadata: Optional[KubernetesMetadata] = None
    spec: Optional[PodSpec] = None
    status: Optional[PodStatus] = None


@dataclass
class DeploymentStatus:
    """Deployment 상태"""
    replicas: int = 0
    ready_replicas: int = 0
    available_replicas: int = 0
    updated_replicas: int = 0
    conditions: Optional[List[Dict[str, Any]]] = None


@dataclass
class DeploymentSpec:
    """Deployment 스펙"""
    replicas: int = 1
    selector: Optional[LabelSelector] = None
    template: Optional[Dict[str, Any]] = None


@dataclass
class Deployment:
    """Deployment 리소스"""
    api_version: str = "apps/v1"
    kind: str = "Deployment"
    metadata: Optional[KubernetesMetadata] = None
    spec: Optional[DeploymentSpec] = None
    status: Optional[DeploymentStatus] = None


@dataclass
class ServiceSpec:
    """Service 스펙"""
    selector: Optional[Dict[str, str]] = None
    ports: Optional[List[PortInfo]] = None
    type: str = "ClusterIP"


@dataclass
class Service:
    """Service 리소스"""
    api_version: str = "v1"
    kind: str = "Service"
    metadata: Optional[KubernetesMetadata] = None
    spec: Optional[ServiceSpec] = None


# 그래프 데이터 모델
@dataclass
class GraphNode:
    """그래프 노드"""
    id: str
    label: str
    group: str  # policy, pod, deployment, service, ipblock
    namespace: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'label': self.label,
            'group': self.group,
            'namespace': self.namespace,
            'status': self.status,
            'metadata': self.metadata or {}
        }


@dataclass
class GraphEdge:
    """그래프 엣지"""
    source: str
    target: str
    type: str  # ingress, egress, ingress-ipblock, egress-ipblock
    ports: Optional[List[PortInfo]] = None
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'source': self.source,
            'target': self.target,
            'type': self.type,
            'ports': [vars(p) for p in (self.ports or [])],
            'details': self.details or {}
        }


@dataclass
class GraphData:
    """완전한 그래프 데이터"""
    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)
    namespaces: List[str] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'nodes': [node.to_dict() for node in self.nodes],
            'edges': [edge.to_dict() for edge in self.edges],
            'namespaces': self.namespaces,
            'metadata': self.metadata or {}
        }


@dataclass
class HealthStatus:
    """헬스 체크 상태"""
    status: str = "healthy"
    timestamp: Optional[str] = None
    version: str = "2.0.0"
    kubernetes_connected: bool = False
    cluster_info: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'status': self.status,
            'timestamp': self.timestamp,
            'version': self.version,
            'kubernetes_connected': self.kubernetes_connected,
            'cluster_info': self.cluster_info or {}
        }


# 유틸리티 함수들
def create_graph_node(
    node_id: str,
    label: str,
    group: str,
    namespace: Optional[str] = None,
    status: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> GraphNode:
    """그래프 노드 생성 헬퍼"""
    return GraphNode(
        id=node_id,
        label=label,
        group=group,
        namespace=namespace,
        status=status,
        metadata=metadata
    )


def create_graph_edge(
    source: str,
    target: str,
    edge_type: str,
    ports: Optional[List[PortInfo]] = None,
    details: Optional[Dict[str, Any]] = None
) -> GraphEdge:
    """그래프 엣지 생성 헬퍼"""
    return GraphEdge(
        source=source,
        target=target,
        type=edge_type,
        ports=ports,
        details=details
    )


def create_port_info(
    port: Optional[Union[int, str]] = None,
    protocol: str = "TCP",
    name: Optional[str] = None
) -> PortInfo:
    """포트 정보 생성 헬퍼"""
    return PortInfo(port=port, protocol=protocol, name=name) 