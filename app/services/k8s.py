import subprocess
import json
from typing import Optional, Dict, List
from ..utils.exceptions import K8sConnectionError
from ..utils.logger import logger
from typing import Dict, List, Optional, Set, Tuple

def _run_kubectl_command(command: List[str]) -> dict:
    """kubectl 명령어를 실행하고 결과를 반환합니다."""
    try:
        logger.debug(f"Executing kubectl command: {' '.join(command)}")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"kubectl command failed: {e.stderr}")
        raise K8sConnectionError(f"Failed to execute kubectl command: {e.stderr}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse kubectl output: {e}")
        raise K8sConnectionError(f"Failed to parse kubectl output: {e}")

def get_network_policies() -> Dict:
    """Kubernetes cluster의 모든 네트워크 정책을 가져옵니다."""
    return _run_kubectl_command([
        "kubectl", "get", "networkpolicies",
        "--all-namespaces", "-o", "json"
    ])

def get_pods() -> Dict:
    """Kubernetes cluster의 모든 Pod을 가져옵니다."""
    return _run_kubectl_command([
        "kubectl", "get", "pods",
        "--all-namespaces", "-o", "json"
    ])

def get_deployments() -> Dict:
    """Kubernetes cluster의 모든 Deployment를 가져옵니다."""
    return _run_kubectl_command([
        "kubectl", "get", "deployments",
        "--all-namespaces", "-o", "json"
    ])

def get_namespaces() -> List[str]:
    """Kubernetes cluster의 모든 네임스페이스를 가져옵니다."""
    result = _run_kubectl_command([
        "kubectl", "get", "namespaces",
        "-o", "json"
    ])
    return [item['metadata']['name'] for item in result['items']]

