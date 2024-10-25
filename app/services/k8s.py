import subprocess
import json
from typing import Optional, Dict, List
from ..utils.exceptions import K8sConnectionError
from ..utils.logger import logger

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