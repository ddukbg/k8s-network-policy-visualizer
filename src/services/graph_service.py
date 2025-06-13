import logging
from typing import Dict, List, Set, Union, Any, Optional
import hashlib

from ..models.kubernetes_models import (
    GraphData, GraphNode, GraphEdge, PortInfo,
    create_graph_node, create_graph_edge, create_port_info
)

logger = logging.getLogger(__name__)


class GraphService:
    """네트워크 정책을 그래프 데이터로 변환하는 서비스"""
    
    def __init__(self):
        self.last_hash: Optional[str] = None
    
    def _matches_selector(self, labels: Dict[str, str], selector: Optional[Dict[str, Any]]) -> bool:
        """라벨 셀렉터 매칭 검사"""
        if not selector:
            return True
        
        match_labels = selector.get('matchLabels', {})
        if not match_labels:
            return True
        
        for key, value in match_labels.items():
            if labels.get(key) != value:
                return False
        return True
    
    def _create_resource_nodes(self, resources: List[Dict[str, Any]], resource_type: str) -> Dict[str, GraphNode]:
        """리소스를 그래프 노드로 변환"""
        nodes = {}
        
        for resource in resources:
            metadata = resource.get('metadata', {})
            status = resource.get('status', {})
            
            resource_id = f"{metadata.get('namespace', 'default')}/{metadata.get('name', 'unknown')}"
            
            # 상태 정보 추출
            status_text = "Unknown"
            if resource_type == "pod":
                status_text = status.get('phase', 'Unknown')
            elif resource_type == "deployment":
                total_replicas = status.get('replicas', 0)
                ready_replicas = status.get('readyReplicas', 0)
                status_text = f"{ready_replicas}/{total_replicas}"
            
            node = create_graph_node(
                node_id=resource_id,
                label=metadata.get('name', 'unknown'),
                group=resource_type,
                namespace=metadata.get('namespace', 'default'),
                status=status_text,
                metadata={
                    "labels": metadata.get('labels', {}),
                    "created": metadata.get('creationTimestamp'),
                    "uid": metadata.get('uid'),
                    "annotations": metadata.get('annotations', {}),
                    "policies": []
                }
            )
            nodes[resource_id] = node
        
        return nodes
    
    def _create_policy_nodes(self, policies: List[Dict[str, Any]]) -> Dict[str, GraphNode]:
        """정책을 그래프 노드로 변환"""
        nodes = {}
        
        for policy in policies:
            metadata = policy.get('metadata', {})
            spec = policy.get('spec', {})
            
            policy_id = f"{metadata.get('namespace', 'default')}/{metadata.get('name', 'unknown')}"
            
            node = create_graph_node(
                node_id=policy_id,
                label=metadata.get('name', 'unknown'),
                group="policy",
                namespace=metadata.get('namespace', 'default'),
                status="Active",
                metadata={
                    "labels": metadata.get('labels', {}),
                    "created": metadata.get('creationTimestamp'),
                    "uid": metadata.get('uid'),
                    "policy_types": spec.get('policyTypes', []),
                    "pod_selector": spec.get('podSelector', {})
                }
            )
            nodes[policy_id] = node
        
        return nodes
    
    def _create_ipblock_node(self, policy_id: str, ip_block: Dict[str, Any]) -> GraphNode:
        """IP 블록 노드 생성"""
        cidr = ip_block.get('cidr', 'Unknown')
        node_id = f"{policy_id}/ipblock/{hashlib.md5(cidr.encode()).hexdigest()[:8]}"
        
        return create_graph_node(
            node_id=node_id,
            label=f"IP: {cidr}",
            group="ipblock",
            namespace="external",
            status="External",
            metadata={
                "labels": {},
                "cidr": cidr,
                "except": ip_block.get('except', []),
                "policies": [policy_id]
            }
        )
    
    def _process_policy_rules(
        self, 
        policy: Dict[str, Any], 
        resource_nodes: Dict[str, GraphNode],
        policy_nodes: Dict[str, GraphNode]
    ) -> tuple[List[GraphEdge], Dict[str, GraphNode]]:
        """정책 규칙을 처리하여 엣지와 IP 블록 노드 생성"""
        edges = []
        ipblock_nodes = {}
        
        metadata = policy.get('metadata', {})
        spec = policy.get('spec', {})
        policy_id = f"{metadata.get('namespace', 'default')}/{metadata.get('name', 'unknown')}"
        
        # Ingress 규칙 처리
        for ingress_rule in spec.get('ingress', []):
            # 포트 정보 추출
            ports = []
            for port_info in ingress_rule.get('ports', []):
                ports.append(create_port_info(
                    port=port_info.get('port'),
                    protocol=port_info.get('protocol', 'TCP'),
                    name=port_info.get('name')
                ))
            
            # from 필드 처리
            for from_peer in ingress_rule.get('from', []):
                # IP 블록 처리
                if 'ipBlock' in from_peer:
                    ipblock_node = self._create_ipblock_node(policy_id, from_peer['ipBlock'])
                    ipblock_nodes[ipblock_node.id] = ipblock_node
                    
                    edge = create_graph_edge(
                        source=ipblock_node.id,
                        target=policy_id,
                        edge_type="ingress-ipblock",
                        ports=ports,
                        details=from_peer['ipBlock']
                    )
                    edges.append(edge)
                
                # Pod/Namespace 셀렉터 처리
                else:
                    for resource_id, resource_node in resource_nodes.items():
                        resource_labels = resource_node.metadata.get('labels', {})
                        
                        # 같은 네임스페이스 체크 (네임스페이스 셀렉터가 없는 경우)
                        if 'namespaceSelector' not in from_peer and resource_node.namespace != metadata.get('namespace'):
                            continue
                        
                        # Pod 셀렉터 매칭
                        if 'podSelector' in from_peer and not self._matches_selector(resource_labels, from_peer['podSelector']):
                            continue
                        
                        # 네임스페이스 셀렉터 매칭
                        if 'namespaceSelector' in from_peer:
                            ns_labels = {"name": resource_node.namespace}
                            if not self._matches_selector(ns_labels, from_peer['namespaceSelector']):
                                continue
                        
                        edge = create_graph_edge(
                            source=resource_id,
                            target=policy_id,
                            edge_type="ingress",
                            ports=ports
                        )
                        edges.append(edge)
                        
                        # 리소스 노드에 정책 연결 정보 추가
                        if 'policies' not in resource_node.metadata:
                            resource_node.metadata['policies'] = []
                        if policy_id not in resource_node.metadata['policies']:
                            resource_node.metadata['policies'].append(policy_id)
        
        # Egress 규칙 처리
        for egress_rule in spec.get('egress', []):
            # 포트 정보 추출
            ports = []
            for port_info in egress_rule.get('ports', []):
                ports.append(create_port_info(
                    port=port_info.get('port'),
                    protocol=port_info.get('protocol', 'TCP'),
                    name=port_info.get('name')
                ))
            
            # to 필드 처리
            for to_peer in egress_rule.get('to', []):
                # IP 블록 처리
                if 'ipBlock' in to_peer:
                    ipblock_node = self._create_ipblock_node(policy_id, to_peer['ipBlock'])
                    ipblock_nodes[ipblock_node.id] = ipblock_node
                    
                    edge = create_graph_edge(
                        source=policy_id,
                        target=ipblock_node.id,
                        edge_type="egress-ipblock",
                        ports=ports,
                        details=to_peer['ipBlock']
                    )
                    edges.append(edge)
                
                # Pod/Namespace 셀렉터 처리
                else:
                    for resource_id, resource_node in resource_nodes.items():
                        resource_labels = resource_node.metadata.get('labels', {})
                        
                        # 같은 네임스페이스 체크 (네임스페이스 셀렉터가 없는 경우)
                        if 'namespaceSelector' not in to_peer and resource_node.namespace != metadata.get('namespace'):
                            continue
                        
                        # Pod 셀렉터 매칭
                        if 'podSelector' in to_peer and not self._matches_selector(resource_labels, to_peer['podSelector']):
                            continue
                        
                        # 네임스페이스 셀렉터 매칭
                        if 'namespaceSelector' in to_peer:
                            ns_labels = {"name": resource_node.namespace}
                            if not self._matches_selector(ns_labels, to_peer['namespaceSelector']):
                                continue
                        
                        edge = create_graph_edge(
                            source=policy_id,
                            target=resource_id,
                            edge_type="egress",
                            ports=ports
                        )
                        edges.append(edge)
                        
                        # 리소스 노드에 정책 연결 정보 추가
                        if 'policies' not in resource_node.metadata:
                            resource_node.metadata['policies'] = []
                        if policy_id not in resource_node.metadata['policies']:
                            resource_node.metadata['policies'].append(policy_id)
        
        return edges, ipblock_nodes
    
    def _connect_policy_to_resources(
        self, 
        policy: Dict[str, Any], 
        resource_nodes: Dict[str, GraphNode], 
        policy_nodes: Dict[str, GraphNode]
    ) -> List[GraphEdge]:
        """정책을 적용 대상 리소스에 연결"""
        edges = []
        metadata = policy.get('metadata', {})
        spec = policy.get('spec', {})
        policy_id = f"{metadata.get('namespace', 'default')}/{metadata.get('name', 'unknown')}"
        
        pod_selector = spec.get('podSelector', {})
        
        for resource_id, resource_node in resource_nodes.items():
            # 같은 네임스페이스의 리소스만
            if resource_node.namespace != metadata.get('namespace'):
                continue
            
            # Pod 셀렉터 매칭
            resource_labels = resource_node.metadata.get('labels', {})
            if self._matches_selector(resource_labels, pod_selector):
                # 정책 적용 관계를 나타내는 엣지 생성
                edge = create_graph_edge(
                    source=policy_id,
                    target=resource_id,
                    edge_type="applies-to",
                    ports=[],
                    details={"selector": pod_selector}
                )
                edges.append(edge)
                
                # 리소스 노드에 정책 연결 정보 추가
                if 'policies' not in resource_node.metadata:
                    resource_node.metadata['policies'] = []
                if policy_id not in resource_node.metadata['policies']:
                    resource_node.metadata['policies'].append(policy_id)
        
        return edges
    
    def create_graph_data(
        self, 
        policies: List[Dict[str, Any]], 
        resources: List[Dict[str, Any]], 
        resource_type: str,
        namespaces: List[str]
    ) -> GraphData:
        """그래프 데이터 생성"""
        try:
            logger.info(f"그래프 데이터 생성 시작: {resource_type}, 정책 {len(policies)}개, 리소스 {len(resources)}개")
            
            # 노드 생성
            resource_nodes = self._create_resource_nodes(resources, resource_type)
            policy_nodes = self._create_policy_nodes(policies)
            logger.info(f"노드 생성 완료: 리소스 {len(resource_nodes)}개, 정책 {len(policy_nodes)}개")
            
            all_edges = []
            all_ipblock_nodes = {}
            
            # 간단한 정책-리소스 연결만 생성 (복잡한 규칙 처리 건너뛰기)
            policies_to_process = policies[:5]  # 성능을 위해 최대 5개만 처리
            logger.info(f"정책 처리 중: {len(policies_to_process)}개")
            
            for i, policy in enumerate(policies_to_process):
                policy_name = policy.get('metadata', {}).get('name', f'policy-{i}')
                logger.info(f"정책 처리 중: {policy_name}")
                
                # 복잡한 규칙 처리 대신 간단한 적용 관계만 생성
                apply_edges = self._connect_policy_to_resources(policy, resource_nodes, policy_nodes)
                all_edges.extend(apply_edges)
                
                logger.info(f"정책 {policy_name} 처리 완료: 적용 엣지 {len(apply_edges)}개")
            
            # 모든 노드 통합
            all_nodes = list(resource_nodes.values()) + list(policy_nodes.values()) + list(all_ipblock_nodes.values())
            
            # GraphData 생성
            graph_data = GraphData(
                nodes=all_nodes,
                edges=all_edges,
                namespaces=namespaces,
                metadata={
                    "resource_type": resource_type,
                    "generated_at": str(hashlib.sha256(str(all_nodes + all_edges).encode()).hexdigest()),
                    "total_policies": len(policies),
                    "total_resources": len(resources),
                    "processed_policies": len(policies_to_process)
                }
            )
            
            logger.info(f"그래프 데이터 생성 완료: 노드 {len(all_nodes)}개, 엣지 {len(all_edges)}개")
            return graph_data
            
        except Exception as e:
            logger.error(f"그래프 데이터 생성 실패: {e}")
            # 빈 그래프 데이터 반환
            return GraphData(
                nodes=[],
                edges=[],
                namespaces=namespaces,
                metadata={"error": str(e)}
            )
    
    def _calculate_data_hash(self, graph_data: GraphData) -> str:
        """그래프 데이터 해시 계산"""
        data_string = f"{len(graph_data.nodes)}-{len(graph_data.edges)}-{','.join(graph_data.namespaces)}"
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def has_data_changed(self, new_data: GraphData) -> bool:
        """데이터 변경 여부 확인"""
        new_hash = self._calculate_data_hash(new_data)
        if self.last_hash != new_hash:
            self.last_hash = new_hash
            return True
        return False 