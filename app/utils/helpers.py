import json
import hashlib
import time
from typing import Optional, Dict, Any  # typing import 추가
from .. import socketio, cache_lock, cached_graph_data
from ..services.k8s import get_network_policies, get_pods, get_deployments
from ..services.graph import map_policies_to_resources
from ..utils.logger import logger  # logger import 추가

def get_hash(data: Optional[dict]) -> Optional[str]:
    """JSON 데이터의 SHA-256 해시를 생성합니다."""
    if data is None:
        return None
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

def monitor_changes() -> None:
    """
    Kubernetes 리소스의 변경사항을 모니터링하고 실시간 업데이트를 전송합니다.
    변경사항이 있을 때만 업데이트를 전송합니다.
    """
    global cached_graph_data
    logger.info("Starting monitor_changes thread")  # 시작 로그 추가
    
    try:
        previous_policies = get_network_policies()
        previous_pods = get_pods()
        previous_deployments = get_deployments()

        previous_policies_hash = get_hash(previous_policies)
        previous_pods_hash = get_hash(previous_pods)
        previous_deployments_hash = get_hash(previous_deployments)

        while True:
            try:
                time.sleep(60)  # 1분마다 체크
                
                # 현재 상태 가져오기
                current_policies = get_network_policies()
                current_pods = get_pods()
                current_deployments = get_deployments()

                current_policies_hash = get_hash(current_policies)
                current_pods_hash = get_hash(current_pods)
                current_deployments_hash = get_hash(current_deployments)

                # 실제 변경사항이 있는 경우에만 업데이트 전송
                if any([
                    current_policies_hash != previous_policies_hash,
                    current_pods_hash != previous_pods_hash,
                    current_deployments_hash != previous_deployments_hash
                ]):
                    logger.info(f"Changes detected at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # 변경된 리소스 타입 확인 및 업데이트
                    if current_deployments_hash != previous_deployments_hash:
                        logger.debug("Deployment changes detected")
                        _update_resource_data('deployment', current_policies, current_deployments)
                    
                    if current_pods_hash != previous_pods_hash:
                        logger.debug("Pod changes detected")
                        _update_resource_data('pod', current_policies, current_pods)

                    # 이전 상태 업데이트
                    previous_policies = current_policies
                    previous_pods = current_pods
                    previous_deployments = current_deployments
                    previous_policies_hash = current_policies_hash
                    previous_pods_hash = current_pods_hash
                    previous_deployments_hash = current_deployments_hash

            except Exception as e:
                logger.error(f"Error in monitor_changes loop: {e}", exc_info=True)
                time.sleep(5)  # 에러 발생 시 5초 대기 후 재시도

    except Exception as e:
        logger.error(f"Error in monitor_changes: {e}", exc_info=True)

def _update_resource_data(resource_type: str, policies: dict, resources: dict) -> None:
    """특정 리소스 타입의 데이터를 업데이트하고 클라이언트에 전송합니다."""
    try:
        policy_map, edges, resource_map = map_policies_to_resources(policies, resources, resource_type)
        
        nodes = [
            {'data': {'id': key, 'label': resource['label'], 'group': resource['group']}}
            for key, resource in resource_map.items()
        ]

        formatted_edges = []
        for edge in edges:
            ports = edge['ports']
            ports_str = ', '.join([
                f"{p.get('protocol', 'TCP')}/{p.get('port', 'N/A')}" 
                for p in ports
            ]) if ports else 'All Ports'
            
            formatted_edges.append({
                'data': {
                    'source': edge['source'],
                    'target': edge['target'],
                    'type': edge['type'],
                    'label': f"{edge['type'].capitalize()} ({ports_str})"
                }
            })

        graph_data = {
            'nodes': nodes,
            'edges': formatted_edges
        }

        # 캐시 업데이트
        with cache_lock:
            cached_graph_data[resource_type] = graph_data

        # 클라이언트에 업데이트 전송
        socketio.emit(f'update_{resource_type}', graph_data)
        logger.debug(f"Sent update for {resource_type}")

    except Exception as e:
        logger.error(f"Error updating {resource_type} data: {e}", exc_info=True)