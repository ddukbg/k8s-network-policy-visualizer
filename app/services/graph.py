from typing import Dict, List, Tuple, Any

def matches_selector(labels: Dict[str, str], selector: Dict[str, Any]) -> bool:
    """레이블이 선택자와 일치하는지 확인합니다."""
    if not selector:
        return False
    for key, value in selector.get('matchLabels', {}).items():
        if labels.get(key) != value:
            return False
    return True

def map_policies_to_resources(policies: Dict[str, Any], resources: Dict[str, Any], resource_type: str = 'pod') -> Tuple[Dict, List, Dict]:
    """네트워크 정책과 리소스(Pod 또는 Deployment)를 매핑합니다."""
    policy_map = {}
    edges = []
    resource_map = {}

    # 정책 매핑
    for policy in policies['items']:
        policy_name = policy['metadata']['name']
        namespace = policy['metadata']['namespace']
        policy_key = f"{namespace}/{policy_name}"
        policy_map[policy_key] = {
            'id': policy_key,
            'label': policy_name,
            'group': 'policy',
            'namespace': namespace,
            'pod_selector': policy['spec'].get('podSelector', {}),
            'ingress': policy['spec'].get('ingress', []),
            'egress': policy['spec'].get('egress', [])
        }
        # 정책 노드도 resource_map에 추가
        resource_map[policy_key] = {
            'id': policy_key,
            'label': policy_name,
            'group': 'policy',
            'labels': {},  # 정책은 레이블이 없음
            'status': 'Active',
            'policies': []
        }

    # Resource 초기화
    for resource in resources['items']:
        resource_name = resource['metadata']['name']
        resource_namespace = resource['metadata']['namespace']
        resource_labels = resource['metadata'].get('labels', {})
        resource_full_name = f"{resource_namespace}/{resource_name}"
        resource_map[resource_full_name] = {
            'id': resource_full_name,
            'label': f"{resource_name}",  # namespace는 제외
            'group': resource_type,
            'labels': resource_labels,
            'status': resource.get('status', {}).get('phase', 'Unknown') if resource_type == 'pod' else 'Unknown',
            'policies': []
        }

    # 정책을 Resource에 매핑하고 엣지 생성
    for policy_key, policy in policy_map.items():
        # Ingress 규칙 처리
        for ingress_rule in policy['ingress']:
            if 'ipBlock' in ingress_rule:
                _handle_ip_block(policy_key, ingress_rule, edges, resource_map, 'ingress')
            
            for from_field in ingress_rule.get('from', []):
                _handle_selector_rule(policy_key, from_field, ingress_rule, edges, resource_map, 'ingress', policy['namespace'])

        # Egress 규칙 처리
        for egress_rule in policy['egress']:
            if 'ipBlock' in egress_rule:
                _handle_ip_block(policy_key, egress_rule, edges, resource_map, 'egress')
            
            for to_field in egress_rule.get('to', []):
                _handle_selector_rule(policy_key, to_field, egress_rule, edges, resource_map, 'egress', policy['namespace'])

    return policy_map, edges, resource_map

def _handle_ip_block(policy_key: str, rule: Dict[str, Any], edges: List[Dict], resource_map: Dict, rule_type: str) -> None:
    """IPBlock 규칙을 처리합니다."""
    ip_block = rule['ipBlock']
    ip_block_id = f"{policy_key}/ipBlock"
    edges.append({
        'source': policy_key,
        'target': ip_block_id,
        'type': f'{rule_type}-ipBlock',
        'details': ip_block
    })
    resource_map[ip_block_id] = {
        'id': ip_block_id,
        'label': f"IPBlock: {ip_block.get('cidr', 'N/A')}",
        'group': 'ipblock',
        'labels': {},
        'status': 'N/A',
        'policies': [policy_key]
    }

def _handle_selector_rule(policy_key: str, selector_field: Dict[str, Any], rule: Dict[str, Any], 
                         edges: List[Dict], resource_map: Dict, rule_type: str, policy_namespace: str) -> None:
    """선택자 기반 규칙을 처리합니다."""
    for resource_key, resource in resource_map.items():
        resource_namespace = resource_key.split('/')[0]
        if resource_namespace != policy_namespace:
            continue
        if matches_selector(resource['labels'], selector_field.get('podSelector', {})) and \
           matches_selector({'name': resource_namespace}, selector_field.get('namespaceSelector', {})):
            ports = rule.get('ports', [])
            edges.append({
                'source': policy_key,
                'target': resource_key,
                'type': rule_type,
                'ports': ports
            })
            resource['policies'].append(policy_key)