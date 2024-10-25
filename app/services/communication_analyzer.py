# app/services/communication_analyzer.py

from typing import Dict, Set, List, Tuple, Any
from ..utils.logger import logger

class CommunicationAnalyzer:
    def __init__(self, policies: Dict, resources: Dict):
        self.policies = policies
        self.resources = resources
        self.communication_map = {}
        self.namespace_policies = self._group_policies_by_namespace()

    def _group_policies_by_namespace(self) -> Dict[str, List[Dict]]:
        """네임스페이스별로 정책을 그룹화합니다."""
        namespace_policies = {}
        for policy in self.policies['items']:
            namespace = policy['metadata']['namespace']
            if namespace not in namespace_policies:
                namespace_policies[namespace] = []
            namespace_policies[namespace].append(policy)
        return namespace_policies

    def analyze_communications(self) -> Dict:
        """전체 리소스 간의 통신 가능성을 분석합니다."""
        for resource in self.resources['items']:
            resource_name = f"{resource['metadata']['namespace']}/{resource['metadata']['name']}"
            self.communication_map[resource_name] = {
                'allowed_ingress': set(),  # 들어오는 통신 허용
                'allowed_egress': set(),   # 나가는 통신 허용
                'blocked_ingress': set(),  # 들어오는 통신 차단
                'blocked_egress': set(),   # 나가는 통신 차단
                'policies': {
                    'ingress': [],         # 영향을 주는 ingress 정책들
                    'egress': []           # 영향을 주는 egress 정책들
                }
            }

        self._analyze_network_policies()
        return self.communication_map

    def _analyze_network_policies(self):
        """네트워크 정책을 분석하여 통신 가능성을 평가합니다."""
        for policy in self.policies['items']:
            namespace = policy['metadata']['namespace']
            policy_name = policy['metadata']['name']
            policy_types = policy['spec'].get('policyTypes', [])
            
            # 정책이 적용되는 대상 Pod 찾기
            affected_pods = self._get_affected_pods(policy)
            
            # Ingress 규칙 분석
            if 'Ingress' in policy_types:
                ingress_rules = policy['spec'].get('ingress', [])
                for pod in affected_pods:
                    self.communication_map[pod]['policies']['ingress'].append(policy_name)
                    self._analyze_ingress_rules(pod, ingress_rules, policy)

            # Egress 규칙 분석
            if 'Egress' in policy_types:
                egress_rules = policy['spec'].get('egress', [])
                for pod in affected_pods:
                    self.communication_map[pod]['policies']['egress'].append(policy_name)
                    self._analyze_egress_rules(pod, egress_rules, policy)

    def _get_affected_pods(self, policy: Dict) -> List[str]:
        """정책이 적용되는 Pod들을 찾습니다."""
        affected_pods = []
        namespace = policy['metadata']['namespace']
        pod_selector = policy['spec'].get('podSelector', {})

        for resource in self.resources['items']:
            if resource['metadata']['namespace'] != namespace:
                continue

            if self._matches_selector(resource['metadata'].get('labels', {}), pod_selector):
                resource_name = f"{namespace}/{resource['metadata']['name']}"
                affected_pods.append(resource_name)

        return affected_pods

    def _matches_selector(self, labels: Dict, selector: Dict) -> bool:
        """레이블이 선택자와 일치하는지 확인합니다."""
        match_labels = selector.get('matchLabels', {})
        if not match_labels:  # 빈 선택자는 모든 것과 매치
            return True
            
        for key, value in match_labels.items():
            if labels.get(key) != value:
                return False
        return True

    def _analyze_ingress_rules(self, target_pod: str, rules: List[Dict], policy: Dict):
        """Ingress 규칙을 분석합니다."""
        if not rules:  # 규칙이 없으면 모든 인그레스 트래픽 차단
            self._block_all_ingress(target_pod, policy)
            return

        for rule in rules:
            # From 필드 분석
            from_pods = self._get_pods_from_rule(rule.get('from', []), policy['metadata']['namespace'])
            ports = rule.get('ports', [])

            # 허용된 Pod들 기록
            for source_pod in from_pods:
                self.communication_map[target_pod]['allowed_ingress'].add((source_pod, self._format_ports(ports)))

    def _analyze_egress_rules(self, source_pod: str, rules: List[Dict], policy: Dict):
        """Egress 규칙을 분석합니다."""
        if not rules:  # 규칙이 없으면 모든 이그레스 트래픽 차단
            self._block_all_egress(source_pod, policy)
            return

        for rule in rules:
            # To 필드 분석
            to_pods = self._get_pods_from_rule(rule.get('to', []), policy['metadata']['namespace'])
            ports = rule.get('ports', [])

            # 허용된 Pod들 기록
            for target_pod in to_pods:
                self.communication_map[source_pod]['allowed_egress'].add((target_pod, self._format_ports(ports)))

    def _get_pods_from_rule(self, rule_peers: List[Dict], policy_namespace: str) -> Set[str]:
        """규칙에서 매칭되는 Pod들을 찾습니다."""
        matching_pods = set()

        for peer in rule_peers:
            if 'podSelector' in peer:
                # 같은 네임스페이스의 Pod만 선택
                matching_pods.update(self._get_pods_by_selector(
                    peer['podSelector'], 
                    policy_namespace
                ))
            
            if 'namespaceSelector' in peer:
                # 선택된 네임스페이스의 모든 Pod 선택
                matching_pods.update(self._get_pods_by_namespace_selector(
                    peer['namespaceSelector']
                ))

            if 'ipBlock' in peer:
                # IPBlock은 별도로 처리
                cidr = peer['ipBlock']['cidr']
                matching_pods.add(f"ipBlock:{cidr}")

        return matching_pods

    def _format_ports(self, ports: List[Dict]) -> str:
        """포트 정보를 문자열로 포맷팅합니다."""
        if not ports:
            return "all ports"
        
        return ", ".join([
            f"{port.get('protocol', 'TCP')}:{port.get('port', '*')}"
            for port in ports
        ])

    def check_communication(self, source: str, target: str) -> Dict:
        """두 리소스 간의 통신 가능성을 확인합니다."""
        result = {
            'allowed': False,
            'reason': '',
            'ingress_policies': [],
            'egress_policies': [],
            'ports': []  # set 대신 list 사용
        }

        source_info = self.communication_map.get(source)
        target_info = self.communication_map.get(target)

        if not source_info or not target_info:
            result['reason'] = 'Source or target resource not found'
            return result

        # Egress 체크
        egress_allowed = False
        port_list = set()  # 임시로 set 사용
        for allowed_target, ports in source_info['allowed_egress']:
            if allowed_target == target:
                egress_allowed = True
                if ports != "all ports":
                    port_list.add(ports)

        # Ingress 체크
        ingress_allowed = False
        for allowed_source, ports in target_info['allowed_ingress']:
            if allowed_source == source:
                ingress_allowed = True
                if ports != "all ports":
                    port_list.add(ports)

        result['allowed'] = egress_allowed and ingress_allowed
        result['ingress_policies'] = list(target_info['policies']['ingress'])
        result['egress_policies'] = list(source_info['policies']['egress'])
        result['ports'] = list(port_list)  # set을 list로 변환

        if result['allowed']:
            result['reason'] = 'Communication allowed'
            if not result['ports']:
                result['ports'] = ['all ports']
        else:
            result['reason'] = 'Communication blocked by network policies'

        return result

    def _block_all_ingress(self, pod: str, policy: Dict):
        """모든 인그레스 트래픽을 차단으로 표시합니다."""
        self.communication_map[pod]['blocked_ingress'].add(('all', policy['metadata']['name']))

    def _block_all_egress(self, pod: str, policy: Dict):
        """모든 이그레스 트래픽을 차단으로 표시합니다."""
        self.communication_map[pod]['blocked_egress'].add(('all', policy['metadata']['name']))

    def _get_pods_by_selector(self, pod_selector: Dict, namespace: str) -> Set[str]:
        """Pod 선택자에 매칭되는 Pod들을 찾습니다."""
        matching_pods = set()
        
        for resource in self.resources['items']:
            if resource['metadata']['namespace'] != namespace:
                continue
                
            if self._matches_selector(resource['metadata'].get('labels', {}), pod_selector):
                resource_name = f"{namespace}/{resource['metadata']['name']}"
                matching_pods.add(resource_name)
                
        return matching_pods

    def _get_pods_by_namespace_selector(self, namespace_selector: Dict) -> Set[str]:
        """네임스페이스 선택자에 매칭되는 Pod들을 찾습니다."""
        matching_pods = set()
        
        for resource in self.resources['items']:
            namespace = resource['metadata']['namespace']
            # 네임스페이스 레이블 확인 로직 필요
            if self._matches_selector({'name': namespace}, namespace_selector):
                resource_name = f"{namespace}/{resource['metadata']['name']}"
                matching_pods.add(resource_name)
                
        return matching_pods