class NetworkPolicyAnalyzer:
    def __init__(self, policies: Dict, resources: Dict):
        self.policies = policies['items']
        self.resources = resources['items']
        self._resource_policy_map = self._build_resource_policy_map()

    def _build_resource_policy_map(self) -> Dict:
        """각 리소스에 적용되는 NetworkPolicy를 매핑합니다."""
        resource_policies = {}
        
        for policy in self.policies:
            namespace = policy['metadata']['namespace']
            pod_selector = policy['spec'].get('podSelector', {})
            
            # 해당 정책이 적용되는 리소스 찾기
            for resource in self.resources:
                if resource['metadata']['namespace'] != namespace:
                    continue
                
                resource_name = f"{namespace}/{resource['metadata']['name']}"
                if self._matches_selector(resource['metadata'].get('labels', {}), pod_selector):
                    if resource_name not in resource_policies:
                        resource_policies[resource_name] = {
                            'ingress': [],
                            'egress': []
                        }
                    
                    if 'ingress' in policy['spec']:
                        resource_policies[resource_name]['ingress'].append(policy)
                    if 'egress' in policy['spec']:
                        resource_policies[resource_name]['egress'].append(policy)
        
        return resource_policies

    def _matches_selector(self, labels: Dict, selector: Dict) -> bool:
        """레이블이 선택자와 일치하는지 확인합니다."""
        match_labels = selector.get('matchLabels', {})
        if not match_labels:
            return True
            
        return all(labels.get(k) == v for k, v in match_labels.items())

    def analyze_communication(self, source: str, target: str) -> Dict:
        """두 리소스 간의 통신 가능성을 분석합니다."""
        source_policies = self._resource_policy_map.get(source, {'ingress': [], 'egress': []})
        target_policies = self._resource_policy_map.get(target, {'ingress': [], 'egress': []})

        # NetworkPolicy가 없는 경우
        if not source_policies['egress'] and not target_policies['ingress']:
            return {
                'allowed': True,
                'reason': 'No NetworkPolicies applied',
                'ports': ['all'],
                'policies': []
            }

        result = {
            'allowed': True,
            'blocked_by': [],
            'allowed_by': [],
            'ports': set(),
            'policies': []
        }

        # Egress 정책 확인
        if source_policies['egress']:
            egress_result = self._check_egress_rules(source_policies['egress'], target)
            if not egress_result['allowed']:
                result['allowed'] = False
                result['blocked_by'].extend(egress_result['blocked_by'])
            else:
                result['allowed_by'].extend(egress_result['allowed_by'])
                result['ports'].update(egress_result['ports'])

        # Ingress 정책 확인
        if target_policies['ingress']:
            ingress_result = self._check_ingress_rules(target_policies['ingress'], source)
            if not ingress_result['allowed']:
                result['allowed'] = False
                result['blocked_by'].extend(ingress_result['blocked_by'])
            else:
                result['allowed_by'].extend(ingress_result['allowed_by'])
                result['ports'].update(ingress_result['ports'])

        # 결과 정리
        if result['allowed']:
            result['reason'] = 'Communication allowed'
            result['ports'] = list(result['ports']) if result['ports'] else ['all']
            result['policies'] = [{'name': p, 'type': 'allow'} for p in result['allowed_by']]
        else:
            result['reason'] = 'Communication blocked by NetworkPolicies'
            result['policies'] = [{'name': p, 'type': 'block'} for p in result['blocked_by']]
            result['ports'] = []

        return result

    def _check_egress_rules(self, policies: List[Dict], target: str) -> Dict:
        """Egress 규칙을 확인합니다."""
        result = {
            'allowed': False,
            'blocked_by': [],
            'allowed_by': [],
            'ports': set()
        }

        target_namespace, target_name = target.split('/')
        
        for policy in policies:
            policy_name = f"{policy['metadata']['namespace']}/{policy['metadata']['name']}"
            
            if not policy['spec'].get('egress'):
                result['blocked_by'].append(policy_name)
                continue

            for rule in policy['spec']['egress']:
                if self._matches_egress_rule(rule, target_namespace, target_name):
                    result['allowed'] = True
                    result['allowed_by'].append(policy_name)
                    if rule.get('ports'):
                        result['ports'].update(
                            f"{p.get('protocol', 'TCP')}:{p['port']}"
                            for p in rule['ports']
                        )

        return result

    def _check_ingress_rules(self, policies: List[Dict], source: str) -> Dict:
        """Ingress 규칙을 확인합니다."""
        result = {
            'allowed': False,
            'blocked_by': [],
            'allowed_by': [],
            'ports': set()
        }

        source_namespace, source_name = source.split('/')
        
        for policy in policies:
            policy_name = f"{policy['metadata']['namespace']}/{policy['metadata']['name']}"
            
            if not policy['spec'].get('ingress'):
                result['blocked_by'].append(policy_name)
                continue

            for rule in policy['spec']['ingress']:
                if self._matches_ingress_rule(rule, source_namespace, source_name):
                    result['allowed'] = True
                    result['allowed_by'].append(policy_name)
                    if rule.get('ports'):
                        result['ports'].update(
                            f"{p.get('protocol', 'TCP')}:{p['port']}"
                            for p in rule['ports']
                        )

        return result

    def _matches_egress_rule(self, rule: Dict, target_namespace: str, target_name: str) -> bool:
        """Egress 규칙이 대상 리소스와 일치하는지 확인합니다."""
        if not rule.get('to'):
            return True

        for to in rule['to']:
            # IPBlock 처리
            if 'ipBlock' in to:
                # IP 기반 매칭 로직 필요
                continue

            # 네임스페이스 선택자 확인
            namespace_matches = True
            if 'namespaceSelector' in to:
                namespace_matches = self._matches_selector(
                    {'name': target_namespace}, 
                    to['namespaceSelector']
                )

            # Pod 선택자 확인
            pod_matches = True
            if 'podSelector' in to:
                target_resource = next(
                    (r for r in self.resources 
                     if r['metadata']['namespace'] == target_namespace 
                     and r['metadata']['name'] == target_name),
                    None
                )
                if target_resource:
                    pod_matches = self._matches_selector(
                        target_resource['metadata'].get('labels', {}),
                        to['podSelector']
                    )

            if namespace_matches and pod_matches:
                return True

        return False

    def _matches_ingress_rule(self, rule: Dict, source_namespace: str, source_name: str) -> bool:
        """Ingress 규칙이 소스 리소스와 일치하는지 확인합니다."""
        if not rule.get('from'):
            return True

        for from_ in rule['from']:
            # IPBlock 처리
            if 'ipBlock' in from_:
                # IP 기반 매칭 로직 필요
                continue

            # 네임스페이스 선택자 확인
            namespace_matches = True
            if 'namespaceSelector' in from_:
                namespace_matches = self._matches_selector(
                    {'name': source_namespace}, 
                    from_['namespaceSelector']
                )

            # Pod 선택자 확인
            pod_matches = True
            if 'podSelector' in from_:
                source_resource = next(
                    (r for r in self.resources 
                     if r['metadata']['namespace'] == source_namespace 
                     and r['metadata']['name'] == source_name),
                    None
                )
                if source_resource:
                    pod_matches = self._matches_selector(
                        source_resource['metadata'].get('labels', {}),
                        from_['podSelector']
                    )

            if namespace_matches and pod_matches:
                return True

        return False