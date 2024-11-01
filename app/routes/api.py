from flask import Blueprint, jsonify, request, render_template
from ..services.k8s import (
    get_network_policies,
    get_pods,
    get_deployments,
    get_namespaces,
    NetworkPolicyAnalyzer
)
from ..services.graph import map_policies_to_resources
from ..services.communication_analyzer import CommunicationAnalyzer
from ..utils.exceptions import ResourceNotFoundError, InvalidResourceTypeError
from ..utils.logger import logger
from .. import socketio, cache_lock, cached_graph_data

api = Blueprint('api', __name__)

@api.route('/')
def index():
    logger.debug("Rendering index page")
    return render_template('index.html')

@api.route('/favicon.ico')
def favicon():
    return '', 204

@api.route('/data')
def data():
    logger.debug("Data request received")
    resource_type = request.args.get('resource_type', 'deployment')
    
    policies = get_network_policies()
    logger.debug(f"Retrieved {len(policies['items'])} policies")
    
    if resource_type == 'deployment':
        resources = get_deployments()
    else:
        resources = get_pods()
    logger.debug(f"Retrieved {len(resources['items'])} {resource_type}s")
    
    policy_map, edges, resource_map = map_policies_to_resources(policies, resources, resource_type)
    logger.debug(f"Generated {len(edges)} edges")
    
    # 노드와 엣지 포맷팅
    nodes = []
    formatted_edges = []
    
    for resource_key, resource in resource_map.items():
        node = {
            'data': {
                'id': resource_key,
                'label': resource['label'],
                'group': resource['type'] if resource.get('type') else resource['group']
            }
        }
        nodes.append(node)
    
    # 엣지 포맷팅
    for edge in edges:
        formatted_edge = {
            'data': {
                'id': f"{edge['source']}->{edge['target']}",
                'source': edge['source'],
                'target': edge['target'],
                'directed': True,  # 화살표 표시를 위해 추가
                'type': edge['type'],
                'label': f"{edge['type'].capitalize()} ({', '.join([f'{p.get('protocol', 'TCP')}/{p.get('port', 'N/A')}' for p in edge['ports']])})"
            }
        }
        formatted_edges.append(formatted_edge)
    
    graph_data = {
        'nodes': nodes,
        'edges': formatted_edges
    }
    
    logger.debug(f"Final graph data: {len(nodes)} nodes, {len(formatted_edges)} edges")
    return jsonify(graph_data)

@api.route('/namespaces')
def namespaces():
    logger.debug("Fetching namespaces")
    try:
        namespaces = get_namespaces()
        logger.debug(f"Successfully retrieved {len(namespaces)} namespaces")
        return jsonify({"namespaces": namespaces})
    except Exception as e:
        logger.error(f"Error fetching namespaces: {str(e)}", exc_info=True)
        raise

@api.route('/policy/<policy_name>')
def policy_details(policy_name):
    logger.debug(f"Fetching details for policy: {policy_name}")
    try:
        policies = get_network_policies()
        
        for policy in policies['items']:
            if policy['metadata']['name'] == policy_name:
                policy_data = {
                    'name': policy['metadata']['name'],
                    'namespace': policy['metadata']['namespace'],
                    'ingress': policy['spec'].get('ingress', []),
                    'egress': policy['spec'].get('egress', [])
                }
                logger.debug(f"Successfully retrieved policy details for {policy_name}")
                return jsonify(policy_data)
        
        logger.warning(f"Policy not found: {policy_name}")
        raise ResourceNotFoundError(f"Policy not found: {policy_name}")

    except ResourceNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error fetching policy details: {str(e)}", exc_info=True)
        raise

@api.route('/resource/<resource_type>/<path:resource_name>')
def resource_details(resource_type, resource_name):
    logger.debug(f"Fetching details for {resource_type}: {resource_name}")

    if resource_type not in ['deployment', 'pod']:
        logger.warning(f"Invalid resource type requested: {resource_type}")
        raise InvalidResourceTypeError(f"Invalid resource type: {resource_type}")

    try:
        if resource_type == 'deployment':
            resources = get_deployments()
        else:
            resources = get_pods()

        for resource in resources['items']:
            full_resource_name = f"{resource['metadata']['namespace']}/{resource['metadata']['name']}"
            if full_resource_name == resource_name:
                if resource_type == 'deployment':
                    resource_data = {
                        'name': resource['metadata']['name'],
                        'namespace': resource['metadata']['namespace'],
                        'labels': resource['metadata'].get('labels', {}),
                        'status': resource['status'].get('availableReplicas', 'Unknown'),
                        'replicas': resource['spec'].get('replicas', 0),
                        'strategy': resource['spec'].get('strategy', {}),
                        'selector': resource['spec'].get('selector', {}),
                        'created_at': resource['metadata'].get('creationTimestamp')
                    }
                else:  # pod
                    resource_data = {
                        'name': resource['metadata']['name'],
                        'namespace': resource['metadata']['namespace'],
                        'labels': resource['metadata'].get('labels', {}),
                        'status': resource['status'].get('phase', 'Unknown'),
                        'node': resource['spec'].get('nodeName', 'Unknown'),
                        'ip': resource['status'].get('podIP', 'Unknown'),
                        'created_at': resource['metadata'].get('creationTimestamp'),
                        'containers': [
                            {
                                'name': container['name'],
                                'image': container['image'],
                                'ready': any(
                                    status['ready']
                                    for status in resource['status'].get('containerStatuses', [])
                                    if status['name'] == container['name']
                                )
                            }
                            for container in resource['spec'].get('containers', [])
                        ]
                    }
                
                logger.debug(f"Successfully retrieved {resource_type} details for {resource_name}")
                return jsonify(resource_data)
        
        logger.warning(f"{resource_type.capitalize()} not found: {resource_name}")
        raise ResourceNotFoundError(f"{resource_type.capitalize()} not found: {resource_name}")

    except ResourceNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error fetching {resource_type} details: {str(e)}", exc_info=True)
        raise

@api.route('/analyze-communication')
def analyze_communication():
    """전체 통신 가능성을 분석합니다."""
    policies = get_network_policies()
    if resource_type == 'deployment':
        resources = get_deployments()
    else:
        resources = get_pods()

    analyzer = CommunicationAnalyzer(policies, resources)
    communication_map = analyzer.analyze_communications()
    
    return jsonify(communication_map)

@api.route('/check-communication')
def check_communication():
    """특정 두 리소스 간의 통신 가능성을 확인합니다."""
    source = request.args.get('source')
    target = request.args.get('target')
    resource_type = request.args.get('resource_type', 'deployment')
    
    if not source or not target:
        return jsonify({"error": "Source and target must be specified"}), 400

    try:
        logger.debug(f"Checking communication from {source} to {target}")
        policies = get_network_policies()
        if resource_type == 'deployment':
            resources = get_deployments()
        else:
            resources = get_pods()

        analyzer = NetworkPolicyAnalyzer(policies, resources)
        result = analyzer.analyze_communication(source, target)
        
        logger.debug(f"Analysis result: {result}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error checking communication: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    
@socketio.on('connect')
def handle_connect():
    logger.info("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info("Client disconnected")