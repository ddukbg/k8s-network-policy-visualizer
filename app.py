from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import subprocess
import json
from threading import Thread
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, async_mode='threading')  # 'threading'으로 설정

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

def matches_selector(pod_labels, selector):
    if not selector:
        return False
    for key, value in selector.get('matchLabels', {}).items():
        if pod_labels.get(key) != value:
            return False
    return True

def map_policies_to_pods(policies, pods):
    policy_map = {}
    
    for policy in policies['items']:
        policy_name = policy['metadata']['name']
        namespace = policy['metadata']['namespace']
        policy_map[policy_name] = {
            'namespace': namespace,
            'pod_selector': policy['spec'].get('podSelector', {}),
            'ingress': policy['spec'].get('ingress', []),
            'egress': policy['spec'].get('egress', [])
        }
    
    pod_map = {}
    
    for pod in pods['items']:
        pod_name = pod['metadata']['name']
        pod_namespace = pod['metadata']['namespace']
        pod_labels = pod['metadata'].get('labels', {})
        pod_map[f"{pod_namespace}/{pod_name}"] = {
            'labels': pod_labels,
            'policies': []  # 여기에 정책 정보를 추가할 예정
        }
    
    edges = []
    
    for policy_name, policy in policy_map.items():
        for pod_key, pod in pod_map.items():
            pod_namespace, pod_name = pod_key.split('/')
            if pod_namespace != policy['namespace']:
                continue
            selector = policy['pod_selector']
            if matches_selector(pod['labels'], selector):
                # Ingress 규칙 추가
                for ingress_rule in policy['ingress']:
                    ports = ingress_rule.get('ports', [])
                    edges.append({
                        'source': f"{policy['namespace']}/{policy_name}",
                        'target': pod_key,
                        'type': 'ingress',
                        'ports': ports
                    })
                
                # Egress 규칙 추가
                for egress_rule in policy['egress']:
                    ports = egress_rule.get('ports', [])
                    edges.append({
                        'source': f"{policy['namespace']}/{policy_name}",
                        'target': pod_key,
                        'type': 'egress',
                        'ports': ports
                    })
    
    return policy_map, edges


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    policies = get_network_policies()
    pods = get_pods()
    
    if not policies or not pods:
        return jsonify({"error": "Failed to retrieve data."}), 500
    
    policy_map, edges = map_policies_to_pods(policies, pods)
    
    # 그래프 데이터 준비
    nodes = []
    formatted_edges = []
    
    # 노드 추가
    for policy_name, policy in policy_map.items():
        policy_key = f"{policy['namespace']}/{policy_name}"
        nodes.append({
            'data': {'id': policy_key, 'label': policy_key, 'group': 'policy'}
        })
    
    for pod_key in policy_map.keys():
        pass  # 이미 policy 노드만 추가됨. 필요 시 Pod 노드도 추가 가능
    
    # Pod 노드 추가
    for pod_key in pods['items']:
        pod_full_name = f"{pod_key['metadata']['namespace']}/{pod_key['metadata']['name']}"
        nodes.append({
            'data': {'id': pod_full_name, 'label': pod_full_name, 'group': 'pod'}
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
        return jsonify({"error": "Failed to retrieve policies."}), 500
    
    for policy in policies['items']:
        if policy['metadata']['name'] == policy_name:
            return jsonify({
                'name': policy['metadata']['name'],
                'namespace': policy['metadata']['namespace'],
                'ingress': policy['spec'].get('ingress', []),
                'egress': policy['spec'].get('egress', [])
            })
    return jsonify({"error": "Policy not found."}), 404

# 새로운 엔드포인트: Pod 상세 정보
@app.route('/pod/<path:pod_name>')
def pod_details(pod_name):
    pods = get_pods()
    if not pods:
        return jsonify({"error": "Failed to retrieve pods."}), 500
    
    for pod in pods['items']:
        full_pod_name = f"{pod['metadata']['namespace']}/{pod['metadata']['name']}"
        if full_pod_name == pod_name:
            return jsonify({
                'name': pod['metadata']['name'],
                'namespace': pod['metadata']['namespace'],
                'labels': pod['metadata'].get('labels', {}),
                'status': pod['status'].get('phase', 'Unknown')
            })
    return jsonify({"error": "Pod not found."}), 404

def monitor_changes():
    previous_policies = get_network_policies()
    previous_pods = get_pods()
    
    while True:
        time.sleep(60)  # 1분마다 체크
        current_policies = get_network_policies()
        current_pods = get_pods()
        
        if not current_policies or not current_pods:
            continue
        
        if current_policies != previous_policies or current_pods != previous_pods:
            # 변화가 감지되었을 때 클라이언트에 실시간 업데이트 전송
            pod_map, policy_map = map_policies_to_pods(current_policies, current_pods)
            
            nodes = []
            edges = []
            
            for pod_key, pod in pod_map.items():
                nodes.append({
                    'data': {'id': pod_key, 'label': pod_key, 'group': 'pod'}
                })
                for policy in pod['policies']:
                    policy_key = f"{policy_map[policy]['namespace']}/{policy}"
                    nodes.append({
                        'data': {'id': policy_key, 'label': policy_key, 'group': 'policy'}
                    })
                    edges.append({
                        'data': {'source': policy_key, 'target': pod_key, 'label': 'applied'}
                    })
            
            unique_nodes = {node['data']['id']: node for node in nodes}.values()
            unique_edges = edges  # 필요 시 중복 제거 로직 추가
            
            graph_data = {
                'nodes': list(unique_nodes),
                'edges': unique_edges
            }
            
            socketio.emit('update', graph_data)
            previous_policies = current_policies
            previous_pods = current_pods

@socketio.on('connect')
def handle_connect():
    print('Client connected')

if __name__ == '__main__':
    thread = Thread(target=monitor_changes)
    thread.daemon = True
    thread.start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
