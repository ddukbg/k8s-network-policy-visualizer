import subprocess
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import hashlib
import time
from threading import Lock

from ..models.kubernetes_models import (
    NetworkPolicy, Pod, Deployment,
    GraphData, GraphNode, GraphEdge, PortInfo,
    create_graph_node, create_graph_edge, create_port_info
)

logger = logging.getLogger(__name__)


class KubernetesService:
    """Kubernetes API와 상호작용하는 서비스"""
    
    def __init__(self, kubectl_timeout: int = 5, cache_timeout: int = 60):
        self.kubectl_timeout = kubectl_timeout
        self.cache_timeout = cache_timeout
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = Lock()
        
    def _run_kubectl_command(self, command: List[str]) -> Optional[Dict[str, Any]]:
        """kubectl 명령어 실행"""
        try:
            logger.info(f"kubectl 명령어 실행: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=self.kubectl_timeout
            )
            
            if not result.stdout.strip():
                logger.warning("kubectl 명령어 결과가 비어있습니다")
                return {"items": []}
                
            data = json.loads(result.stdout)
            logger.info(f"kubectl 명령어 성공: {len(data.get('items', []))}개 항목 조회")
            return data
            
        except subprocess.CalledProcessError as e:
            logger.error(f"kubectl 명령어 실행 실패: {e.stderr}")
            return {"items": []}
        except subprocess.TimeoutExpired:
            logger.error(f"kubectl 명령어 타임아웃 ({self.kubectl_timeout}초): {' '.join(command)}")
            return {"items": []}
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            logger.error(f"출력 내용: {result.stdout[:200]}...")
            return {"items": []}
    
    def _get_cache_key(self, resource_type: str, namespace: str = None) -> str:
        """캐시 키 생성"""
        key = f"{resource_type}"
        if namespace:
            key += f":{namespace}"
        return key
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """캐시 유효성 검사"""
        with self._cache_lock:
            if cache_key not in self._cache:
                return False
            
            cache_entry = self._cache[cache_key]
            expiry_time = cache_entry.get('expiry', datetime.min)
            return datetime.now() < expiry_time
    
    def _set_cache(self, cache_key: str, data: Any) -> None:
        """캐시 설정"""
        with self._cache_lock:
            self._cache[cache_key] = {
                'data': data,
                'expiry': datetime.now() + timedelta(seconds=self.cache_timeout)
            }
    
    def _get_cache(self, cache_key: str) -> Optional[Any]:
        """캐시 조회"""
        with self._cache_lock:
            if cache_key in self._cache and self._is_cache_valid(cache_key):
                return self._cache[cache_key]['data']
            return None
    
    def get_network_policies(self, namespace: str = None) -> List[NetworkPolicy]:
        """네트워크 정책 조회"""
        cache_key = self._get_cache_key('networkpolicies', namespace)
        
        # 캐시 확인
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        # kubectl 명령어 구성
        command = ["kubectl", "get", "networkpolicies"]
        if namespace:
            command.extend(["-n", namespace])
        else:
            command.append("--all-namespaces")
        command.extend(["-o", "json", f"--request-timeout={self.kubectl_timeout}s"])
        
        # API 호출
        data = self._run_kubectl_command(command)
        if not data:
            return []
        
        try:
            # 단순히 딕셔너리로 반환 (pydantic 제거로 인한 수정)
            policies = data.get('items', [])
            self._set_cache(cache_key, policies)
            return policies
        except Exception as e:
            logger.error(f"네트워크 정책 파싱 실패: {e}")
            return []
    
    def get_pods(self, namespace: str = None) -> List[Pod]:
        """Pod 조회"""
        cache_key = self._get_cache_key('pods', namespace)
        
        # 캐시 확인
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        # kubectl 명령어 구성
        command = ["kubectl", "get", "pods"]
        if namespace:
            command.extend(["-n", namespace])
        else:
            command.append("--all-namespaces")
        command.extend(["-o", "json", f"--request-timeout={self.kubectl_timeout}s"])
        
        # API 호출
        data = self._run_kubectl_command(command)
        if not data:
            return []
        
        try:
            # 단순히 딕셔너리로 반환 (pydantic 제거로 인한 수정)
            pods = data.get('items', [])
            self._set_cache(cache_key, pods)
            return pods
        except Exception as e:
            logger.error(f"Pod 파싱 실패: {e}")
            return []
    
    def get_deployments(self, namespace: str = None) -> List[Deployment]:
        """Deployment 조회"""
        cache_key = self._get_cache_key('deployments', namespace)
        
        # 캐시 확인
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        # kubectl 명령어 구성
        command = ["kubectl", "get", "deployments"]
        if namespace:
            command.extend(["-n", namespace])
        else:
            command.append("--all-namespaces")
        command.extend(["-o", "json", f"--request-timeout={self.kubectl_timeout}s"])
        
        # API 호출
        data = self._run_kubectl_command(command)
        if not data:
            return []
        
        try:
            # 단순히 딕셔너리로 반환 (pydantic 제거로 인한 수정)
            deployments = data.get('items', [])
            self._set_cache(cache_key, deployments)
            return deployments
        except Exception as e:
            logger.error(f"Deployment 파싱 실패: {e}")
            return []
    
    def get_namespaces(self) -> List[str]:
        """네임스페이스 목록 조회"""
        cache_key = self._get_cache_key('namespaces')
        
        # 캐시 확인
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        # kubectl 명령어 구성
        command = ["kubectl", "get", "namespaces", "-o", "json", f"--request-timeout={self.kubectl_timeout}s"]
        
        # API 호출
        data = self._run_kubectl_command(command)
        if not data:
            return []
        
        try:
            namespaces = [item['metadata']['name'] for item in data.get('items', [])]
            self._set_cache(cache_key, namespaces)
            return namespaces
        except Exception as e:
            logger.error(f"네임스페이스 파싱 실패: {e}")
            return []
    
    def clear_cache(self) -> None:
        """캐시 클리어"""
        with self._cache_lock:
            self._cache.clear()
            logger.info("캐시가 클리어되었습니다.")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 정보"""
        with self._cache_lock:
            return {
                'total_entries': len(self._cache),
                'entries': list(self._cache.keys()),
                'cache_timeout': self.cache_timeout
            } 