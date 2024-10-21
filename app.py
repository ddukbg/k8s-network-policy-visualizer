from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import subprocess
import json
from threading import Thread, Lock
import time
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, async_mode='threading')  # 'threading'으로 설정

# 데이터 캐싱을 위한 변수
cached_graph_data = {
    'deployment': None,
    'pod': None
}
cache_lock = Lock()

def get_network_policies():
    try:
        result = subprocess.run(
            ["kubectl", "get", "networkpolicies", "--all-namespaces", "-o", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        policies = json.loads(result.stdout)
        return policies
    except subprocess.CalledProcessError as e:
        print(f"Error fetching network policies: {e.stderr}")
        return None

def get_pods():
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "--all-namespaces", "-o", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        pods = json.loads(result.stdout)
        return pods
    except subprocess.CalledProcessError as e:
        print(f"Error fetching pods: {e.stderr}")
        return None

def get_deployments():
    try:
        result = subprocess.run(
            ["kubectl", "get", "deployments", "--all-namespaces", "-o", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        deployments = json.loads(result.stdout)
        return deployments
    except subprocess.CalledProcessError as e:
        print(f"Error fetching deployments: {e.stderr}")
        return None

def get_namespaces():
    try:
        result = subprocess.run(
            ["kubectl", "get", "namespaces", "-o", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        namespaces = json.loads(result.stdout)
        return [item['metadata']['name'] for item in namespaces['items']]
    except subprocess.CalledProcessError as e:
        print(f"Error fetching namespaces: {e.stderr}")
        return []

def matches_selector(labels, selector):
    if not selector:
        return False
    for key, value in selector.get('matchLabels', {}).items():
        if labels.get(key) != value:
            return False
    return True

def map_policies_to_resources(policies, resources, resource_type='pod'):
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

    # Resource 초기화 (Pod 또는 Deployment)
    for resource in resources['items']:
        resource_name = resource['metadata']['name']
        resource_namespace = resource['metadata']['namespace']
        resource_labels = resource['metadata'].get('labels', {})
        resource_full_name = f"{resource_namespace}/{resource_name}"
        resource_map[resource_full_name] = {
            'id': resource_full_name,
            'label': resource_name,
            'group': resource_type,
            'labels': resource_labels,
            'status': resource.get('status', {}).get('phase', 'Unknown') if resource_type == 'pod' else 'Unknown',
            'policies': []  # 초기화
        }

    # 정책을 Resource에 매핑하고 엣지 생성
    for policy_key, policy in policy_map.items():
        for resource_key, resource in resource_map.items():
            resource_namespace, resource_name = resource_key.split('/')
            if resource_namespace != policy['namespace']:
                continue
            selector = policy['pod_selector']
            if matches_selector(resource['labels'], selector):
                # Ingress 규칙 추가
                for ingress_rule in policy['ingress']:
                    ports = ingress_rule.get('ports', [])
                    edges.append({
                        'source': policy_key,
                        'target': resource_key,
                        'type': 'ingress',
                        'ports': ports
                    })
                    resource['policies'].append(policy_key)  # 정책 추가

                # Egress 규칙 추가
                for egress_rule in policy['egress']:
                    ports = egress_rule.get('ports', [])
                    edges.append({
                        'source': policy_key,
                        'target': resource_key,
                        'type': 'egress',
                        'ports': ports
                    })
                    resource['policies'].append(policy_key)  # 정책 추가

    return policy_map, edges, resource_map

def get_hash(data):
    """JSON 데이터를 정렬된 키 순서로 직렬화한 후 SHA-256 해시를 생성합니다."""
    if data is None:
        return None
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    global cached_graph_data
    resource_type = request.args.get('resource_type', 'deployment')  # 기본값을 'deployment'로 설정

    with cache_lock:
        if cached_graph_data.get(resource_type):
            return jsonify(cached_graph_data[resource_type])

    policies = get_network_policies()
    if not policies:
        return jsonify({"error": "Failed to retrieve network policies."}), 500

    if resource_type == 'deployment':
        resources = get_deployments()
    else:
        resources = get_pods()

    if not resources:
        return jsonify({"error": f"Failed to retrieve {resource_type}s."}), 500

    policy_map, edges, resource_map = map_policies_to_resources(policies, resources, resource_type)

    # 그래프 데이터 준비
    nodes = []
    formatted_edges = []

    # 노드 추가
    for resource_key, resource in resource_map.items():
        nodes.append({
            'data': {'id': resource_key, 'label': resource['label'], 'group': resource['group']}
        })

    # 엣지 추가
    for edge in edges:
        # 포트 정보를 문자열로 변환
        ports = edge['ports']
        if ports:
            ports_str = ', '.join([f"{p.get('protocol', 'TCP')}/{p.get('port', 'N/A')}" for p in ports])
        else:
            ports_str = 'All Ports'

        formatted_edges.append({
            'data': {
                'source': edge['source'],
                'target': edge['target'],
                'type': edge['type'],
                'label': f"{edge['type'].capitalize()} ({ports_str})"
            }
        })

    # 중복 제거
    unique_nodes = {node['data']['id']: node for node in nodes}.values()
    unique_edges = formatted_edges  # 필요 시 중복 제거 로직 추가

    graph_data = {
        'nodes': list(unique_nodes),
        'edges': unique_edges
    }

    # 캐싱
    with cache_lock:
        cached_graph_data[resource_type] = graph_data

    return jsonify(graph_data)

@app.route('/namespaces')
def namespaces():
    namespaces = get_namespaces()
    return jsonify({"namespaces": namespaces})

# 새로운 엔드포인트: Policy 상세 정보
@app.route('/policy/<policy_name>')
def policy_details(policy_name):
    policies = get_network_policies()
    if not policies:
        return jsonify({"error": "Failed to retrieve network policies."}), 500

    for policy in policies['items']:
        if policy['metadata']['name'] == policy_name:
            return jsonify({
                'name': policy['metadata']['name'],
                'namespace': policy['metadata']['namespace'],
                'ingress': policy['spec'].get('ingress', []),
                'egress': policy['spec'].get('egress', [])
            })
    return jsonify({"error": "Policy not found."}), 404

# 새로운 엔드포인트: Resource 상세 정보 (Pod 또는 Deployment)
@app.route('/resource/<resource_type>/<path:resource_name>')
def resource_details(resource_type, resource_name):
    if resource_type == 'deployment':
        resources = get_deployments()
    elif resource_type == 'pod':
        resources = get_pods()
    else:
        return jsonify({"error": "Invalid resource type."}), 400

    if not resources:
        return jsonify({"error": f"Failed to retrieve {resource_type}s."}), 500

    for resource in resources['items']:
        full_resource_name = f"{resource['metadata']['namespace']}/{resource['metadata']['name']}"
        if full_resource_name == resource_name:
            if resource_type == 'deployment':
                return jsonify({
                    'name': resource['metadata']['name'],
                    'namespace': resource['metadata']['namespace'],
                    'labels': resource['metadata'].get('labels', {}),
                    'status': resource['status'].get('availableReplicas', 'Unknown')
                })
            elif resource_type == 'pod':
                return jsonify({
                    'name': resource['metadata']['name'],
                    'namespace': resource['metadata']['namespace'],
                    'labels': resource['metadata'].get('labels', {}),
                    'status': resource['status'].get('phase', 'Unknown')
                })
    return jsonify({"error": f"{resource_type.capitalize()} not found."}), 404

def monitor_changes():
    global cached_graph_data
    previous_policies = get_network_policies()
    previous_pods = get_pods()
    previous_deployments = get_deployments()

    previous_policies_hash = get_hash(previous_policies) if previous_policies else None
    previous_pods_hash = get_hash(previous_pods) if previous_pods else None
    previous_deployments_hash = get_hash(previous_deployments) if previous_deployments else None

    while True:
        try:
            time.sleep(60)  # 1분마다 체크
            current_policies = get_network_policies()
            current_pods = get_pods()
            current_deployments = get_deployments()

            current_policies_hash = get_hash(current_policies) if current_policies else None
            current_pods_hash = get_hash(current_pods) if current_pods else None
            current_deployments_hash = get_hash(current_deployments) if current_deployments else None

            policies_changed = current_policies_hash != previous_policies_hash
            pods_changed = current_pods_hash != previous_pods_hash
            deployments_changed = current_deployments_hash != previous_deployments_hash

            if policies_changed or pods_changed or deployments_changed:
                print(f"Updating deployment and pod data at {time.strftime('%Y-%m-%d %H:%M:%S')}")

                # Deployment 데이터 업데이트
                policy_map_deployment, edges_deployment, deployment_map = map_policies_to_resources(current_policies, current_deployments, 'deployment')
                nodes_deployment = []
                formatted_edges_deployment = []

                for policy_key, policy in policy_map_deployment.items():
                    nodes_deployment.append({
                        'data': {'id': policy_key, 'label': policy['label'], 'group': 'policy'}
                    })

                for deployment_key, deployment in deployment_map.items():
                    nodes_deployment.append({
                        'data': {'id': deployment_key, 'label': deployment['label'], 'group': 'deployment'}
                    })

                for edge in edges_deployment:
                    ports = edge['ports']
                    if ports:
                        ports_str = ', '.join([f"{p.get('protocol', 'TCP')}/{p.get('port', 'N/A')}" for p in ports])
                    else:
                        ports_str = 'All Ports'

                    formatted_edges_deployment.append({
                        'data': {
                            'source': edge['source'],
                            'target': edge['target'],
                            'type': edge['type'],
                            'label': f"{edge['type'].capitalize()} ({ports_str})"
                        }
                    })

                unique_nodes_deployment = {node['data']['id']: node for node in nodes_deployment}.values()
                unique_edges_deployment = formatted_edges_deployment  # 필요 시 중복 제거 로직 추가

                graph_data_deployment = {
                    'nodes': list(unique_nodes_deployment),
                    'edges': unique_edges_deployment
                }

                # Pod 데이터 업데이트
                policy_map_pod, edges_pod, pod_map = map_policies_to_resources(current_policies, current_pods, 'pod')
                nodes_pod = []
                formatted_edges_pod = []

                for policy_key, policy in policy_map_pod.items():
                    nodes_pod.append({
                        'data': {'id': policy_key, 'label': policy['label'], 'group': 'policy'}
                    })

                for pod_key, pod in pod_map.items():
                    nodes_pod.append({
                        'data': {'id': pod_key, 'label': pod['label'], 'group': 'pod'}
                    })

                for edge in edges_pod:
                    ports = edge['ports']
                    if ports:
                        ports_str = ', '.join([f"{p.get('protocol', 'TCP')}/{p.get('port', 'N/A')}" for p in ports])
                    else:
                        ports_str = 'All Ports'

                    formatted_edges_pod.append({
                        'data': {
                            'source': edge['source'],
                            'target': edge['target'],
                            'type': edge['type'],
                            'label': f"{edge['type'].capitalize()} ({ports_str})"
                        }
                    })

                unique_nodes_pod = {node['data']['id']: node for node in nodes_pod}.values()
                unique_edges_pod = formatted_edges_pod  # 필요 시 중복 제거 로직 추가

                graph_data_pod = {
                    'nodes': list(unique_nodes_pod),
                    'edges': unique_edges_pod
                }

                # 클라이언트에 업데이트 전송
                socketio.emit('update_deployment', graph_data_deployment)
                socketio.emit('update_pod', graph_data_pod)

                # 캐시 업데이트
                with cache_lock:
                    cached_graph_data['deployment'] = graph_data_deployment
                    cached_graph_data['pod'] = graph_data_pod

                # 이전 데이터 업데이트
                previous_policies = current_policies
                previous_pods = current_pods
                previous_deployments = current_deployments

                previous_policies_hash = current_policies_hash
                previous_pods_hash = current_pods_hash
                previous_deployments_hash = current_deployments_hash

        except Exception as e:
            print(f"Error in monitor_changes: {e}")

@socketio.on('connect')
def handle_connect():
    print('Client connected')

if __name__ == '__main__':
    thread = Thread(target=monitor_changes)
    thread.daemon = True
    thread.start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
