class K8sVisualizerError(Exception):
    """기본 애플리케이션 예외 클래스"""
    pass

class K8sConnectionError(K8sVisualizerError):
    """Kubernetes 클러스터 연결 오류"""
    pass

class ResourceNotFoundError(K8sVisualizerError):
    """요청한 리소스를 찾을 수 없음"""
    pass

class InvalidResourceTypeError(K8sVisualizerError):
    """잘못된 리소스 타입"""
    pass