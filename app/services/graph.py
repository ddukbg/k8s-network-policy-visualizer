from typing import Dict, List, Tuple, Any
from ..utils.logger import logger

def matches_selector(labels, selector):
    """레이블 셀렉터 매칭 확인"""
    logger.debug(f"Matching labels {labels} against selector {selector}")
    
    # 빈 셀렉터는 모든 것과 매칭
    if not selector or not selector.get('matchLabels'):
        logger.debug("Empty selector, matching all")
        return True
        
    match_labels = selector.get('matchLabels', {})
    for key, value in match_labels.items():
        if labels.get(key) != value:
            logger.debug(f"Label mismatch: {key}={labels.get(key)} != {value}")
            return False
    
    logger.debug("Labels matched successfully")
    return True


def map_policies_to_resources(policies, resources, resource_type='pod'):
    logger.debug("Starting policy mapping")
    policy_map = {}
    edges = []
    resource_map = {}

    # Resource 초기화
    for resource in resources['items']:
        resource_name = resource['metadata']['name']
        resource_namespace = resource['metadata']['namespace']
        resource_labels = resource['metadata'].get('labels', {})
        resource_full_name = f"{resource_namespace}/{resource_name}"
        
        logger.debug(f"Adding resource: {resource_full_name} with labels: {resource_labels}")
        resource_map[resource_full_name] = {
            'id': resource_full_name,
            'label': resource_name,
            'group': resource_namespace,
            'type': resource_type,
            'labels': resource_labels
        }

    # NetworkPolicy 처리
    for policy in policies['items']:
        namespace = policy['metadata']['namespace']
        policy_name = policy['metadata']['name']
        logger.debug(f"\nProcessing policy: {policy_name} in namespace: {namespace}")
        
        # 정책이 적용되는 Pod 찾기
        pod_selector = policy['spec'].get('podSelector', {})
        selected_pods = []
        
        for resource_key, resource in resource_map.items():
            resource_ns = resource_key.split('/')[0]
            if resource_ns == namespace and matches_selector(resource['labels'], pod_selector):
                selected_pods.append(resource_key)
                logger.debug(f"Policy applies to pod: {resource_key}")

        # Egress 규칙 처리
        if 'egress' in policy['spec']:
            logger.debug("Processing egress rules")
            for egress in policy['spec']['egress']:
                for to in egress.get('to', []):
                    target_pods = []
                    ns_selector = to.get('namespaceSelector')
                    pod_selector = to.get('podSelector')
                    
                    if ns_selector and pod_selector:
                        # 크로스-네임스페이스 + Pod 선택
                        logger.debug(f"Cross-namespace pod selection - NS: {ns_selector}, Pod: {pod_selector}")
                        for resource_key, resource in resource_map.items():
                            target_ns = resource_key.split('/')[0]
                            ns_labels = {'kubernetes.io/metadata.name': target_ns}
                            if (matches_selector(ns_labels, ns_selector) and 
                                matches_selector(resource['labels'], pod_selector)):
                                target_pods.append(resource_key)
                                logger.debug(f"Found target pod in other namespace: {resource_key}")
                    
                    elif ns_selector:
                        # 네임스페이스만 선택
                        logger.debug(f"Namespace-only selection: {ns_selector}")
                        for resource_key, resource in resource_map.items():
                            target_ns = resource_key.split('/')[0]
                            ns_labels = {'kubernetes.io/metadata.name': target_ns}
                            if matches_selector(ns_labels, ns_selector):
                                target_pods.append(resource_key)
                                logger.debug(f"Found target pod by namespace: {resource_key}")
                    
                    elif pod_selector:
                        # 같은 네임스페이스 내 Pod 선택
                        logger.debug(f"Same-namespace pod selection: {pod_selector}")
                        for resource_key, resource in resource_map.items():
                            if (resource_key.split('/')[0] == namespace and 
                                matches_selector(resource['labels'], pod_selector)):
                                target_pods.append(resource_key)
                                logger.debug(f"Found target pod in same namespace: {resource_key}")

                    # 엣지 생성 (source -> target)
                    ports = egress.get('ports', [{'port': 80, 'protocol': 'TCP'}])
                    for source in selected_pods:
                        for target in target_pods:
                            edge = {
                                'source': source,
                                'target': target,
                                'type': 'egress',
                                'ports': ports,
                                'directed': True
                            }
                            edges.append(edge)
                            logger.debug(f"Created egress edge: {source} -> {target}")

        # Ingress 규칙 처리
        if 'ingress' in policy['spec']:
            logger.debug("Processing ingress rules")
            for ingress in policy['spec']['ingress']:
                for from_field in ingress.get('from', []):
                    source_pods = []
                    ns_selector = from_field.get('namespaceSelector')
                    pod_selector = from_field.get('podSelector')
                    
                    if ns_selector and pod_selector:
                        # 크로스-네임스페이스 + Pod 선택
                        logger.debug(f"Cross-namespace pod selection - NS: {ns_selector}, Pod: {pod_selector}")
                        for resource_key, resource in resource_map.items():
                            source_ns = resource_key.split('/')[0]
                            ns_labels = {'kubernetes.io/metadata.name': source_ns}
                            if (matches_selector(ns_labels, ns_selector) and 
                                matches_selector(resource['labels'], pod_selector)):
                                source_pods.append(resource_key)
                                logger.debug(f"Found source pod in other namespace: {resource_key}")
                    
                    elif ns_selector:
                        # 네임스페이스만 선택
                        logger.debug(f"Namespace-only selection: {ns_selector}")
                        for resource_key, resource in resource_map.items():
                            source_ns = resource_key.split('/')[0]
                            ns_labels = {'kubernetes.io/metadata.name': source_ns}
                            if matches_selector(ns_labels, ns_selector):
                                source_pods.append(resource_key)
                                logger.debug(f"Found source pod by namespace: {resource_key}")
                    
                    elif pod_selector:
                        # 같은 네임스페이스 내 Pod 선택
                        logger.debug(f"Same-namespace pod selection: {pod_selector}")
                        for resource_key, resource in resource_map.items():
                            if (resource_key.split('/')[0] == namespace and 
                                matches_selector(resource['labels'], pod_selector)):
                                source_pods.append(resource_key)
                                logger.debug(f"Found source pod in same namespace: {resource_key}")

                    # 엣지 생성 (source -> target)
                    ports = ingress.get('ports', [{'port': 80, 'protocol': 'TCP'}])
                    for source in source_pods:
                        for target in selected_pods:
                            edge = {
                                'source': source,
                                'target': target,
                                'type': 'ingress',
                                'ports': ports,
                                'directed': True
                            }
                            edges.append(edge)
                            logger.debug(f"Created ingress edge: {source} -> {target}")

    logger.debug(f"Created total {len(edges)} edges")
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