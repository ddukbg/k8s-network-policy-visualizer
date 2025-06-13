#!/usr/bin/env python3
"""
Kubernetes Network Policy Visualizer - 간단하고 안정적인 버전
실제 클러스터 데이터를 안정적으로 처리
"""

import logging
import sys
import os
import time
import json
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime
import urllib.parse

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

# 로컬 모듈 import
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from config import get_config

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleKubernetesService:
    """간단한 Kubernetes 서비스"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 60  # 60초 캐시
        
    def _run_kubectl(self, cmd: List[str]) -> List[Dict]:
        """kubectl 명령 실행"""
        try:
            full_cmd = ['kubectl'] + cmd
            result = subprocess.run(
                full_cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"kubectl 명령 실패: {result.stderr}")
                return []
            
            if result.stdout.strip():
                return json.loads(result.stdout)
            return []
            
        except subprocess.TimeoutExpired:
            logger.error("kubectl 명령 시간 초과")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            return []
        except Exception as e:
            logger.error(f"kubectl 실행 실패: {e}")
            return []
    
    def get_pods(self) -> List[Dict]:
        """Pod 목록 조회"""
        cache_key = 'pods'
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            cmd = ['get', 'pods', '--all-namespaces', '-o', 'json']
            result = self._run_kubectl(cmd)
            
            if isinstance(result, dict) and 'items' in result:
                # test-namespace와 중요한 네임스페이스 우선 포함
                all_pods = result['items']
                priority_namespaces = ['test-namespace-1', 'test-namespace-2', 'test-namespace-3', 
                                     'calico-apiserver', 'calico-system', 'kube-system']
                
                priority_pods = []
                other_pods = []
                
                for pod in all_pods:
                    namespace = pod.get('metadata', {}).get('namespace', 'default')
                    if namespace in priority_namespaces:
                        priority_pods.append(pod)
                    else:
                        other_pods.append(pod)
                
                # 우선순위 Pod들 + 나머지 Pod들 (최대 50개)
                pods = priority_pods + other_pods[:max(0, 50 - len(priority_pods))]
                self._update_cache(cache_key, pods)
                return pods
            return []
            
        except Exception as e:
            logger.error(f"Pod 조회 실패: {e}")
            return []
    
    def get_deployments(self) -> List[Dict]:
        """Deployment 목록 조회"""
        cache_key = 'deployments'
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            cmd = ['get', 'deployments', '--all-namespaces', '-o', 'json']
            result = self._run_kubectl(cmd)
            
            if isinstance(result, dict) and 'items' in result:
                # test-namespace와 중요한 네임스페이스 우선 포함
                all_deployments = result['items']
                priority_namespaces = ['test-namespace-1', 'test-namespace-2', 'test-namespace-3', 
                                     'calico-apiserver', 'calico-system', 'default']
                
                priority_deployments = []
                other_deployments = []
                
                for deployment in all_deployments:
                    namespace = deployment.get('metadata', {}).get('namespace', 'default')
                    if namespace in priority_namespaces:
                        priority_deployments.append(deployment)
                    else:
                        other_deployments.append(deployment)
                
                # 우선순위 Deployment들 + 나머지 (최대 30개)
                deployments = priority_deployments + other_deployments[:max(0, 30 - len(priority_deployments))]
                self._update_cache(cache_key, deployments)
                return deployments
            return []
            
        except Exception as e:
            logger.error(f"Deployment 조회 실패: {e}")
            return []

    def get_network_policies(self) -> List[Dict]:
        """네트워크 정책 목록 조회"""
        cache_key = 'network_policies'
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            cmd = ['get', 'networkpolicies', '--all-namespaces', '-o', 'json']
            result = self._run_kubectl(cmd)
            
            if isinstance(result, dict) and 'items' in result:
                policies = result['items']
                self._update_cache(cache_key, policies)
                return policies
            return []
            
        except Exception as e:
            logger.error(f"네트워크 정책 조회 실패: {e}")
            return []
    
    def get_namespaces(self) -> List[str]:
        """네임스페이스 목록 조회"""
        try:
            cmd = ['get', 'namespaces', '-o', 'json']
            result = self._run_kubectl(cmd)
            
            if isinstance(result, dict) and 'items' in result:
                return [item['metadata']['name'] for item in result['items']]
            return ['default']
            
        except Exception as e:
            logger.error(f"네임스페이스 조회 실패: {e}")
            return ['default']
    
    def _is_cache_valid(self, key: str) -> bool:
        """캐시 유효성 확인"""
        if key not in self.cache:
            return False
        
        cache_time = self.cache[key]['timestamp']
        return (time.time() - cache_time) < self.cache_timeout
    
    def _update_cache(self, key: str, data: Any):
        """캐시 업데이트"""
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }

class NetworkPolicyVisualizer:
    """메인 애플리케이션 클래스"""
    
    def __init__(self):
        self.config = get_config()
        self.app = self._create_app()
        self.socketio = self._setup_socketio()
        self.k8s_service = SimpleKubernetesService()
        
        self._setup_routes()
        logger.info("애플리케이션 초기화 완료")
    
    def _create_app(self) -> Flask:
        """Flask 애플리케이션 생성"""
        app = Flask(__name__, 
                   template_folder='templates',
                   static_folder='static')
        
        app.config.from_object(self.config)
        return app
    
    def _setup_socketio(self) -> SocketIO:
        """Socket.IO 설정"""
        return SocketIO(
            self.app,
            async_mode='threading',
            logger=False,
            engineio_logger=False,
            cors_allowed_origins="*"
        )
    
    def _setup_routes(self):
        """HTTP 라우트 설정"""
        
        @self.app.route('/')
        def index():
            """메인 페이지"""
            return render_template('index.html')
        
        @self.app.route('/api/health')
        def health_check():
            """헬스 체크 엔드포인트"""
            try:
                namespaces = self.k8s_service.get_namespaces()
                return jsonify({
                    "status": "healthy",
                    "kubectl_available": len(namespaces) > 0,
                    "namespaces_count": len(namespaces)
                })
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "error": str(e)
                }), 500
        
        @self.app.route('/api/data')
        def get_graph_data():
            """실제 클러스터 데이터 기반 그래프 API"""
            resource_type = request.args.get('resource_type', 'pod')
            
            try:
                logger.info(f"실제 클러스터 데이터 요청: {resource_type}")
                start_time = time.time()
                
                nodes = []
                edges = []
                namespaces = set()
                
                # 1. 네트워크 정책 수집
                policies = self.k8s_service.get_network_policies()
                logger.info(f"네트워크 정책 {len(policies)}개 수집")
                
                for policy in policies:
                    metadata = policy.get('metadata', {})
                    name = metadata.get('name', 'unknown')
                    namespace = metadata.get('namespace', 'default')
                    namespaces.add(namespace)
                    
                    policy_node = {
                        'id': f"{namespace}/{name}",
                        'label': name,
                        'group': 'policy',
                        'namespace': namespace,
                        'status': 'Active',
                        'policy_type': 'network-policy',
                        'metadata': metadata,
                        'spec': policy.get('spec', {})
                    }
                    nodes.append(policy_node)
                
                # 2. 리소스 수집 (resource_type에 따라)
                if resource_type == 'pod':
                    resources = self.k8s_service.get_pods()
                    logger.info(f"Pod {len(resources)}개 수집")
                    
                    for resource in resources:
                        metadata = resource.get('metadata', {})
                        name = metadata.get('name', 'unknown')
                        namespace = metadata.get('namespace', 'default')
                        namespaces.add(namespace)
                        
                        status = resource.get('status', {}).get('phase', 'Unknown')
                        
                        resource_node = {
                            'id': f"{namespace}/{name}",
                            'label': name,
                            'group': 'pod',
                            'namespace': namespace,
                            'status': status,
                            'metadata': metadata,
                            'labels': metadata.get('labels', {})
                        }
                        nodes.append(resource_node)
                        
                elif resource_type == 'deployment':
                    resources = self.k8s_service.get_deployments()
                    logger.info(f"Deployment {len(resources)}개 수집")
                    
                    for resource in resources:
                        metadata = resource.get('metadata', {})
                        name = metadata.get('name', 'unknown')
                        namespace = metadata.get('namespace', 'default')
                        namespaces.add(namespace)
                        
                        status_info = resource.get('status', {})
                        ready_replicas = status_info.get('readyReplicas', 0)
                        replicas = status_info.get('replicas', 0)
                        status = f"{ready_replicas}/{replicas} Ready"
                        
                        # Deployment의 selector 라벨을 가져옴
                        spec = resource.get('spec', {})
                        selector = spec.get('selector', {}).get('matchLabels', {})
                        template_labels = spec.get('template', {}).get('metadata', {}).get('labels', {})
                        
                        resource_node = {
                            'id': f"{namespace}/{name}",
                            'label': name,
                            'group': 'deployment',
                            'namespace': namespace,
                            'status': status,
                            'metadata': metadata,
                            'labels': template_labels,  # Pod template의 라벨 사용
                            'selector': selector,
                            'spec': spec
                        }
                        nodes.append(resource_node)
                else:
                    logger.warning(f"지원하지 않는 리소스 타입: {resource_type}")
                    resources = []
                
                # 3. 정책-리소스 연결 관계 생성 (실제 정책 매칭 로직)
                policy_nodes = [n for n in nodes if n['group'] == 'policy']
                resource_nodes = [n for n in nodes if n['group'] in ['pod', 'deployment']]
                
                for policy_node in policy_nodes:
                    policy_spec = policy_node.get('spec', {})
                    pod_selector = policy_spec.get('podSelector', {})
                    policy_namespace = policy_node['namespace']
                    policy_types = policy_spec.get('policyTypes', [])
                    
                    # 정책이 적용되는 대상 리소스들 찾기
                    target_resources = []
                    for resource_node in resource_nodes:
                        # 같은 네임스페이스인지 확인
                        if resource_node['namespace'] != policy_namespace:
                            continue
                        
                        # 리소스 라벨 확인 (Pod template 라벨 사용)
                        resource_labels = resource_node.get('labels', {})
                        
                        # 빈 selector는 모든 리소스 선택
                        if not pod_selector:
                            target_resources.append(resource_node)
                        elif 'matchLabels' in pod_selector:
                            match_labels = pod_selector['matchLabels']
                            if all(resource_labels.get(k) == v for k, v in match_labels.items()):
                                target_resources.append(resource_node)
                    
                    # 정책 적용 관계 엣지 생성
                    for target_resource in target_resources:
                        edge = {
                            'id': f"policy-{policy_node['id']}-{target_resource['id']}",
                            'source': policy_node['id'],
                            'target': target_resource['id'],
                            'type': 'applies-to',
                            'style': 'dashed',
                            'label': f"applies to ({', '.join(policy_types)})",
                            'policy_types': policy_types
                        }
                        edges.append(edge)
                    
                    # Ingress 규칙 기반 통신 허용 엣지 생성
                    if 'Ingress' in policy_types:
                        ingress_rules = policy_spec.get('ingress', [])
                        if ingress_rules:  # 빈 배열이 아닌 경우만 허용 규칙 생성
                            for rule in ingress_rules:
                                from_selectors = rule.get('from', [])
                                ports = rule.get('ports', [])
                                port_info = self._format_port_info(ports)
                                
                                # from이 비어있으면 모든 소스에서 허용
                                if not from_selectors:
                                    for source_resource in resource_nodes:
                                        if source_resource['namespace'] == policy_namespace:
                                            for target_resource in target_resources:
                                                if source_resource['id'] != target_resource['id']:
                                                    edge = {
                                                        'id': f"ingress-{source_resource['id']}-{target_resource['id']}",
                                                        'source': source_resource['id'],
                                                        'target': target_resource['id'],
                                                        'type': 'ingress-allowed',
                                                        'style': 'solid',
                                                        'label': f"ingress allowed {port_info}",
                                                        'policy': policy_node['id'],
                                                        'ports': port_info
                                                    }
                                                    edges.append(edge)
                                else:
                                    # from 조건에 맞는 소스 리소스들 찾기
                                    for from_selector in from_selectors:
                                        source_resources = self._find_matching_resources(from_selector, resource_nodes, policy_namespace)
                                        for source_resource in source_resources:
                                            for target_resource in target_resources:
                                                if source_resource['id'] != target_resource['id']:
                                                    edge = {
                                                        'id': f"ingress-{source_resource['id']}-{target_resource['id']}",
                                                        'source': source_resource['id'],
                                                        'target': target_resource['id'],
                                                        'type': 'ingress-allowed',
                                                        'style': 'solid',
                                                        'label': f"ingress allowed {port_info}",
                                                        'policy': policy_node['id'],
                                                        'ports': port_info
                                                    }
                                                    edges.append(edge)
                
                # 응답 데이터 구성
                processing_time = time.time() - start_time
                response_data = {
                    'nodes': nodes,
                    'edges': edges,
                    'namespaces': list(namespaces),
                    'metadata': {
                        "resource_type": resource_type,
                        "total_policies": len(policy_nodes),
                        "total_resources": len(resource_nodes),
                        "total_connections": len(edges),
                        "processing_time": round(processing_time, 2),
                        "data_source": "real_cluster"
                    }
                }
                
                logger.info(f"실제 데이터 반환 완료: {len(nodes)} nodes, {len(edges)} edges, {processing_time:.2f}s")
                return jsonify(response_data)
                
            except Exception as e:
                logger.error(f"그래프 데이터 조회 실패: {str(e)}")
                return jsonify({
                    "error": str(e),
                    "nodes": [],
                    "edges": [],
                    "namespaces": [],
                    "metadata": {"error": str(e)}
                }), 500
        
        @self.app.route('/api/policy/<path:policy_id>')
        def get_policy_details(policy_id: str):
            """네트워크 정책 상세 정보 API"""
            try:
                # URL 디코딩
                decoded_policy_id = urllib.parse.unquote(policy_id)
                logger.info(f"정책 상세 정보 요청: {decoded_policy_id}")
                
                # namespace/name 형태로 파싱
                if '/' in decoded_policy_id:
                    namespace, name = decoded_policy_id.split('/', 1)
                else:
                    return jsonify({"error": "잘못된 정책 ID 형식"}), 400
                
                # 실제 클러스터에서 정책 조회
                policies = self.k8s_service.get_network_policies()
                target_policy = None
                
                for policy in policies:
                    metadata = policy.get('metadata', {})
                    if (metadata.get('namespace') == namespace and 
                        metadata.get('name') == name):
                        target_policy = policy
                        break
                
                if not target_policy:
                    logger.warning(f"정책을 찾을 수 없음: {decoded_policy_id}")
                    # 기본 응답 반환
                    return jsonify({
                        "id": decoded_policy_id,
                        "name": name,
                        "namespace": namespace,
                        "spec": {"podSelector": {}, "policyTypes": ["Ingress"]},
                        "metadata": {"name": name, "namespace": namespace},
                        "analysis": {
                            "affected_pods_count": 0,
                            "security_level": "알 수 없음",
                            "policy_types": ["Ingress"],
                            "ingress_rules_count": 0,
                            "egress_rules_count": 0
                        }
                    })
                
                # 정책 분석 정보 추가
                policy_spec = target_policy.get('spec', {})
                
                # 보안 수준 계산
                has_ingress = 'ingress' in policy_spec
                has_egress = 'egress' in policy_spec
                
                if has_ingress and has_egress:
                    security_level = "높음"
                elif has_ingress or has_egress:
                    security_level = "중간"
                else:
                    security_level = "낮음"
                
                # 정책 타입 결정
                policy_types = []
                if has_ingress:
                    policy_types.append("Ingress")
                if has_egress:
                    policy_types.append("Egress")
                if not policy_types:
                    policy_types.append("Default")
                
                response_data = {
                    "id": decoded_policy_id,
                    "name": name,
                    "namespace": namespace,
                    "spec": policy_spec,
                    "metadata": target_policy.get('metadata', {}),
                    "analysis": {
                        "affected_pods_count": 0,  # 간단화
                        "security_level": security_level,
                        "policy_types": policy_types,
                        "ingress_rules_count": len(policy_spec.get('ingress', [])),
                        "egress_rules_count": len(policy_spec.get('egress', []))
                    }
                }
                
                return jsonify(response_data)
                
            except Exception as e:
                logger.error(f"정책 상세 정보 조회 실패: {str(e)}")
                return jsonify({"error": f"정책 조회 실패: {str(e)}"}), 500
        
        @self.app.route('/api/resource/<resource_type>/<path:resource_id>')
        def get_resource_details(resource_type: str, resource_id: str):
            """리소스 상세 정보 API"""
            try:
                # URL 디코딩
                decoded_resource_id = urllib.parse.unquote(resource_id)
                logger.info(f"리소스 상세 정보 요청: {resource_type}/{decoded_resource_id}")
                
                # namespace/name 형태로 파싱
                if '/' in decoded_resource_id:
                    namespace, name = decoded_resource_id.split('/', 1)
                else:
                    return jsonify({"error": "잘못된 리소스 ID 형식"}), 400
                
                # 실제 클러스터에서 리소스 조회
                if resource_type == 'pod':
                    resources = self.k8s_service.get_pods()
                elif resource_type == 'deployment':
                    resources = self.k8s_service.get_deployments()
                else:
                    return jsonify({"error": "지원하지 않는 리소스 타입"}), 400
                
                target_resource = None
                for resource in resources:
                    metadata = resource.get('metadata', {})
                    if (metadata.get('namespace') == namespace and 
                        metadata.get('name') == name):
                        target_resource = resource
                        break
                
                if not target_resource:
                    logger.warning(f"리소스를 찾을 수 없음: {decoded_resource_id}")
                    # 기본 응답 반환
                    kind = "Deployment" if resource_type == 'deployment' else "Pod"
                    status = {"replicas": 0, "readyReplicas": 0} if resource_type == 'deployment' else {"phase": "Unknown"}
                    
                    return jsonify({
                        "id": decoded_resource_id,
                        "name": name,
                        "namespace": namespace,
                        "kind": kind,
                        "metadata": {"name": name, "namespace": namespace},
                        "spec": {},
                        "status": status,
                        "analysis": {
                            "applied_policies_count": 0,
                            "security_level": "알 수 없음"
                        }
                    })
                
                # 응답 데이터 구성
                kind = target_resource.get('kind', 'Deployment' if resource_type == 'deployment' else 'Pod')
                
                response_data = {
                    "id": decoded_resource_id,
                    "name": name,
                    "namespace": namespace,
                    "kind": kind,
                    "metadata": target_resource.get('metadata', {}),
                    "spec": target_resource.get('spec', {}),
                    "status": target_resource.get('status', {}),
                    "analysis": {
                        "applied_policies_count": 0,  # 간단화
                        "security_level": "중간"
                    }
                }
                
                return jsonify(response_data)
                
            except Exception as e:
                logger.error(f"리소스 상세 정보 조회 실패: {str(e)}")
                return jsonify({"error": f"리소스 조회 실패: {str(e)}"}), 500
        
        @self.app.route('/api/namespaces')
        def get_namespaces():
            """네임스페이스 목록 API"""
            try:
                namespaces = self.k8s_service.get_namespaces()
                return jsonify({
                    "namespaces": namespaces,
                    "count": len(namespaces)
                })
            except Exception as e:
                logger.error(f"네임스페이스 조회 실패: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/simulate', methods=['POST'])
        def simulate_communication():
            """통신 시뮬레이션 API"""
            try:
                data = request.get_json()
                source_id = data.get('source')
                target_id = data.get('target')
                port = data.get('port', 80)
                protocol = data.get('protocol', 'TCP')
                
                if not source_id or not target_id:
                    return jsonify({"error": "source와 target이 필요합니다"}), 400
                
                logger.info(f"통신 시뮬레이션 요청: {source_id} -> {target_id}:{port}/{protocol}")
                
                # 통신 가능성 분석
                result = self._simulate_network_communication(source_id, target_id, port, protocol)
                
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"통신 시뮬레이션 실패: {e}")
                return jsonify({"error": str(e)}), 500
    
    def _format_port_info(self, ports):
        """포트 정보 포맷팅"""
        if not ports:
            return "All Ports"
        
        port_strs = []
        for port in ports:
            protocol = port.get('protocol', 'TCP')
            port_num = port.get('port', 'All')
            port_strs.append(f"{protocol}:{port_num}")
        
        return ", ".join(port_strs)
    
    def _find_matching_resources(self, selector, resource_nodes, current_namespace):
        """selector 조건에 맞는 리소스들 찾기"""
        matching_resources = []
        
        # podSelector 처리 (Pod와 Deployment 모두 적용)
        if 'podSelector' in selector:
            pod_selector = selector['podSelector']
            for resource in resource_nodes:
                if resource['namespace'] != current_namespace:
                    continue
                    
                resource_labels = resource.get('labels', {})
                
                if not pod_selector:  # 빈 selector = 모든 리소스
                    matching_resources.append(resource)
                elif 'matchLabels' in pod_selector:
                    match_labels = pod_selector['matchLabels']
                    if all(resource_labels.get(k) == v for k, v in match_labels.items()):
                        matching_resources.append(resource)
        
        # namespaceSelector 처리
        elif 'namespaceSelector' in selector:
            ns_selector = selector['namespaceSelector']
            target_namespaces = []
            
            if not ns_selector:  # 빈 selector = 모든 네임스페이스
                target_namespaces = list(set(resource['namespace'] for resource in resource_nodes))
            elif 'matchLabels' in ns_selector:
                # 간단히 이름으로 매치
                match_labels = ns_selector['matchLabels']
                if 'name' in match_labels:
                    target_namespaces = [match_labels['name']]
            
            for resource in resource_nodes:
                if resource['namespace'] in target_namespaces:
                    matching_resources.append(resource)
        
        return matching_resources
    
    def _simulate_network_communication(self, source_id, target_id, port, protocol):
        """네트워크 통신 시뮬레이션"""
        try:
            # 리소스 정보 가져오기
            source_info = self._get_resource_info(source_id)
            target_info = self._get_resource_info(target_id)
            
            if not source_info or not target_info:
                return {
                    "allowed": False,
                    "reason": "소스 또는 타겟 리소스를 찾을 수 없습니다",
                    "source": source_id,
                    "target": target_id,
                    "port": port,
                    "protocol": protocol,
                    "policy_results": []
                }
            
            # 적용 가능한 정책들 찾기
            applicable_policies = self._find_applicable_policies(source_info, target_info)
            
            # 각 정책에 대해 통신 허용 여부 확인
            policy_results = []
            final_decision = True
            
            for policy_id, policy_spec in applicable_policies.items():
                result = self._check_policy_allows_communication(
                    policy_spec, source_info, target_info, port, protocol
                )
                
                policy_results.append({
                    "policy": policy_id,
                    "allowed": result["allowed"],
                    "reason": result["reason"],
                    "rule_matched": result.get("rule_matched"),
                    "ports_allowed": result.get("ports_allowed", [])
                })
                
                # 하나라도 차단하면 최종 결과는 차단
                if not result["allowed"]:
                    final_decision = False
            
            # 정책이 없는 경우 기본 허용
            if not applicable_policies:
                policy_results.append({
                    "policy": "default",
                    "allowed": True,
                    "reason": "적용된 네트워크 정책이 없어 기본적으로 허용됩니다",
                    "rule_matched": None,
                    "ports_allowed": ["All"]
                })
            
            return {
                "allowed": final_decision,
                "source": source_info,
                "target": target_info,
                "port": port,
                "protocol": protocol,
                "policy_results": policy_results,
                "summary": "✅ 통신이 허용됩니다" if final_decision else "❌ 통신이 차단됩니다"
            }
            
        except Exception as e:
            logger.error(f"통신 시뮬레이션 중 오류: {e}")
            return {
                "allowed": False,
                "reason": f"시뮬레이션 오류: {str(e)}",
                "source": source_id,
                "target": target_id,
                "port": port,
                "protocol": protocol,
                "policy_results": []
            }
    
    def _get_resource_info(self, resource_id):
        """리소스 정보 가져오기"""
        try:
            # namespace/name 형태로 파싱
            if '/' not in resource_id:
                return None
            
            namespace, name = resource_id.split('/', 1)
            
            # 실제 클러스터에서 Pod 조회
            pods = self.k8s_service.get_pods()
            
            for pod in pods:
                metadata = pod.get('metadata', {})
                if (metadata.get('namespace') == namespace and 
                    metadata.get('name') == name):
                    return {
                        'id': resource_id,
                        'name': name,
                        'namespace': namespace,
                        'labels': metadata.get('labels', {}),
                        'type': 'pod'
                    }
            
            # Deployment 조회
            deployments = self.k8s_service.get_deployments()
            
            for deployment in deployments:
                metadata = deployment.get('metadata', {})
                if (metadata.get('namespace') == namespace and 
                    metadata.get('name') == name):
                    # Deployment의 Pod template 라벨 사용
                    spec = deployment.get('spec', {})
                    template_labels = spec.get('template', {}).get('metadata', {}).get('labels', {})
                    
                    return {
                        'id': resource_id,
                        'name': name,
                        'namespace': namespace,
                        'labels': template_labels,
                        'type': 'deployment'
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"리소스 정보 조회 실패: {e}")
            return None
    
    def _find_applicable_policies(self, source_info, target_info):
        """적용 가능한 정책들 찾기"""
        applicable_policies = {}
        
        try:
            policies = self.k8s_service.get_network_policies()
            
            for policy in policies:
                metadata = policy.get('metadata', {})
                policy_namespace = metadata.get('namespace', 'default')
                policy_name = metadata.get('name', 'unknown')
                policy_id = f"{policy_namespace}/{policy_name}"
                policy_spec = policy.get('spec', {})
                
                # Ingress 정책 확인 (타겟에 적용)
                if ('Ingress' in policy_spec.get('policyTypes', []) and 
                    target_info['namespace'] == policy_namespace and
                    self._pod_matches_selector(target_info, policy_spec.get('podSelector', {}))):
                    applicable_policies[policy_id] = policy_spec
                
                # Egress 정책 확인 (소스에 적용)
                if ('Egress' in policy_spec.get('policyTypes', []) and 
                    source_info['namespace'] == policy_namespace and
                    self._pod_matches_selector(source_info, policy_spec.get('podSelector', {}))):
                    applicable_policies[policy_id] = policy_spec
            
            return applicable_policies
            
        except Exception as e:
            logger.error(f"적용 가능한 정책 찾기 실패: {e}")
            return {}
    
    def _pod_matches_selector(self, pod_info, pod_selector):
        """Pod이 selector와 매치되는지 확인"""
        if not pod_selector:  # 빈 selector = 모든 Pod
            return True
        
        if 'matchLabels' in pod_selector:
            match_labels = pod_selector['matchLabels']
            pod_labels = pod_info.get('labels', {})
            return all(pod_labels.get(k) == v for k, v in match_labels.items())
        
        return False
    
    def _check_policy_allows_communication(self, policy_spec, source_info, target_info, port, protocol):
        """정책이 통신을 허용하는지 확인"""
        
        # Ingress 규칙 확인 (타겟 Pod에 적용)
        if ('Ingress' in policy_spec.get('policyTypes', []) and 
            self._pod_matches_selector(target_info, policy_spec.get('podSelector', {}))):
            
            ingress_rules = policy_spec.get('ingress', [])
            if not ingress_rules:  # 빈 배열 = 모든 ingress 차단
                return {
                    "allowed": False,
                    "reason": "Ingress 정책에 의해 모든 트래픽이 차단됩니다",
                    "rule_matched": "deny-all"
                }
            
            # 각 ingress 규칙 확인
            for rule in ingress_rules:
                if self._rule_allows_communication(rule, source_info, target_info, port, protocol, 'ingress'):
                    return {
                        "allowed": True,
                        "reason": "Ingress 규칙에 의해 허용됩니다",
                        "rule_matched": rule,
                        "ports_allowed": [f"{protocol}:{port}"]
                    }
            
            return {
                "allowed": False,
                "reason": "Ingress 규칙에 매치되지 않아 차단됩니다",
                "rule_matched": None
            }
        
        # Egress 규칙 확인 (소스 Pod에 적용)
        if ('Egress' in policy_spec.get('policyTypes', []) and 
            self._pod_matches_selector(source_info, policy_spec.get('podSelector', {}))):
            
            egress_rules = policy_spec.get('egress', [])
            if not egress_rules:  # 빈 배열 = 모든 egress 차단
                return {
                    "allowed": False,
                    "reason": "Egress 정책에 의해 모든 트래픽이 차단됩니다",
                    "rule_matched": "deny-all"
                }
            
            # 각 egress 규칙 확인
            for rule in egress_rules:
                if self._rule_allows_communication(rule, source_info, target_info, port, protocol, 'egress'):
                    return {
                        "allowed": True,
                        "reason": "Egress 규칙에 의해 허용됩니다",
                        "rule_matched": rule,
                        "ports_allowed": [f"{protocol}:{port}"]
                    }
            
            return {
                "allowed": False,
                "reason": "Egress 규칙에 매치되지 않아 차단됩니다",
                "rule_matched": None
            }
        
        # 정책이 적용되지 않는 경우 허용
        return {
            "allowed": True,
            "reason": "이 정책은 해당 통신에 적용되지 않습니다",
            "rule_matched": None
        }
    
    def _rule_allows_communication(self, rule, source_info, target_info, port, protocol, rule_type):
        """개별 규칙이 통신을 허용하는지 확인"""
        
        # 포트 확인
        rule_ports = rule.get('ports', [])
        if rule_ports:
            port_allowed = False
            for rule_port in rule_ports:
                if (rule_port.get('protocol', 'TCP') == protocol and 
                    rule_port.get('port') == port):
                    port_allowed = True
                    break
            if not port_allowed:
                return False
        
        # from/to 조건 확인
        if rule_type == 'ingress':
            selectors = rule.get('from', [])
            check_info = source_info
        else:  # egress
            selectors = rule.get('to', [])
            check_info = target_info
        
        if not selectors:  # 빈 배열 = 모든 대상 허용
            return True
        
        for selector in selectors:
            if self._selector_matches(selector, check_info, source_info, target_info):
                return True
        
        return False
    
    def _selector_matches(self, selector, check_info, source_info, target_info):
        """selector가 대상과 매치되는지 확인"""
        
        # podSelector
        if 'podSelector' in selector:
            return self._pod_matches_selector(check_info, selector['podSelector'])
        
        # namespaceSelector
        if 'namespaceSelector' in selector:
            ns_selector = selector['namespaceSelector']
            if not ns_selector:  # 빈 selector = 모든 네임스페이스
                return True
            if 'matchLabels' in ns_selector:
                # 간단히 네임스페이스 이름으로 매치
                return check_info['namespace'] == ns_selector['matchLabels'].get('name')
        
        # ipBlock
        if 'ipBlock' in selector:
            # 외부 연결인 경우
            return check_info.get('type') == 'external'
        
        # 빈 selector = 모든 대상
        if not selector or selector == {}:
            return True
        
        return False
    
    def run(self):
        """애플리케이션 실행"""
        logger.info(f"서버 시작: http://localhost:{self.config.APP_PORT}")
        self.socketio.run(
            self.app,
            host=self.config.APP_HOST,
            port=self.config.APP_PORT,
            debug=self.config.DEBUG
        )

def main():
    """메인 함수"""
    try:
        app = NetworkPolicyVisualizer()
        app.run()
    except KeyboardInterrupt:
        logger.info("애플리케이션 종료")
    except Exception as e:
        logger.error(f"애플리케이션 실행 실패: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
