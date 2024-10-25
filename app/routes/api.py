from flask import Blueprint, jsonify, request, render_template
from ..services.k8s import (
    get_network_policies,
    get_pods,
    get_deployments,
    get_namespaces
)
from ..services.graph import map_policies_to_resources
from ..utils.exceptions import ResourceNotFoundError, InvalidResourceTypeError
from ..utils.logger import logger
from .. import socketio, cache_lock, cached_graph_data

api = Blueprint('api', __name__)

@api.route('/')
def index():
    logger.debug("Rendering index page")
    return render_template('index.html')

@api.route('/data')
def data():
    resource_type = request.args.get('resource_type', 'deployment')
    logger.info(f"Fetching data for resource type: {resource_type}")

    if resource_type not in ['deployment', 'pod']:
        raise InvalidResourceTypeError(f"Invalid resource type: {resource_type}")

    with cache_lock:
        if cached_graph_data.get(resource_type):
            logger.debug(f"Returning cached data for {resource_type}")
            return jsonify(cached_graph_data[resource_type])

    try:
        policies = get_network_policies()
        logger.debug("Successfully retrieved network policies")

        if resource_type == 'deployment':
            resources = get_deployments()
            logger.debug("Successfully retrieved deployments")
        else:
            resources = get_pods()
            logger.debug("Successfully retrieved pods")

        policy_map, edges, resource_map = map_policies_to_resources(policies, resources, resource_type)
        logger.debug("Successfully mapped policies to resources")

        nodes = []
        formatted_edges = []

        # 노드 생성
        for resource_key, resource in resource_map.items():
            nodes.append({
                'data': {
                    'id': resource_key,
                    'label': resource['label'],
                    'group': resource['group']
                }
            })

        # 엣지 생성
        for edge in edges:
            ports = edge.get('ports', [])
            if ports:
                ports_str = ', '.join([
                    f"{p.get('protocol', 'TCP')}/{p.get('port', 'N/A')}"
                    for p in ports
                ])
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

        # 중복 노드 제거
        unique_nodes = {node['data']['id']: node for node in nodes}.values()

        graph_data = {
            'nodes': list(unique_nodes),
            'edges': formatted_edges
        }

        # 캐시 업데이트
        with cache_lock:
            cached_graph_data[resource_type] = graph_data

        logger.info(f"Successfully generated graph data for {resource_type}")
        return jsonify(graph_data)

    except Exception as e:
        logger.error(f"Error generating graph data: {str(e)}", exc_info=True)
        raise

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

@socketio.on('connect')
def handle_connect():
    logger.info("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info("Client disconnected")